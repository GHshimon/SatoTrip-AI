"""
ユーザー関連のPydanticスキーマ
"""
from pydantic import BaseModel, EmailStr
from typing import Optional


class UserBase(BaseModel):
    """ユーザーベーススキーマ"""
    username: str
    email: EmailStr
    name: str
    avatar: Optional[str] = None
    role: str = "user"


class UserCreate(UserBase):
    """ユーザー作成スキーマ"""
    password: str


class UserUpdate(BaseModel):
    """ユーザー更新スキーマ"""
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    avatar: Optional[str] = None


class UserResponse(UserBase):
    """ユーザーレスポンススキーマ"""
    id: str
    is_active: bool
    
    class Config:
        from_attributes = True

