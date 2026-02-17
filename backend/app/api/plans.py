"""
プラン管理APIエンドポイント
"""
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional, Tuple
from app.utils.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.plan import (
    PlanCreate,
    PlanUpdate,
    PlanResponse,
    PlanGenerateRequest
)
from app.services.plan_service import (
    create_plan,
    get_user_plans,
    get_plan,
    update_plan,
    delete_plan
)
from app.services.gemini_service import generate_plan
from app.services.spot_service import get_spots_for_plan
from app.utils.plan_cache import get_cached_plan, save_cached_plan
from app.utils.subscription import can_generate_plan, record_plan_generation, get_user_plan, check_feature_access
from app.utils.rate_limiter import rate_limiter
from app.utils.plan_export import export_to_pdf, export_to_ical
import uuid
from datetime import datetime
from app.utils.geocoding import get_coordinates
from app.utils.spot_matcher import create_spot_index, match_spot
from app.utils.route_service import get_route_info, get_route_info_batch
from app.models.spot import Spot
from typing import Dict, Any


router = APIRouter(prefix="/api/plans", tags=["plans"])


def filter_pending_spots_by_database(
    pending_spots: List[Dict[str, Any]],
    db_spots: List[Spot]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    pending_spotsをデータベースと照合してフィルタリング
    
    Args:
        pending_spots: ユーザーが選択したスポットリスト
        db_spots: データベースから取得したSpotモデルリスト
    
    Returns:
        (フィルタリングされたpending_spots, 除外されたスポットリスト)
    """
    if not pending_spots:
        return [], []
    
    if not db_spots:
        # データベースにスポットがない場合はすべて除外
        return [], pending_spots
    
    # スポットインデックスを作成
    spot_index = create_spot_index(db_spots)
    
    filtered_spots = []
    excluded_spots = []
    
    for pending_spot in pending_spots:
        spot_name = pending_spot.get("name", "")
        if not spot_name:
            excluded_spots.append(pending_spot)
            continue
        
        # データベースと照合
        match_result = match_spot(spot_name, spot_index, threshold=0.7)
        
        if match_result:
            # データベースに存在する場合は含める
            filtered_spots.append(pending_spot)
        else:
            # データベースに存在しない場合は除外
            excluded_spots.append(pending_spot)
    
    return filtered_spots, excluded_spots


def add_hotels_to_plan_spots(
    plan_spots: List[Dict[str, Any]],
    request: PlanGenerateRequest,
    db: Session,
    area: str
) -> List[Dict[str, Any]]:
    """
    プランスポットに宿泊施設を追加
    
    Args:
        plan_spots: 既存のプランスポットリスト
        request: プラン生成リクエスト
        db: データベースセッション
        area: エリア名
    
    Returns:
        宿泊施設が追加されたプランスポットリスト
    """
    try:
        from datetime import datetime, timedelta
        from app.services.spot_service import get_spots
        import uuid
        
        # チェックイン/チェックアウト日時をパース（オプショナル）
        check_in = None
        check_out = None
        if hasattr(request, "check_in_date") and request.check_in_date:
            try:
                check_in = datetime.strptime(request.check_in_date, "%Y-%m-%d")
            except Exception:
                pass
        if hasattr(request, "check_out_date") and request.check_out_date:
            try:
                check_out = datetime.strptime(request.check_out_date, "%Y-%m-%d")
            except Exception:
                pass
        
        # データベースから宿泊施設のスポットを取得
        # エリア名で検索（部分一致）
        hotel_spots = get_spots(
            db=db,
            area=area,
            category="Hotel",
            limit=10
        )
        
        # エリア名で見つからない場合、エリア名の部分文字列で再検索を試みる
        if not hotel_spots and area:
            # エリア名から都道府県名を抽出（例：「鹿児島県」→「鹿児島」）
            area_parts = area.replace("県", "").replace("府", "").replace("都", "").replace("道", "").strip()
            if area_parts and area_parts != area:
                hotel_spots = get_spots(
                    db=db,
                    area=area_parts,
                    category="Hotel",
                    limit=10
                )
        
        # それでも見つからない場合、カテゴリのみで検索（エリア指定なし）
        if not hotel_spots:
            hotel_spots = get_spots(
                db=db,
                area=None,
                category="Hotel",
                limit=10
            )
        
        if not hotel_spots:
            # 宿泊施設が見つからない場合はスキップ
            import logging
            logging.warning(f"宿泊施設が見つかりませんでした（エリア: {area}）")
            return plan_spots
        
        # 最初の宿泊施設を使用（複数ある場合は最初の1つ）
        hotel_spot = hotel_spots[0]
        
        # 日ごとにグループ化
        from collections import defaultdict
        spots_by_day = defaultdict(list)
        for ps in plan_spots:
            day = ps.get("day", 1)
            spots_by_day[day].append(ps)
        
        # 各日の最後に宿泊施設を追加
        updated_plan_spots = []
        for day in range(1, request.days + 1):
            day_spots = spots_by_day.get(day, [])
            
            # 二日目以降の最初に宿泊施設（前日の宿泊施設から出発）を追加
            if day > 1:
                # 前日の宿泊施設から出発することを示す宿泊施設を最初に追加
                hotel_departure_spot = {
                    "id": str(uuid.uuid4()),
                    "spotId": hotel_spot.id,
                    "spot": {
                        "id": hotel_spot.id,
                        "name": hotel_spot.name,
                        "description": hotel_spot.description or "",
                        "area": hotel_spot.area or area,
                        "category": "Hotel",
                        "durationMinutes": 0,
                        "rating": hotel_spot.rating or 4.0,
                        "image": hotel_spot.image or "",
                        "price": hotel_spot.price,
                        "tags": hotel_spot.tags or [],
                        "location": {
                            "lat": hotel_spot.latitude or 0.0,
                            "lng": hotel_spot.longitude or 0.0
                        }
                    },
                    "day": day,
                    "startTime": request.start_time or "09:00",  # プランの開始時刻
                    "note": "出発",
                    "transportMode": "walk",
                    "transportDuration": 0,
                    "isMustVisit": False
                }
                updated_plan_spots.append(hotel_departure_spot)
            
            # 既存のスポットを追加
            updated_plan_spots.extend(day_spots)
            
            # その日の最後のスポットの終了時刻を計算
            last_end_time = "18:00"  # デフォルト
            if day_spots:
                # 最後のスポットの終了時刻を計算
                last_spot = day_spots[-1]
                start_time = last_spot.get("startTime", "09:00")
                duration_minutes = last_spot.get("spot", {}).get("durationMinutes", 60)
                
                # 時刻を分単位に変換
                def time_to_minutes(time_str: str) -> int:
                    parts = time_str.split(":")
                    return int(parts[0]) * 60 + int(parts[1])
                
                def minutes_to_time(minutes: int) -> str:
                    hours = minutes // 60
                    mins = minutes % 60
                    return f"{hours:02d}:{mins:02d}"
                
                start_minutes = time_to_minutes(start_time)
                end_minutes = start_minutes + duration_minutes
                last_end_time = minutes_to_time(end_minutes)
            
            # 最終日以外の場合のみ宿泊施設を追加（最終日はチェックアウト日なので宿泊施設は不要）
            if day < request.days:
                # 宿泊施設をスポットとして追加
                hotel_plan_spot = {
                    "id": str(uuid.uuid4()),
                    "spotId": hotel_spot.id,
                    "spot": {
                        "id": hotel_spot.id,
                        "name": hotel_spot.name,
                        "description": hotel_spot.description or "",
                        "area": hotel_spot.area or area,
                        "category": "Hotel",
                        "durationMinutes": 0,  # 宿泊施設は滞在時間を計算しない
                        "rating": hotel_spot.rating or 4.0,
                        "image": hotel_spot.image or "",
                        "price": hotel_spot.price,
                        "tags": hotel_spot.tags or [],
                        "location": {
                            "lat": hotel_spot.latitude or 0.0,
                            "lng": hotel_spot.longitude or 0.0
                        }
                    },
                    "day": day,
                    "startTime": last_end_time,
                    "note": "宿泊",
                    "transportMode": "walk",
                    "transportDuration": 0,
                    "isMustVisit": False
                }
                updated_plan_spots.append(hotel_plan_spot)
        
        return updated_plan_spots
    
    except Exception as e:
        # エラーが発生した場合はログに記録してスキップ
        import logging
        logging.error(f"宿泊施設の追加中にエラーが発生しました: {str(e)}")
        return plan_spots


def convert_generated_spots_to_plan_spots(
    generated_spots: List[Dict[str, Any]],
    db_spots: List[Spot],
    request: PlanGenerateRequest,
    generated_plan: Dict[str, Any]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    生成されたスポットをPlanSpot形式に変換（共通関数）
    
    Args:
        generated_spots: 生成されたスポットリスト（spots配列）
        db_spots: データベースから取得したSpotモデルリスト
        request: プラン生成リクエスト
        generated_plan: 生成されたプランデータ
    
    Returns:
        (PlanSpot形式のリスト, 除外されたスポットのリスト)
    """
    # スポットインデックスを作成（一度だけ）
    spot_index = create_spot_index(db_spots)
    
    plan_spots = []
    excluded_spots = []
    
    for i, spot_data in enumerate(generated_spots):
        spot_name = spot_data.get("name", "")
        
        # 最適化されたマッチング
        match_result = match_spot(spot_name, spot_index)
        
        if match_result:
            matched_spot, score = match_result
            spot_info = {
                "id": matched_spot.id,
                "name": matched_spot.name,
                "description": spot_data.get("description") or matched_spot.description or "",
                "area": matched_spot.area or generated_plan.get("area", request.destination),
                "category": matched_spot.category or spot_data.get("category", "Culture"),
                "durationMinutes": matched_spot.duration_minutes or spot_data.get("durationMinutes", 60),
                "rating": matched_spot.rating or 4.5,
                "image": matched_spot.image or "",
                "tags": matched_spot.tags or spot_data.get("tags", []),
                "location": {
                    "lat": matched_spot.latitude or 0.0,
                    "lng": matched_spot.longitude or 0.0
                }
            }
        else:
            # データベースにない場合はスキップ（管理者画面にないスポットは使用しない）
            import logging
            logging.warning(f"データベースに存在しないスポットが生成されました: {spot_name}。このスポットはスキップされます。")
            excluded_spots.append({
                "name": spot_name,
                "reason": "データベースに存在しないスポット"
            })
            continue  # このスポットをスキップ
        
        plan_spot = {
            "id": f"gen_{uuid.uuid4()}_{i}",
            "spotId": spot_info["id"],
            "day": spot_data.get("day", 1),
            "startTime": spot_data.get("startTime"),
            "transportMode": spot_data.get("transportMode", "train"),
            "transportDuration": spot_data.get("transportDuration", 20),
            "isMustVisit": any(
                ps.get("name", "") in spot_name or spot_name in ps.get("name", "")
                for ps in request.pending_spots
            ),
            "spot": spot_info
        }
        plan_spots.append(plan_spot)
    
    return plan_spots, excluded_spots


@router.post("/generate-plan", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
async def generate_ai_plan(
    request: PlanGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """AIプラン生成（Gemini API呼び出し）"""
    # 0. データベースからスポットを取得（フィルタリング用）
    db_spots = get_spots_for_plan(
        db=db,
        area=request.destination,
        themes=request.themes,
        limit=100
    )
    
    # pending_spotsをデータベースと照合してフィルタリング（管理者画面にないスポットを除外）
    filtered_pending_spots, excluded_spots = filter_pending_spots_by_database(
        pending_spots=request.pending_spots,
        db_spots=db_spots
    )
    
    # すべてのpending_spotsが除外された場合のエラーハンドリング
    if request.pending_spots and not filtered_pending_spots:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"選択されたスポットがすべてデータベースに存在しません。管理者画面に登録されているスポットのみ使用できます。除外されたスポット: {[s.get('name', '') for s in excluded_spots]}"
        )
    
    # 1. キャッシュチェック（フィルタリングされたpending_spotsを使用）
    cached_plan_data = get_cached_plan(
        db=db,
        destination=request.destination,
        days=request.days,
        budget=request.budget,
        themes=request.themes,
        pending_spots=filtered_pending_spots,  # フィルタリングされたスポットを使用
        preferences=request.preferences,
        start_time=request.start_time,
        end_time=request.end_time,
        transportation=request.transportation
    )
    
    if cached_plan_data:
        # キャッシュからプランデータを取得して、PlanSpot形式に変換
        # days配列が存在する場合はspots配列に変換
        from app.services.gemini_service import convert_days_to_spots
        
        cached_spots = cached_plan_data.get("spots", [])
        if not cached_spots and cached_plan_data.get("days"):
            # days配列からspots配列に変換
            cached_spots = convert_days_to_spots(cached_plan_data["days"])
        
        # データベースからスポットを取得（マッチング用）
        # 既に取得済みのdb_spotsを再利用（重複クエリを回避）
        # db_spotsは上で既に取得済みなので、そのまま使用
        
        # 共通関数を使用して変換（フィルタリングされたpending_spotsを使用）
        # requestオブジェクトを一時的に更新してフィルタリングされたスポットを使用
        original_pending_spots = request.pending_spots
        request.pending_spots = filtered_pending_spots
        plan_spots, excluded_spots = convert_generated_spots_to_plan_spots(
            generated_spots=cached_spots,
            db_spots=db_spots,
            request=request,
            generated_plan=cached_plan_data
        )
        request.pending_spots = original_pending_spots  # 元に戻す
        
        # 宿泊施設を追加（常に追加）
        plan_spots = add_hotels_to_plan_spots(
            plan_spots=plan_spots,
            request=request,
            db=db,
            area=cached_plan_data.get("area", request.destination)
        )
        
        # キャッシュから取得した場合でも時刻を再計算
        # 日ごとにグループ化
        from collections import defaultdict
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
                
                # 距離を計算（移動手段の自動選択のため）
                from math import radians, cos, sin, asin, sqrt
                
                def haversine(lon1, lat1, lon2, lat2):
                    """2点間の距離を計算（km）"""
                    lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
                    dlon = lon2 - lon1
                    dlat = lat2 - lat1
                    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                    c = 2 * asin(sqrt(a))
                    r = 6371  # 地球の半径（km）
                    return c * r
                
                distance_km = haversine(lng1, lat1, lng2, lat2)
                
                profile_map = {
                    "車": "driving",
                    "公共交通機関": "transit",
                    "電車": "transit",
                    "バス": "transit",
                    "徒歩": "walking",
                    "その他": "driving"
                }
                # 移動手段を決定（全体 > スポット個別）
                day_transportation = request.transportation
                
                # 距離に基づく移動手段の自動選択
                if not day_transportation and not request.transportation:
                    if distance_km >= 10:
                        day_transportation = "車"
                    elif distance_km >= 5:
                        day_transportation = "公共交通機関"
                    else:
                        day_transportation = "徒歩"
                
                if day_transportation == "徒歩" and distance_km >= 5:
                    day_transportation = "公共交通機関"
                
                transport_mode = current_spot.get("transportMode", "train")
                profile = profile_map.get(day_transportation or transport_mode, "driving")
                
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
        
        # データベースに保存（キャッシュからでも保存）
        plan = create_plan(db, current_user.id, plan_data)
        # 除外されたスポット情報をレスポンスに含める（PlanResponseに追加する必要がある）
        return plan
    
    # 2. サブスクリプションチェック
    can_gen, message, remaining = can_generate_plan(db, current_user.id)
    if not can_gen:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=message
        )
    
    # 3. レート制限チェック
    plan_name = get_user_plan(db, current_user.id)
    allowed, rate_msg = rate_limiter.check_limit(db, current_user.id, plan_name)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=rate_msg
        )
    
    # Spotモデルを辞書形式に変換（プロンプト生成用のみ）
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
    
    # スポット間の距離・時間を計算（プロンプトに含めるため）
    from app.utils.time_calculator import calculate_spot_distances
    all_spots_for_distance = db_spots_data[:20]  # 最大20件まで計算（パフォーマンス考慮）
    spot_distances = calculate_spot_distances(
        all_spots_for_distance,
        transportation=request.transportation
    )
    
    # Gemini APIでプラン生成（フィルタリングされたpending_spotsのみ使用）
    # themesが辞書のリストの場合、文字列のリストに変換
    themes_list = []
    if request.themes:
        for theme in request.themes:
            if isinstance(theme, str):
                themes_list.append(theme)
            elif isinstance(theme, dict):
                # 辞書の場合はnameキーを取得、なければ文字列化
                themes_list.append(theme.get("name", str(theme)))
            else:
                themes_list.append(str(theme))
    
    generated_plan = generate_plan(
        destination=request.destination,
        days=request.days,
        budget=request.budget,
        themes=themes_list,  # 変換されたthemesを使用
        pending_spots=filtered_pending_spots,  # フィルタリングされたスポットのみ使用
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
    
    # 生成されたプランをPlanSpot形式に変換（共通関数を使用）
    # days配列が存在する場合はspots配列に変換
    from app.services.gemini_service import convert_days_to_spots
    from app.utils.time_calculator import recalculate_spot_times
    
    generated_spots = generated_plan.get("spots", [])
    if not generated_spots and generated_plan.get("days"):
        # days配列からspots配列に変換
        generated_spots = convert_days_to_spots(generated_plan["days"])
    
    # まずPlanSpot形式に変換
    plan_spots_raw, excluded_spots = convert_generated_spots_to_plan_spots(
        generated_spots=generated_spots,
        db_spots=db_spots,
        request=request,
        generated_plan=generated_plan
    )
    
    # 宿泊施設を追加（常に追加）
    plan_spots_raw = add_hotels_to_plan_spots(
        plan_spots=plan_spots_raw,
        request=request,
        db=db,
        area=generated_plan.get("area", request.destination)
    )
    
    # 時刻を再計算（実際の移動時間に基づく）
    # PlanSpot形式から一時的にspots形式に変換（日ごとにグループ化）
    from collections import defaultdict
    spots_by_day = defaultdict(list)
    for ps in plan_spots_raw:
        day = ps.get("day", 1)
        spots_by_day[day].append(ps)
    
    # 日ごとに時刻を再計算
    for day, day_spots in spots_by_day.items():
        # 日ごとのスポットを時間順にソート
        # ただし、二日目以降の宿泊施設（出発）は常に最初に配置
        def sort_key(spot):
            # 宿泊施設（出発）を最初に配置（二日目以降のみ）
            category = None
            if "spot" in spot and isinstance(spot["spot"], dict):
                category = spot["spot"].get("category")
            if not category:
                category = spot.get("category")
            note = spot.get("note", "")
            spot_day = spot.get("day", 1)
            
            # 二日目以降の出発の宿泊施設は最優先
            if category == "Hotel" and note == "出発" and spot_day > 1:
                return ("0", spot.get("startTime", "00:00"))
            # その他の宿泊施設は最後
            elif category == "Hotel":
                return ("2", spot.get("startTime", "00:00"))
            # 通常のスポットは時間順
            else:
                return ("1", spot.get("startTime", "00:00"))
        
        day_spots.sort(key=sort_key)
        
        # スポット間の移動時間を計算（バッチ処理で最適化）
        # 既にtransportDurationが設定されているスポットをスキップするため、まず必要なリクエストを収集
        route_requests = []
        route_request_indices = []
        default_transport_duration = 20
        
        for i in range(len(day_spots) - 1):
            current_spot = day_spots[i]
            next_spot = day_spots[i + 1]
            
            # 既にtransportDurationが設定されている場合はスキップ
            if current_spot.get("transportDuration", 0) > 0:
                continue
            
            # 位置情報を取得
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
            
            # 距離を計算（移動手段の自動選択のため）
            from math import radians, cos, sin, asin, sqrt
            
            def haversine(lon1, lat1, lon2, lat2):
                """2点間の距離を計算（km）"""
                lon1, lat1, lon2, lat2 = map(radians, [lon1, lat1, lon2, lat2])
                dlon = lon2 - lon1
                dlat = lat2 - lat1
                a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                c = 2 * asin(sqrt(a))
                r = 6371  # 地球の半径（km）
                return c * r
            
            distance_km = haversine(lng1, lat1, lng2, lat2)
            
            # 交通手段をプロファイルに変換
            profile_map = {
                "車": "driving",
                "公共交通機関": "transit",
                "電車": "transit",
                "バス": "transit",
                "徒歩": "walking",
                "その他": "driving"
            }
            
            # 移動手段を決定（全体 > スポット個別）
            day_transportation = request.transportation
            
            # 距離に基づく移動手段の自動選択
            if not day_transportation and not request.transportation:
                if distance_km >= 10:
                    day_transportation = "車"
                elif distance_km >= 5:
                    day_transportation = "公共交通機関"
                else:
                    day_transportation = "徒歩"
            
            if day_transportation == "徒歩" and distance_km >= 5:
                day_transportation = "公共交通機関"
            
            transport_mode = current_spot.get("transportMode", "train")
            profile = profile_map.get(day_transportation or transport_mode, "driving")
            
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
        
        # 時刻を再計算（同じday_spotsリストを使用）
        # 開始時刻を分単位に変換
        start_time_str = request.start_time or "09:00"
        start_hour, start_minute = map(int, start_time_str.split(":"))
        current_time_minutes = start_hour * 60 + start_minute
        
        # startTimeのみ再計算（編集された滞在時間・移動時間を使用）
        for i, ps in enumerate(day_spots):
            # 前のスポットからの移動時間を取得
            if i > 0:
                prev_spot = day_spots[i - 1]
                # 前のスポットの終了時刻を計算（開始時刻＋滞在時間）
                # current_time_minutesは前のループで前のスポットの開始時刻＋滞在時間になっている
                # これが前のスポットの終了時刻
                prev_end_time_minutes = current_time_minutes
                
                # 前のスポットの終了時刻に移動時間を加算
                transport_duration = prev_spot.get("transportDuration", 20)
                current_time_minutes = prev_end_time_minutes + transport_duration
            
            # startTimeを更新
            hours = current_time_minutes // 60
            minutes = current_time_minutes % 60
            ps["startTime"] = f"{hours:02d}:{minutes:02d}"
            
            # 次のスポットの開始時刻を計算（滞在時間を加算）
            duration_minutes = 60
            if "spot" in ps and isinstance(ps["spot"], dict):
                duration_minutes = ps["spot"].get("durationMinutes", 60)
            elif "durationMinutes" in ps:
                duration_minutes = ps["durationMinutes"]
            
            # 宿泊施設（出発）の場合、そのtransportDurationを次のスポットの開始時刻に加算
            # 宿泊施設（出発）のtransportDurationは「宿泊施設から次のスポットへの移動時間」を表している
            category = None
            if "spot" in ps and isinstance(ps["spot"], dict):
                category = ps["spot"].get("category")
            if not category:
                category = ps.get("category")
            note = ps.get("note", "")
            
            if category == "Hotel" and note == "出発":
                # 宿泊施設（出発）のtransportDurationを次のスポットの開始時刻に加算
                transport_duration = ps.get("transportDuration", 0)
                current_time_minutes += transport_duration
            else:
                # 通常のスポットの場合、滞在時間を加算
                current_time_minutes += duration_minutes
    
    # 時刻再計算後、ソート済みの順序でplan_spotsを再構築
    plan_spots = []
    for day in sorted(spots_by_day.keys()):
        plan_spots.extend(spots_by_day[day])
    
    # プランデータを作成
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
    
    # 4. キャッシュに保存（Gemini API形式のまま保存）
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
        # キャッシュ保存失敗はログに記録するが、処理は続行
        from app.utils.error_handler import log_error
        log_error(
            "CACHE_ERROR",
            f"キャッシュ保存失敗: {str(cache_error)}",
            {"destination": request.destination, "days": request.days}
        )
    
    # 5. 使用量を記録
    record_plan_generation(db, current_user.id)
    
    # データベースに保存
    plan = create_plan(db, current_user.id, plan_data)
    return plan


@router.get("/usage", status_code=status.HTTP_200_OK)
def get_plan_usage(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """プラン生成使用量を取得"""
    can_gen, message, remaining = can_generate_plan(db, current_user.id)
    plan_name = get_user_plan(db, current_user.id)
    from app.utils.subscription import get_plan_features
    plan_features = get_plan_features(db, current_user.id)
    
    return {
        "can_generate": can_gen,
        "message": message,
        "remaining": remaining,
        "plan_name": plan_name,
        "plan_features": plan_features
    }


@router.get("", response_model=List[PlanResponse])
async def list_plans(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ユーザーのプラン一覧取得"""
    plans = get_user_plans(db, current_user.id, skip, limit)
    return plans


@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan_detail(
    plan_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """プラン詳細取得"""
    plan = get_plan(db, plan_id, current_user.id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="プランが見つかりません"
        )
    return plan


@router.post("", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
async def create_plan_endpoint(
    plan_data: PlanCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """プラン保存"""
    plan_dict = plan_data.model_dump()
    plan = create_plan(db, current_user.id, plan_dict)
    return plan


@router.put("/{plan_id}", response_model=PlanResponse)
async def update_plan_endpoint(
    plan_id: str,
    plan_data: PlanUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """プラン更新（spots配列の更新と時刻再計算をサポート）"""
    from app.schemas.plan import PlanSpotUpdate
    from app.utils.time_calculator import recalculate_spot_times
    from collections import defaultdict
    
    # 既存のプランを取得
    plan = get_plan(db, plan_id, current_user.id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="プランが見つかりません"
        )
    
    plan_dict = plan_data.model_dump(exclude_unset=True)
    
    # spots配列の更新がある場合
    if "spots" in plan_dict and plan_dict["spots"]:
        # 既存のspotsを取得
        existing_spots = plan.spots if hasattr(plan, 'spots') else []
        existing_spot_ids = {s.get("id") or s.get("spotId", "") for s in existing_spots}
        
        # スポットの更新データを処理
        # PlanSpotUpdateのリストか、完全なPlanSpotのリストかを判定
        incoming_spots = plan_dict["spots"]
        is_full_spot_list = any("spot" in spot for spot in incoming_spots if isinstance(spot, dict))
        
        if is_full_spot_list:
            # 完全なPlanSpot配列の場合（PlanEditorから送られてくる場合）
            updated_spots = []
            new_spot_ids = set()
            
            # データベースからスポット一覧を取得（バリデーション用）
            from app.services.spot_service import get_spots_for_plan
            db_spots = get_spots_for_plan(
                db=db,
                area=plan.area or "",
                themes=[],
                limit=1000
            )
            spot_index = create_spot_index(db_spots)
            
            for incoming_spot in incoming_spots:
                spot_id = incoming_spot.get("id") or incoming_spot.get("spotId", "")
                
                # 新しいスポットか既存のスポットかを判定
                if spot_id not in existing_spot_ids and spot_id not in new_spot_ids:
                    # 新しいスポットの場合、データベースに存在するかチェック
                    spot_data = incoming_spot.get("spot", {})
                    spot_name = spot_data.get("name", "") if isinstance(spot_data, dict) else ""
                    
                    if spot_name:
                        match_result = match_spot(spot_name, spot_index)
                        if not match_result:
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"スポット '{spot_name}' はデータベースに存在しません。管理者画面に登録されているスポットのみ使用できます。"
                            )
                    
                    new_spot_ids.add(spot_id)
                
                updated_spots.append(incoming_spot)
        else:
            # PlanSpotUpdateのリストの場合（PlanDetailから送られてくる場合）
            # PlanSpotUpdateのリストを辞書に変換（IDをキーに）
            spot_updates = {spot_update["id"]: spot_update for spot_update in incoming_spots}
            
            # 既存のspotsを更新
            updated_spots = []
            for existing_spot in existing_spots:
                spot_id = existing_spot.get("id") or existing_spot.get("spotId", "")
                if spot_id in spot_updates:
                    update_data = spot_updates[spot_id]
                    # 更新可能なフィールドのみ更新
                    if "startTime" in update_data and update_data["startTime"] is not None:
                        existing_spot["startTime"] = update_data["startTime"]
                    if "durationMinutes" in update_data and update_data["durationMinutes"] is not None:
                        # spotオブジェクト内のdurationMinutesも更新
                        if "spot" in existing_spot and isinstance(existing_spot["spot"], dict):
                            existing_spot["spot"]["durationMinutes"] = update_data["durationMinutes"]
                        existing_spot["durationMinutes"] = update_data["durationMinutes"]
                    if "transportDuration" in update_data and update_data["transportDuration"] is not None:
                        existing_spot["transportDuration"] = update_data["transportDuration"]
                    if "transportMode" in update_data and update_data["transportMode"] is not None:
                        existing_spot["transportMode"] = update_data["transportMode"]
                updated_spots.append(existing_spot)
        
        # 更新されたspotsで時刻を再計算
        # 日ごとにグループ化
        spots_by_day = defaultdict(list)
        for spot in updated_spots:
            day = spot.get("day", 1)
            spots_by_day[day].append(spot)
        
        # 日ごとに時刻を再計算
        for day, day_spots in spots_by_day.items():
            # 順序情報（order）がある場合はそれでソート、なければstartTimeでソート
            # 完全なPlanSpot配列の場合は、startTimeでソート
            if not is_full_spot_list:
                has_order = any(spot_updates.get(spot.get("id") or spot.get("spotId", ""), {}).get("order") is not None for spot in day_spots)
                if has_order:
                    # orderフィールドでソート
                    day_spots.sort(key=lambda x: spot_updates.get(x.get("id") or x.get("spotId", ""), {}).get("order", 999))
                else:
                    # 時間順にソート
                    day_spots.sort(key=lambda x: x.get("startTime", "00:00"))
            else:
                # 完全なPlanSpot配列の場合は、startTimeでソート（既に順序が反映されている）
                day_spots.sort(key=lambda x: x.get("startTime", "00:00"))
            
            # 完全なPlanSpot配列の場合は、編集された値（滞在時間・移動時間）を保持しつつ、startTimeのみ再計算
            if is_full_spot_list:
                # startTimeのみ再計算（編集された滞在時間・移動時間を使用）
                current_time_minutes = 9 * 60  # 09:00を分単位で
                for i, ps in enumerate(day_spots):
                    # 前のスポットからの移動時間を取得
                    if i > 0:
                        prev_spot = day_spots[i - 1]
                        transport_duration = prev_spot.get("transportDuration", 20)
                        current_time_minutes += transport_duration
                    
                    # startTimeを更新
                    hours = current_time_minutes // 60
                    minutes = current_time_minutes % 60
                    ps["startTime"] = f"{hours:02d}:{minutes:02d}"
                    
                    # 次のスポットの開始時刻を計算（滞在時間を加算）
                    duration_minutes = 60
                    if "spot" in ps and isinstance(ps["spot"], dict):
                        duration_minutes = ps["spot"].get("durationMinutes", 60)
                    current_time_minutes += duration_minutes
            else:
                # PlanSpotUpdateのリストの場合、通常の再計算処理
                # spots形式に変換
                spots_for_recalc = []
                for ps in day_spots:
                    spot_data = {
                        "day": day,
                        "name": ps.get("spot", {}).get("name", "") if isinstance(ps.get("spot"), dict) else "",
                        "durationMinutes": ps.get("spot", {}).get("durationMinutes", ps.get("durationMinutes", 60)) if isinstance(ps.get("spot"), dict) else ps.get("durationMinutes", 60),
                        "transportDuration": ps.get("transportDuration", 20),
                        "location": ps.get("spot", {}).get("location", {}) if isinstance(ps.get("spot"), dict) else {}
                    }
                    spots_for_recalc.append(spot_data)
                
                # プランの開始時間・終了時間を取得（デフォルト値）
                start_time = "09:00"
                end_time = "18:00"
                
                # 時刻を再計算
                recalculated_spots = recalculate_spot_times(
                    spots_for_recalc,
                    start_time=start_time,
                    end_time=end_time,
                    transportation=None
                )
                
                # 再計算された時刻を反映
                for i, ps in enumerate(day_spots):
                    if i < len(recalculated_spots):
                        recalc_spot = recalculated_spots[i]
                        ps["startTime"] = recalc_spot.get("startTime", ps.get("startTime", "09:00"))
                        ps["transportDuration"] = recalc_spot.get("transportDuration", ps.get("transportDuration", 20))
                        if "durationMinutes" in recalc_spot:
                            if "spot" in ps and isinstance(ps["spot"], dict):
                                ps["spot"]["durationMinutes"] = recalc_spot["durationMinutes"]
                            if "durationMinutes" not in ps:
                                ps["durationMinutes"] = recalc_spot["durationMinutes"]
        
        plan_dict["spots"] = updated_spots
    
    # プランを更新
    plan = update_plan(db, plan_id, current_user.id, plan_dict)
    return plan


@router.delete("/{plan_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_plan_endpoint(
    plan_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """プラン削除"""
    delete_plan(db, plan_id, current_user.id)
    return None


@router.get("/{plan_id}/export/pdf")
async def export_plan_pdf(
    plan_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """プランをPDF形式でエクスポート"""
    # プラン取得
    plan = get_plan(db, plan_id, current_user.id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="プランが見つかりません"
        )
    
    # PDFエクスポート権限チェック
    if not check_feature_access(db, current_user.id, "pdf_export"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="PDFエクスポートはベーシックプラン以上で利用可能です"
        )
    
    # プランデータを辞書形式に変換
    plan_dict = {
        "title": plan.title,
        "area": plan.area,
        "days": plan.days,
        "spots": plan.spots,
        "summary": f"{plan.area}の{plan.days}日間旅行プラン"
    }
    
    try:
        pdf_buffer = export_to_pdf(plan_dict)
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=travel_plan_{plan_id}.pdf"
            }
        )
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PDFエクスポート機能を使用するには、reportlabライブラリが必要です"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"PDF生成エラー: {str(e)}"
        )


@router.get("/{plan_id}/export/ical")
async def export_plan_ical(
    plan_id: str,
    start_date: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """プランをiCalendar形式でエクスポート"""
    # プラン取得
    plan = get_plan(db, plan_id, current_user.id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="プランが見つかりません"
        )
    
    # 開始日をパース
    if start_date:
        try:
            start_datetime = datetime.fromisoformat(start_date.replace("Z", "+00:00"))
        except:
            start_datetime = None
    else:
        start_datetime = None
    
    # プランデータを辞書形式に変換
    plan_dict = {
        "title": plan.title,
        "area": plan.area,
        "days": plan.days,
        "spots": plan.spots
    }
    
    try:
        ical_data = export_to_ical(plan_dict, start_datetime)
        return Response(
            content=ical_data,
            media_type="text/calendar",
            headers={
                "Content-Disposition": f"attachment; filename=travel_plan_{plan_id}.ics"
            }
        )
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="カレンダーエクスポート機能を使用するには、icalendarライブラリが必要です"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"カレンダー生成エラー: {str(e)}"
        )


@router.get("/{plan_id}/route")
async def get_plan_route(
    plan_id: str,
    day: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    プランのルート情報を取得
    
    Args:
        plan_id: プランID
        day: 日数（指定がない場合は全日のルート情報を返す）
        current_user: 現在のユーザー
        db: データベースセッション
    
    Returns:
        ルート情報（geometry, distance, duration）
    """
    # プラン取得
    plan = get_plan(db, plan_id, current_user.id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="プランが見つかりません"
        )
    
    # プランのスポットを取得
    import json
    plan_spots = json.loads(plan.spots) if isinstance(plan.spots, str) else plan.spots
    
    # 日数でフィルタリング
    if day:
        plan_spots = [s for s in plan_spots if s.get("day") == day]
    
    # 座標を抽出
    coordinates = []
    for spot in plan_spots:
        spot_data = spot.get("spot", {})
        location = spot_data.get("location", {})
        if location.get("lat") and location.get("lng"):
            coordinates.append((location["lat"], location["lng"]))
    
    if len(coordinates) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ルート情報を取得するには、少なくとも2つのスポットが必要です"
        )
    
    # ルート情報を取得
    route_info = get_route_info(coordinates)
    
    if not route_info:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="ルート情報の取得に失敗しました"
        )
    
    return {
        "plan_id": plan_id,
        "day": day,
        "route": route_info
    }

