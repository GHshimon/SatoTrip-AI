"""
プランモデル
"""
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, JSON, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.utils.database import Base
import uuid


class Plan(Base):
    """プランテーブル"""
    __tablename__ = "plans"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    area = Column(String, nullable=True)
    days = Column(Integer, nullable=False)
    people = Column(Integer, nullable=True)
    budget = Column(Float, nullable=True)
    thumbnail = Column(String, nullable=True)
    spots = Column(JSON, nullable=False)  # Array of PlanSpot objects
    grounding_urls = Column(JSON, nullable=True)  # Array of URLs
    is_favorite = Column(Boolean, default=False)  # お気に入りフラグ
    folder_id = Column(String, ForeignKey("plan_folders.id"), nullable=True) # フォルダID
    check_in_date = Column(String, nullable=True)  # チェックイン日（YYYY-MM-DD形式）
    check_out_date = Column(String, nullable=True)  # チェックアウト日（YYYY-MM-DD形式）
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # リレーション
    user = relationship("User", backref="plans")

