"""
フォルダ関連のPydanticスキーマ
"""
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class FolderBase(BaseModel):
    """フォルダベーススキーマ"""
    name: str
    parent_id: Optional[str] = None


class FolderCreate(FolderBase):
    """フォルダ作成スキーマ"""
    pass


class FolderUpdate(BaseModel):
    """フォルダ更新スキーマ"""
    name: Optional[str] = None
    parent_id: Optional[str] = None


class FolderResponse(FolderBase):
    """フォルダレスポンススキーマ"""
    id: str
    user_id: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
