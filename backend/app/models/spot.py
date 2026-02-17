"""
スポットモデル
"""
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, JSON
from sqlalchemy.sql import func
from app.utils.database import Base
import uuid


class Spot(Base):
    """スポットテーブル"""
    __tablename__ = "spots"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    area = Column(String, nullable=True, index=True)
    category = Column(String, nullable=True)  # History, Nature, Food, etc.
    duration_minutes = Column(Integer, nullable=True)
    rating = Column(Float, nullable=True)
    image = Column(String, nullable=True)
    price = Column(Float, nullable=True)
    tags = Column(JSON, nullable=True)  # Array of structured tags: [{"value": "...", "category": "...", "priority": 1, "source": "...", "normalized": "..."}]
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

