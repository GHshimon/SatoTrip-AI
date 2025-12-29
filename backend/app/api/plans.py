"""
プラン管理APIエンドポイント
"""
from fastapi import APIRouter, Depends, HTTPException, status, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
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
from app.utils.route_service import get_route_info
from app.models.spot import Spot
from typing import Dict, Any


router = APIRouter(prefix="/api/plans", tags=["plans"])


def convert_generated_spots_to_plan_spots(
    generated_spots: List[Dict[str, Any]],
    db_spots: List[Spot],
    request: PlanGenerateRequest,
    generated_plan: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    生成されたスポットをPlanSpot形式に変換（共通関数）
    
    Args:
        generated_spots: 生成されたスポットリスト（spots配列）
        db_spots: データベースから取得したSpotモデルリスト
        request: プラン生成リクエスト
        generated_plan: 生成されたプランデータ
    
    Returns:
        PlanSpot形式のリスト
    """
    # スポットインデックスを作成（一度だけ）
    spot_index = create_spot_index(db_spots)
    
    plan_spots = []
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
            # データベースにない場合は生成された情報を使用
            spot_info = {
                "id": f"gen_spot_{uuid.uuid4()}_{i}",
                "name": spot_data.get("name", ""),
                "description": spot_data.get("description", ""),
                "area": generated_plan.get("area", request.destination),
                "category": spot_data.get("category", "Culture"),
                "durationMinutes": spot_data.get("durationMinutes", 60),
                "rating": 4.5,
                "image": "",
                "tags": spot_data.get("tags", []),
                "location": get_coordinates(spot_data.get("name", "") + " " + generated_plan.get("area", "")) or {
                    "lat": 0.0,
                    "lng": 0.0
                }
            }
        
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
    
    return plan_spots


@router.post("/generate-plan", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
async def generate_ai_plan(
    request: PlanGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """AIプラン生成（Gemini API呼び出し）"""
    # 1. キャッシュチェック
    cached_plan_data = get_cached_plan(
        db=db,
        destination=request.destination,
        days=request.days,
        budget=request.budget,
        themes=request.themes,
        pending_spots=request.pending_spots,
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
        db_spots = get_spots_for_plan(
            db=db,
            area=request.destination,
            themes=request.themes,
            limit=100
        )
        
        # 共通関数を使用して変換
        plan_spots = convert_generated_spots_to_plan_spots(
            generated_spots=cached_spots,
            db_spots=db_spots,
            request=request,
            generated_plan=cached_plan_data
        )
        
        plan_data = {
            "title": cached_plan_data.get("title", f"{request.destination}の{request.days}日間旅行"),
            "area": cached_plan_data.get("area", request.destination),
            "days": request.days,
            "people": 2,
            "budget": cached_plan_data.get("budget", 100000),
            "thumbnail": plan_spots[0]["spot"]["image"] if plan_spots else "",
            "spots": plan_spots,
            "grounding_urls": cached_plan_data.get("grounding_urls")
        }
        
        # データベースに保存（キャッシュからでも保存）
        plan = create_plan(db, current_user.id, plan_data)
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
    
    # #region agent log
    import json
    import time
    with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
        f.write(json.dumps({"location":"plans.py:39","message":"generate_ai_plan called","data":{"destination":request.destination,"themes":request.themes,"pendingSpotsCount":len(request.pending_spots)},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"A"},ensure_ascii=False)+'\n')
    # #endregion
    # データベースからスポットを取得
    db_spots = get_spots_for_plan(
        db=db,
        area=request.destination,
        themes=request.themes,
        limit=100
    )
    # #region agent log
    with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
        f.write(json.dumps({"location":"plans.py:46","message":"After get_spots_for_plan","data":{"dbSpotsCount":len(db_spots)},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"A"},ensure_ascii=False)+'\n')
    # #endregion
    
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
    # #region agent log
    with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
        f.write(json.dumps({"location":"plans.py:65","message":"db_spots_data converted","data":{"dbSpotsDataCount":len(db_spots_data),"firstSpotName":db_spots_data[0]["name"] if db_spots_data else None},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"A"},ensure_ascii=False)+'\n')
    # #endregion
    
    # スポット間の距離・時間を計算（プロンプトに含めるため）
    from app.utils.time_calculator import calculate_spot_distances
    all_spots_for_distance = db_spots_data[:20]  # 最大20件まで計算（パフォーマンス考慮）
    spot_distances = calculate_spot_distances(
        all_spots_for_distance,
        transportation=request.transportation
    )
    
    # Gemini APIでプラン生成（データベーススポットを含める）
    generated_plan = generate_plan(
        destination=request.destination,
        days=request.days,
        budget=request.budget,
        themes=request.themes,
        pending_spots=request.pending_spots,
        database_spots=db_spots_data,
        start_time=request.start_time,
        end_time=request.end_time,
        transportation=request.transportation,
        preferences=request.preferences,
        spot_distances=spot_distances
    )
    # #region agent log
    with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
        f.write(json.dumps({"location":"plans.py:75","message":"After generate_plan","data":{"hasPlan":bool(generated_plan),"generatedSpotsCount":len(generated_plan.get("spots", [])) if generated_plan else 0},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"C"},ensure_ascii=False)+'\n')
    # #endregion
    
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
    plan_spots_raw = convert_generated_spots_to_plan_spots(
        generated_spots=generated_spots,
        db_spots=db_spots,
        request=request,
        generated_plan=generated_plan
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
        day_spots.sort(key=lambda x: x.get("startTime", "00:00"))
        
        # スポット間の移動時間を計算
        for i in range(len(day_spots) - 1):
            current_spot = day_spots[i]
            next_spot = day_spots[i + 1]
            
            # 位置情報を取得
            loc1 = current_spot.get("spot", {}).get("location", {})
            loc2 = next_spot.get("spot", {}).get("location", {})
            
            lat1 = loc1.get("lat") or loc1.get("latitude")
            lng1 = loc1.get("lng") or loc1.get("longitude")
            lat2 = loc2.get("lat") or loc2.get("latitude")
            lng2 = loc2.get("lng") or loc2.get("longitude")
            
            # 位置情報がある場合は実際の移動時間を計算
            if lat1 and lng1 and lat2 and lng2 and lat1 != 0.0 and lng1 != 0.0 and lat2 != 0.0 and lng2 != 0.0:
                # 交通手段をプロファイルに変換
                profile_map = {
                    "車": "driving",
                    "電車": "transit",
                    "バス": "transit",
                    "徒歩": "walking",
                    "その他": "driving"
                }
                transport_mode = current_spot.get("transportMode", "train")
                profile = profile_map.get(request.transportation or transport_mode, "driving") if request.transportation else "driving"
                
                try:
                    route_info = get_route_info(
                        coordinates=[(lat1, lng1), (lat2, lng2)],
                        profile=profile
                    )
                    
                    if route_info:
                        transport_duration = int(route_info.get("duration_minutes", 20))
                        current_spot["transportDuration"] = transport_duration
                except Exception:
                    # エラー時は既存の値を使用
                    pass
    
    # 時刻を再計算（日ごと）
    from app.utils.time_calculator import recalculate_spot_times
    
    for day, day_spots in spots_by_day.items():
        # spots形式に変換
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
        
        # 時刻を再計算
        recalculated_spots = recalculate_spot_times(
            spots_for_recalc,
            start_time=request.start_time or "09:00",
            end_time=request.end_time or "18:00",
            transportation=request.transportation
        )
        
        # 再計算された時刻をplan_spotsに反映
        for i, ps in enumerate(day_spots):
            if i < len(recalculated_spots):
                recalc_spot = recalculated_spots[i]
                ps["startTime"] = recalc_spot.get("startTime", ps.get("startTime", "09:00"))
                ps["transportDuration"] = recalc_spot.get("transportDuration", ps.get("transportDuration", 20))
                # 滞在時間も更新（終了時間制約で調整された場合）
                if "durationMinutes" in recalc_spot:
                    ps["spot"]["durationMinutes"] = recalc_spot["durationMinutes"]
    
    plan_spots = plan_spots_raw
    
    # プランデータを作成
    plan_data = {
        "title": generated_plan.get("title", f"{request.destination}の{request.days}日間旅行"),
        "area": generated_plan.get("area", request.destination),
        "days": request.days,
        "people": 2,
        "budget": generated_plan.get("budget", 100000),
        "thumbnail": plan_spots[0]["spot"]["image"] if plan_spots else "",
        "spots": plan_spots,
        "grounding_urls": generated_plan.get("grounding_urls")
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
        
        # PlanSpotUpdateのリストを辞書に変換（IDをキーに）
        spot_updates = {spot_update["id"]: spot_update for spot_update in plan_dict["spots"]}
        
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
            has_order = any(spot_updates.get(spot.get("id") or spot.get("spotId", ""), {}).get("order") is not None for spot in day_spots)
            if has_order:
                # orderフィールドでソート
                day_spots.sort(key=lambda x: spot_updates.get(x.get("id") or x.get("spotId", ""), {}).get("order", 999))
            else:
                # 時間順にソート
                day_spots.sort(key=lambda x: x.get("startTime", "00:00"))
            
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
            # プランから開始時間・終了時間を取得できる場合は使用（将来的な拡張）
            
            # 時刻を再計算
            recalculated_spots = recalculate_spot_times(
                spots_for_recalc,
                start_time=start_time,
                end_time=end_time,
                transportation=None  # プランから取得可能な場合は使用
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

