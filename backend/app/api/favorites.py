"""
スポットお気に入りAPI
すべて認証必須・本人スコープ。/api/spots/{spot_id} と衝突しないよう独立プレフィックスにする
"""
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List

from app.utils.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.spot import SpotResponse
from app.services import favorite_service

router = APIRouter(
    prefix="/api/favorites",
    tags=["favorites"]
)


@router.get("", response_model=List[SpotResponse])
async def list_favorite_spots(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """お気に入りスポット一覧を取得"""
    return favorite_service.get_favorite_spots(db, current_user.id)


@router.get("/ids", response_model=List[str])
async def list_favorite_spot_ids(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """お気に入りスポットIDのみを取得（一覧画面でのお気に入り状態表示用）"""
    return favorite_service.get_favorite_spot_ids(db, current_user.id)


@router.post("/{spot_id}", response_model=SpotResponse, status_code=status.HTTP_201_CREATED)
async def add_favorite_spot(
    spot_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """スポットをお気に入りに追加"""
    return favorite_service.add_favorite(db, current_user.id, spot_id)


@router.delete("/{spot_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite_spot(
    spot_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """お気に入りから削除"""
    favorite_service.remove_favorite(db, current_user.id, spot_id)
