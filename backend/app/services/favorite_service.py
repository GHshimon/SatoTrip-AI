"""
スポットお気に入りサービス
すべてのクエリを user_id でスコープし、他ユーザーのお気に入りに触れられないようにする
"""
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import List
import uuid

from app.models.spot import Spot
from app.models.spot_favorite import SpotFavorite


def _get_favorite(db: Session, user_id: str, spot_id: str) -> SpotFavorite | None:
    return db.query(SpotFavorite).filter(
        SpotFavorite.user_id == user_id,
        SpotFavorite.spot_id == spot_id
    ).first()


def add_favorite(db: Session, user_id: str, spot_id: str) -> Spot:
    """スポットをお気に入りに追加する（冪等：既に登録済みでも成功扱い）"""
    # スポットの実在確認
    spot = db.query(Spot).filter(Spot.id == spot_id).first()
    if not spot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="スポットが見つかりません"
        )

    existing = _get_favorite(db, user_id, spot_id)
    if not existing:
        favorite = SpotFavorite(
            id=str(uuid.uuid4()),
            user_id=user_id,
            spot_id=spot_id
        )
        db.add(favorite)
        db.commit()

    return spot


def remove_favorite(db: Session, user_id: str, spot_id: str) -> None:
    """お気に入りから削除する（登録が無い場合は404）"""
    favorite = _get_favorite(db, user_id, spot_id)
    if not favorite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="お気に入りが見つかりません"
        )
    db.delete(favorite)
    db.commit()


def get_favorite_spots(db: Session, user_id: str) -> List[Spot]:
    """ユーザーのお気に入りスポット一覧を新しい順に取得する"""
    return (
        db.query(Spot)
        .join(SpotFavorite, SpotFavorite.spot_id == Spot.id)
        .filter(SpotFavorite.user_id == user_id)
        .order_by(SpotFavorite.created_at.desc())
        .all()
    )


def get_favorite_spot_ids(db: Session, user_id: str) -> List[str]:
    """ユーザーのお気に入りスポットIDのみを取得する（フロントの状態判定用）"""
    rows = db.query(SpotFavorite.spot_id).filter(
        SpotFavorite.user_id == user_id
    ).all()
    return [r[0] for r in rows]
