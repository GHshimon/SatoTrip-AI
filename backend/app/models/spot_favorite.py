"""
スポットお気に入りモデル
ユーザーとスポットの多対多を表す中間テーブル
"""
from sqlalchemy import Column, String, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.utils.database import Base
import uuid


class SpotFavorite(Base):
    """スポットお気に入りテーブル"""
    __tablename__ = "spot_favorites"
    __table_args__ = (
        # 同一ユーザーが同じスポットを重複登録できないようにする
        UniqueConstraint("user_id", "spot_id", name="uq_spot_favorite_user_spot"),
    )

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    spot_id = Column(String, ForeignKey("spots.id"), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # リレーション
    user = relationship("User", backref="spot_favorites")
    spot = relationship("Spot")
