"""
ユーザー関連のPydanticスキーマ
"""
from pydantic import BaseModel, EmailStr, Field
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


class UserPreferencesResponse(BaseModel):
    """ユーザー設定レスポンススキーマ"""
    notifications_enabled: bool
    email_notifications: bool
    language: str

    class Config:
        from_attributes = True


class UserPreferencesUpdate(BaseModel):
    """ユーザー設定更新スキーマ（部分更新）"""
    notifications_enabled: Optional[bool] = None
    email_notifications: Optional[bool] = None
    language: Optional[str] = None


class PasswordChangeRequest(BaseModel):
    """パスワード変更スキーマ"""
    current_password: str
    new_password: str = Field(min_length=8, description="新しいパスワード（8文字以上）")


class AccountDeleteRequest(BaseModel):
    """退会（アカウント削除）確認スキーマ"""
    confirm: str = Field(description="確認のため自分のユーザー名を正確に入力する")

