"""
ユーザー管理APIエンドポイント
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.utils.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import UserResponse, UserUpdate
from app.services.user_service import update_user
from app.services.plan_service import get_user_plans
from app.schemas.plan import PlanResponse

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """現在のユーザー情報取得"""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ユーザー情報更新"""
    user_dict = user_data.model_dump(exclude_unset=True)
    updated_user = update_user(db, current_user.id, user_dict)
    return updated_user


@router.get("/me/plans", response_model=List[PlanResponse])
async def get_current_user_plans(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ユーザーのプラン一覧（/api/plansのエイリアス）"""
    plans = get_user_plans(db, current_user.id, skip, limit)
    return plans

