"""
プランフォルダモデル
"""
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.utils.database import Base
import uuid


class PlanFolder(Base):
    """プランフォルダテーブル"""
    __tablename__ = "plan_folders"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    parent_id = Column(String, ForeignKey("plan_folders.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # リレーション
    user = relationship("User", backref="folders")
    parent = relationship("PlanFolder", remote_side=[id], backref="children")
    plans = relationship("Plan", backref="folder")
