"""
APIキーモデル
AIエージェント向けAPIキー管理
"""
from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.utils.database import Base
import uuid


class ApiKey(Base):
    """APIキーテーブル"""
    __tablename__ = "api_keys"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    key_hash = Column(String, nullable=False, unique=True, index=True)  # bcryptハッシュ
    name = Column(String, nullable=False)  # APIキーの名前/説明
    user_id = Column(String, ForeignKey("users.id"), nullable=True, index=True)  # 所有者（オプション）
    is_active = Column(Boolean, default=True, nullable=False)
    
    # レート制限設定
    rate_limit_per_minute = Column(Integer, default=10, nullable=False)
    rate_limit_per_hour = Column(Integer, default=100, nullable=False)
    rate_limit_per_day = Column(Integer, default=1000, nullable=False)
    monthly_plan_limit = Column(Integer, default=100, nullable=False)  # -1で無制限
    
    # タイムスタンプ
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    last_used_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # リレーション
    user = relationship("User", backref="api_keys")
    usage_records = relationship("ApiKeyUsage", back_populates="api_key", cascade="all, delete-orphan")


class ApiKeyUsage(Base):
    """APIキー使用量記録テーブル"""
    __tablename__ = "api_key_usage"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    api_key_id = Column(String, ForeignKey("api_keys.id"), nullable=False, index=True)
    month = Column(String, nullable=False, index=True)  # YYYY-MM形式
    request_count = Column(Integer, nullable=False, default=0)
    plan_generation_count = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # リレーション
    api_key = relationship("ApiKey", back_populates="usage_records")

