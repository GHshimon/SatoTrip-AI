"""
サブスクリプションと使用量モデル
"""
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.utils.database import Base
import uuid


class Subscription(Base):
    """サブスクリプションテーブル"""
    __tablename__ = "subscriptions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    plan_name = Column(String, nullable=False, default="free")  # free, basic, premium
    upgraded_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # リレーション
    user = relationship("User", backref="subscription")


class Usage(Base):
    """使用量記録テーブル"""
    __tablename__ = "usage"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    month = Column(String, nullable=False, index=True)  # YYYY-MM形式
    count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # リレーション
    user = relationship("User", backref="usage_records")

