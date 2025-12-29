"""
スポット関連のPydanticスキーマ
"""
from pydantic import BaseModel
from typing import Optional, List, Dict
from datetime import datetime


class SpotBase(BaseModel):
    """スポットベーススキーマ"""
    name: str
    description: Optional[str] = None
    area: Optional[str] = None
    category: Optional[str] = None
    duration_minutes: Optional[int] = None
    rating: Optional[float] = None
    image: Optional[str] = None
    price: Optional[float] = None
    tags: Optional[List[str]] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class SpotCreate(SpotBase):
    """スポット作成スキーマ"""
    pass


class SpotUpdate(BaseModel):
    """スポット更新スキーマ"""
    name: Optional[str] = None
    description: Optional[str] = None
    area: Optional[str] = None
    category: Optional[str] = None
    duration_minutes: Optional[int] = None
    rating: Optional[float] = None
    image: Optional[str] = None
    price: Optional[float] = None
    tags: Optional[List[str]] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None


class SpotResponse(SpotBase):
    """スポットレスポンススキーマ"""
    id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class BulkAddRequest(BaseModel):
    """都道府県一括追加リクエストスキーマ"""
    prefecture: str
    max_results_per_keyword: Optional[int] = 5
    max_keywords: Optional[int] = None
    max_total_videos: Optional[int] = None
    add_location: Optional[bool] = True
    run_async: Optional[bool] = None
    category: Optional[str] = None


class BulkAddResponse(BaseModel):
    """都道府県一括追加レスポンススキーマ"""
    success: bool
    imported: int
    errors: int
    skipped: int
    total_keywords: int
    quota_exceeded: bool
    processed_keywords: int
    failed_keywords: int
    total_videos: int
    location_updated: Optional[int] = None
    location_errors: Optional[int] = None
    error: Optional[str] = None
    job_id: Optional[str] = None
    job_status: Optional[str] = None