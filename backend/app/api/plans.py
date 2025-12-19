"""
プラン管理APIエンドポイント
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
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
import uuid
from datetime import datetime
from app.utils.geocoding import get_coordinates


router = APIRouter(prefix="/api/plans", tags=["plans"])


@router.post("/generate-plan", response_model=PlanResponse, status_code=status.HTTP_201_CREATED)
async def generate_ai_plan(
    request: PlanGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """AIプラン生成（Gemini API呼び出し）"""
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
    # #region agent log
    with open(r'c:\projects\SatoTrip-AI\.cursor\debug.log', 'a', encoding='utf-8') as f:
        f.write(json.dumps({"location":"plans.py:65","message":"db_spots_data converted","data":{"dbSpotsDataCount":len(db_spots_data),"firstSpotName":db_spots_data[0]["name"] if db_spots_data else None},"timestamp":int(time.time()*1000),"sessionId":"debug-session","runId":"run1","hypothesisId":"A"},ensure_ascii=False)+'\n')
    # #endregion
    
    # Gemini APIでプラン生成（データベーススポットを含める）
    generated_plan = generate_plan(
        destination=request.destination,
        days=request.days,
        budget=request.budget,
        themes=request.themes,
        pending_spots=request.pending_spots,
        database_spots=db_spots_data
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
    
    # 生成されたプランをPlanSpot形式に変換
    plan_spots = []
    for i, spot_data in enumerate(generated_plan.get("spots", [])):
        spot_name = spot_data.get("name", "")
        
        # データベースから該当するスポットを検索
        matched_spot = None
        for db_spot in db_spots:
            if db_spot.name == spot_name or spot_name in db_spot.name or db_spot.name in spot_name:
                matched_spot = db_spot
                break
        
        # データベースのスポットが見つかった場合は詳細情報を使用
        if matched_spot:
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
    """プラン更新"""
    plan_dict = plan_data.model_dump(exclude_unset=True)
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

