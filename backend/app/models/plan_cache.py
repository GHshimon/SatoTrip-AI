"""
プランキャッシュモデル
"""
from sqlalchemy import Column, String, DateTime, JSON, Index
from sqlalchemy.sql import func
from app.utils.database import Base
import uuid


class PlanCache(Base):
    """プランキャッシュテーブル"""
    __tablename__ = "plan_cache"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    cache_key = Column(String, nullable=False, unique=True, index=True)  # MD5ハッシュ
    plan_data = Column(JSON, nullable=False)  # キャッシュされたプランデータ
    cached_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # 複合インデックス（期限切れチェック用）
    __table_args__ = (
        Index('idx_cache_expires', 'expires_at'),
    )

