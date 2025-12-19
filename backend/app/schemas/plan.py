"""
プラン関連のPydanticスキーマ
"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime


class PlanSpotBase(BaseModel):
    """プランスポットベーススキーマ"""
    spot_id: str
    day: int
    start_time: Optional[str] = None
    note: Optional[str] = None
    transport_mode: Optional[str] = None
    transport_duration: Optional[int] = None
    is_must_visit: Optional[bool] = False


class PlanBase(BaseModel):
    """プランベーススキーマ"""
    title: str
    area: str
    days: int
    people: Optional[int] = None
    budget: Optional[float] = None
    thumbnail: Optional[str] = None
    spots: List[Dict[str, Any]]  # PlanSpot objects as JSON
    grounding_urls: Optional[List[str]] = None


class PlanCreate(PlanBase):
    """プラン作成スキーマ"""
    pass


class PlanUpdate(BaseModel):
    """プラン更新スキーマ"""
    title: Optional[str] = None
    area: Optional[str] = None
    days: Optional[int] = None
    people: Optional[int] = None
    budget: Optional[float] = None
    thumbnail: Optional[str] = None
    spots: Optional[List[Dict[str, Any]]] = None
    grounding_urls: Optional[List[str]] = None


class PlanResponse(PlanBase):
    """プランレスポンススキーマ"""
    id: str
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class PlanGenerateRequest(BaseModel):
    """プラン生成リクエスト"""
    destination: str
    days: int
    budget: str
    themes: List[str]
    pending_spots: List[Dict[str, Any]]  # Spot objects

