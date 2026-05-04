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
    address = Column(String, nullable=True, index=True)
    category = Column(String, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    rating = Column(Float, nullable=True)
    image = Column(String, nullable=True)
    price = Column(Float, nullable=True)
    tags = Column(JSON, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    place_id = Column(String, nullable=True, unique=True, index=True)
    phone = Column(String, nullable=True)
    website = Column(String, nullable=True)
    source_videos = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
