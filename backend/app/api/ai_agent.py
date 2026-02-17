"""
AIエージェント向けプラン生成APIエンドポイント
APIキー認証を使用
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Tuple
from app.utils.database import get_db
from app.dependencies import verify_api_key
from app.models.api_key import ApiKey
from app.schemas.plan import PlanGenerateRequest, PlanResponse
from app.services.plan_service import create_plan
from app.services.gemini_service import generate_plan
from app.services.spot_service import get_spots_for_plan
from app.utils.plan_cache import get_cached_plan, save_cached_plan
from app.utils.rate_limiter import rate_limiter
from app.services.api_key_service import (
    check_api_key_plan_limit,
    record_api_key_request
)
from app.utils.geocoding import get_coordinates
from app.utils.spot_matcher import create_spot_index, match_spot
from app.utils.route_service import get_route_info, get_route_info_batch
from app.models.spot import Spot
from app.api.plans import (
    filter_pending_spots_by_database,
    add_hotels_to_plan_spots,
    convert_generated_spots_to_plan_spots
)
import uuid
from datetime import datetime
from collections import defaultdict

router = APIRouter(prefix="/api/v1/ai", tags=["ai-agent"])


@router.post("/generate-plan", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
async def generate_ai_plan_for_agent(
    request: PlanGenerateRequest,
    api_key: ApiKey = Depends(verify_api_key),
    db: Session = Depends(get_db)
):
    """
    AIエージェント向けプラン生成エンドポイント
    APIキー認証を使用
    """
    # 1. レート制限チェック
    allowed, rate_msg = rate_limiter.check_limit_by_api_key(
        db=db,
        api_key_id=api_key.id,
        rate_limit_per_minute=api_key.rate_limit_per_minute,
        rate_limit_per_hour=api_key.rate_limit_per_hour,
        rate_limit_per_day=api_key.rate_limit_per_day
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=rate_msg
        )
    
    # 2. プラン生成上限チェック
    can_gen, message, remaining = check_api_key_plan_limit(db, api_key.id)
    if not can_gen:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=message
        )
    
    # 3. リクエストを記録
    record_api_key_request(db, api_key.id, is_plan_generation=False)
    
    # 4. データベースからスポットを取得（フィルタリング用）
    db_spots = get_spots_for_plan(
        db=db,
        area=request.destination,
        themes=request.themes,
        limit=100
    )
    
    # 5. pending_spotsをデータベースと照合してフィルタリング
    filtered_pending_spots, excluded_spots = filter_pending_spots_by_database(
        pending_spots=request.pending_spots,
        db_spots=db_spots
    )
    
    # 6. すべてのpending_spotsが除外された場合のエラーハンドリング
    if request.pending_spots and not filtered_pending_spots:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"選択されたスポットがすべてデータベースに存在しません。管理者画面に登録されているスポットのみ使用できます。除外されたスポット: {[s.get('name', '') for s in excluded_spots]}"
        )
    
    # 7. キャッシュチェック
    cached_plan_data = get_cached_plan(
        db=db,
        destination=request.destination,
        days=request.days,
        budget=request.budget,
        themes=request.themes,
        pending_spots=filtered_pending_spots,
        preferences=request.preferences,
        start_time=request.start_time,
        end_time=request.end_time,
        transportation=request.transportation
    )
    
    if cached_plan_data:
        # キャッシュからプランデータを取得
        from app.services.gemini_service import convert_days_to_spots
        
        cached_spots = cached_plan_data.get("spots", [])
        if not cached_spots and cached_plan_data.get("days"):
            cached_spots = convert_days_to_spots(cached_plan_data["days"])
        
        # データベースからスポットを取得（マッチング用）
        # 既に取得済みのdb_spotsを再利用（重複クエリを回避）
        # db_spotsは上で既に取得済みなので、そのまま使用
        
        # 共通関数を使用して変換
        original_pending_spots = request.pending_spots
        request.pending_spots = filtered_pending_spots
        plan_spots, excluded_spots = convert_generated_spots_to_plan_spots(
            generated_spots=cached_spots,
            db_spots=db_spots,
            request=request,
            generated_plan=cached_plan_data
        )
        request.pending_spots = original_pending_spots
        
        # 宿泊施設を追加
        plan_spots = add_hotels_to_plan_spots(
            plan_spots=plan_spots,
            request=request,
            db=db,
            area=cached_plan_data.get("area", request.destination)
        )
        
        # キャッシュから取得した場合でも時刻を再計算
        # 日ごとにグループ化
        spots_by_day_cached = defaultdict(list)
        for ps in plan_spots:
            day = ps.get("day", 1)
            spots_by_day_cached[day].append(ps)
        
        # 日ごとに時刻を再計算（キャッシュから取得した場合）
        for day, day_spots in spots_by_day_cached.items():
            def sort_key(spot):
                category = None
                if "spot" in spot and isinstance(spot["spot"], dict):
                    category = spot["spot"].get("category")
                if not category:
                    category = spot.get("category")
                note = spot.get("note", "")
                spot_day = spot.get("day", 1)
                
                if category == "Hotel" and note == "出発" and spot_day > 1:
                    return ("0", spot.get("startTime", "00:00"))
                elif category == "Hotel":
                    return ("2", spot.get("startTime", "00:00"))
                else:
                    return ("1", spot.get("startTime", "00:00"))
            
            day_spots.sort(key=sort_key)
            
            # スポット間の移動時間を計算（バッチ処理で最適化）
            route_requests = []
            route_request_indices = []
            default_transport_duration = 20
            
            for i in range(len(day_spots) - 1):
                current_spot = day_spots[i]
                next_spot = day_spots[i + 1]
                
                # 既にtransportDurationが設定されている場合はスキップ
                if current_spot.get("transportDuration", 0) > 0:
                    continue
                
                loc1 = current_spot.get("spot", {}).get("location", {})
                loc2 = next_spot.get("spot", {}).get("location", {})
                
                lat1 = loc1.get("lat") or loc1.get("latitude")
                lng1 = loc1.get("lng") or loc1.get("longitude")
                lat2 = loc2.get("lat") or loc2.get("latitude")
                lng2 = loc2.get("lng") or loc2.get("longitude")
                
                # 位置情報がない場合はデフォルト値を設定してスキップ
                if not lat1 or not lng1 or not lat2 or not lng2 or lat1 == 0.0 or lng1 == 0.0 or lat2 == 0.0 or lng2 == 0.0:
                    current_spot["transportDuration"] = default_transport_duration
                    continue
                
                profile_map = {
                    "車": "driving",
                    "電車": "transit",
                    "バス": "transit",
                    "徒歩": "walking",
                    "その他": "driving"
                }
                transport_mode = current_spot.get("transportMode", "train")
                profile = profile_map.get(request.transportation or transport_mode, "driving") if request.transportation else "driving"
                
                # バッチ処理用にリクエストを収集
                route_requests.append(([(lat1, lng1), (lat2, lng2)], profile))
                route_request_indices.append(i)
            
            # バッチ処理でルート情報を取得
            if route_requests:
                route_results = get_route_info_batch(route_requests, max_workers=10)
                
                # 結果を適用
                for idx, route_result in enumerate(route_results):
                    spot_idx = route_request_indices[idx]
                    current_spot = day_spots[spot_idx]
                    
                    if route_result:
                        transport_duration = int(route_result.get("duration_minutes", default_transport_duration))
                        current_spot["transportDuration"] = transport_duration
                    else:
                        current_spot["transportDuration"] = default_transport_duration
            
            # 時刻を再計算
            start_time_str = request.start_time or "09:00"
            start_hour, start_minute = map(int, start_time_str.split(":"))
            current_time_minutes = start_hour * 60 + start_minute
            
            for i, ps in enumerate(day_spots):
                if i > 0:
                    prev_spot = day_spots[i - 1]
                    prev_end_time_minutes = current_time_minutes
                    transport_duration = prev_spot.get("transportDuration", 20)
                    current_time_minutes = prev_end_time_minutes + transport_duration
                
                hours = current_time_minutes // 60
                minutes = current_time_minutes % 60
                ps["startTime"] = f"{hours:02d}:{minutes:02d}"
                
                duration_minutes = 60
                if "spot" in ps and isinstance(ps["spot"], dict):
                    duration_minutes = ps["spot"].get("durationMinutes", 60)
                elif "durationMinutes" in ps:
                    duration_minutes = ps["durationMinutes"]
                
                category = None
                if "spot" in ps and isinstance(ps["spot"], dict):
                    category = ps["spot"].get("category")
                if not category:
                    category = ps.get("category")
                note = ps.get("note", "")
                
                if category == "Hotel" and note == "出発":
                    transport_duration = ps.get("transportDuration", 0)
                    current_time_minutes += transport_duration
                else:
                    current_time_minutes += duration_minutes
        
        plan_data = {
            "title": cached_plan_data.get("title", f"{request.destination}の{request.days}日間旅行"),
            "area": cached_plan_data.get("area", request.destination),
            "days": request.days,
            "people": 2,
            "budget": cached_plan_data.get("budget", 100000),
            "thumbnail": plan_spots[0]["spot"]["image"] if plan_spots else "",
            "spots": plan_spots,
            "grounding_urls": cached_plan_data.get("grounding_urls"),
            "excluded_spots": excluded_spots,
            "check_in_date": getattr(request, "check_in_date", None),
            "check_out_date": getattr(request, "check_out_date", None)
        }
        
        # プラン生成を記録
        record_api_key_request(db, api_key.id, is_plan_generation=True)
        
        # データベースに保存
        # APIキーにuser_idが設定されている場合はそれを使用、ない場合はエラー
        if not api_key.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="このAPIキーには所有者が設定されていません。プランを作成するには、APIキーにuser_idを設定してください。"
            )
        
        try:
            plan = create_plan(db, api_key.user_id, plan_data)
            return plan
        except Exception as e:
            raise
    
    # 8. Gemini APIでプラン生成
    # Spotモデルを辞書形式に変換
    db_spots_data = [
        {
            "name": spot.name,
            "description": spot.description or "",
            "area": spot.area or "",
            "category": spot.category or "Culture",
            "durationMinutes": spot.duration_minutes or 60,
            "rating": spot.rating or 4.0,
            "image": spot.image or "",
            "tags": spot.tags or [],
            "location": {
                "lat": spot.latitude or 0.0,
                "lng": spot.longitude or 0.0
            }
        }
        for spot in db_spots
    ]
    
    # スポット間の距離・時間を計算
    from app.utils.time_calculator import calculate_spot_distances
    all_spots_for_distance = db_spots_data[:20]
    spot_distances = calculate_spot_distances(
        all_spots_for_distance,
        transportation=request.transportation
    )
    
    # themesが辞書のリストの場合、文字列のリストに変換
    themes_list = []
    if request.themes:
        for theme in request.themes:
            if isinstance(theme, str):
                themes_list.append(theme)
            elif isinstance(theme, dict):
                themes_list.append(theme.get("name", str(theme)))
            else:
                themes_list.append(str(theme))
    
    generated_plan = generate_plan(
        destination=request.destination,
        days=request.days,
        budget=request.budget,
        themes=themes_list,
        pending_spots=filtered_pending_spots,
        database_spots=db_spots_data,
        start_time=request.start_time,
        end_time=request.end_time,
        transportation=request.transportation,
        preferences=request.preferences,
        spot_distances=spot_distances
    )
    
    if not generated_plan:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="プラン生成に失敗しました"
        )
    
    # 9. 生成されたプランをPlanSpot形式に変換
    from app.services.gemini_service import convert_days_to_spots
    from app.utils.time_calculator import recalculate_spot_times
    
    generated_spots = generated_plan.get("spots", [])
    if not generated_spots and generated_plan.get("days"):
        generated_spots = convert_days_to_spots(generated_plan["days"])
    
    # PlanSpot形式に変換
    plan_spots_raw, excluded_spots = convert_generated_spots_to_plan_spots(
        generated_spots=generated_spots,
        db_spots=db_spots,
        request=request,
        generated_plan=generated_plan
    )
    
    # 宿泊施設を追加
    plan_spots_raw = add_hotels_to_plan_spots(
        plan_spots=plan_spots_raw,
        request=request,
        db=db,
        area=generated_plan.get("area", request.destination)
    )
    
    # 時刻を再計算
    spots_by_day = defaultdict(list)
    for ps in plan_spots_raw:
        day = ps.get("day", 1)
        spots_by_day[day].append(ps)
    
    # 日ごとに時刻を再計算
    for day, day_spots in spots_by_day.items():
        def sort_key(spot):
            category = None
            if "spot" in spot and isinstance(spot["spot"], dict):
                category = spot["spot"].get("category")
            if not category:
                category = spot.get("category")
            note = spot.get("note", "")
            spot_day = spot.get("day", 1)
            
            if category == "Hotel" and note == "出発" and spot_day > 1:
                return ("0", spot.get("startTime", "00:00"))
            elif category == "Hotel":
                return ("2", spot.get("startTime", "00:00"))
            else:
                return ("1", spot.get("startTime", "00:00"))
        
        day_spots.sort(key=sort_key)
        
        # スポット間の移動時間を計算（バッチ処理で最適化）
        route_requests = []
        route_request_indices = []
        default_transport_duration = 20
        
        for i in range(len(day_spots) - 1):
            current_spot = day_spots[i]
            next_spot = day_spots[i + 1]
            
            # 既にtransportDurationが設定されている場合はスキップ
            if current_spot.get("transportDuration", 0) > 0:
                continue
            
            loc1 = current_spot.get("spot", {}).get("location", {})
            loc2 = next_spot.get("spot", {}).get("location", {})
            
            lat1 = loc1.get("lat") or loc1.get("latitude")
            lng1 = loc1.get("lng") or loc1.get("longitude")
            lat2 = loc2.get("lat") or loc2.get("latitude")
            lng2 = loc2.get("lng") or loc2.get("longitude")
            
            # 位置情報がない場合はデフォルト値を設定してスキップ
            if not lat1 or not lng1 or not lat2 or not lng2 or lat1 == 0.0 or lng1 == 0.0 or lat2 == 0.0 or lng2 == 0.0:
                current_spot["transportDuration"] = default_transport_duration
                continue
            
            profile_map = {
                "車": "driving",
                "電車": "transit",
                "バス": "transit",
                "徒歩": "walking",
                "その他": "driving"
            }
            transport_mode = current_spot.get("transportMode", "train")
            profile = profile_map.get(request.transportation or transport_mode, "driving") if request.transportation else "driving"
            
            # バッチ処理用にリクエストを収集
            route_requests.append(([(lat1, lng1), (lat2, lng2)], profile))
            route_request_indices.append(i)
        
        # バッチ処理でルート情報を取得
        if route_requests:
            route_results = get_route_info_batch(route_requests, max_workers=10)
            
            # 結果を適用
            for idx, route_result in enumerate(route_results):
                spot_idx = route_request_indices[idx]
                current_spot = day_spots[spot_idx]
                
                if route_result:
                    transport_duration = int(route_result.get("duration_minutes", default_transport_duration))
                    current_spot["transportDuration"] = transport_duration
                else:
                    current_spot["transportDuration"] = default_transport_duration
    
    # 時刻を再計算（日ごと）
    from app.utils.time_calculator import recalculate_spot_times
    
    for day, day_spots in spots_by_day.items():
        spots_for_recalc = []
        for ps in day_spots:
            spot_data = {
                "day": day,
                "name": ps.get("spot", {}).get("name", ""),
                "durationMinutes": ps.get("spot", {}).get("durationMinutes", 60),
                "transportDuration": ps.get("transportDuration", 20),
                "location": ps.get("spot", {}).get("location", {})
            }
            spots_for_recalc.append(spot_data)
        
        recalculated_spots = recalculate_spot_times(
            spots_for_recalc,
            start_time=request.start_time or "09:00",
            end_time=request.end_time or "18:00",
            transportation=request.transportation
        )
        
        for i, ps in enumerate(day_spots):
            if i < len(recalculated_spots):
                recalc_spot = recalculated_spots[i]
                ps["startTime"] = recalc_spot.get("startTime", ps.get("startTime", "09:00"))
                ps["transportDuration"] = recalc_spot.get("transportDuration", ps.get("transportDuration", 20))
                if "durationMinutes" in recalc_spot:
                    ps["spot"]["durationMinutes"] = recalc_spot["durationMinutes"]
    
    plan_spots = plan_spots_raw
    
    # 10. プランデータを作成
    plan_data = {
        "title": generated_plan.get("title", f"{request.destination}の{request.days}日間旅行"),
        "area": generated_plan.get("area", request.destination),
        "days": request.days,
        "people": 2,
        "budget": generated_plan.get("budget", 100000),
        "thumbnail": plan_spots[0]["spot"]["image"] if plan_spots else "",
        "spots": plan_spots,
        "grounding_urls": generated_plan.get("grounding_urls"),
        "excluded_spots": excluded_spots,
        "check_in_date": getattr(request, "check_in_date", None),
        "check_out_date": getattr(request, "check_out_date", None)
    }
    
    # 11. キャッシュに保存
    try:
        save_cached_plan(
            db=db,
            destination=request.destination,
            days=request.days,
            budget=request.budget,
            themes=request.themes,
            pending_spots=request.pending_spots,
            plan=generated_plan,
            preferences=request.preferences,
            start_time=request.start_time,
            end_time=request.end_time,
            transportation=request.transportation
        )
    except Exception as cache_error:
        from app.utils.error_handler import log_error
        log_error(
            "CACHE_ERROR",
            f"キャッシュ保存失敗: {str(cache_error)}",
            {"destination": request.destination, "days": request.days}
        )
    
    # 12. プラン生成を記録
    record_api_key_request(db, api_key.id, is_plan_generation=True)
    
    # 13. データベースに保存
    # APIキーにuser_idが設定されている場合はそれを使用、ない場合はエラー
    if not api_key.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="このAPIキーには所有者が設定されていません。プランを作成するには、APIキーにuser_idを設定してください。"
        )
    
    try:
        plan = create_plan(db, api_key.user_id, plan_data)
        return plan
    except Exception as e:
        raise

