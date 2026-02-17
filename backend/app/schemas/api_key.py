"""
APIキー関連のPydanticスキーマ
"""
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime


class ApiKeyCreate(BaseModel):
    """APIキー作成リクエスト"""
    name: str = Field(..., description="APIキーの名前/説明")
    user_id: Optional[str] = Field(None, description="所有者のユーザーID（オプション）")
    rate_limit_per_minute: int = Field(10, ge=1, le=1000, description="1分間のリクエスト制限")
    rate_limit_per_hour: int = Field(100, ge=1, le=10000, description="1時間のリクエスト制限")
    rate_limit_per_day: int = Field(1000, ge=1, le=100000, description="1日のリクエスト制限")
    monthly_plan_limit: int = Field(100, ge=-1, description="月間プラン生成上限（-1で無制限）")
    expires_at: Optional[datetime] = Field(None, description="有効期限（オプション）")


class ApiKeyUpdate(BaseModel):
    """APIキー更新リクエスト"""
    name: Optional[str] = Field(None, description="APIキーの名前/説明")
    is_active: Optional[bool] = Field(None, description="有効/無効フラグ")
    rate_limit_per_minute: Optional[int] = Field(None, ge=1, le=1000, description="1分間のリクエスト制限")
    rate_limit_per_hour: Optional[int] = Field(None, ge=1, le=10000, description="1時間のリクエスト制限")
    rate_limit_per_day: Optional[int] = Field(None, ge=1, le=100000, description="1日のリクエスト制限")
    monthly_plan_limit: Optional[int] = Field(None, ge=-1, description="月間プラン生成上限（-1で無制限）")
    expires_at: Optional[datetime] = Field(None, description="有効期限（オプション）")


class ApiKeyResponse(BaseModel):
    """APIキーレスポンス（キー自体は初回のみ表示）"""
    id: str
    name: str
    user_id: Optional[str]
    is_active: bool
    rate_limit_per_minute: int
    rate_limit_per_hour: int
    rate_limit_per_day: int
    monthly_plan_limit: int
    created_at: datetime
    last_used_at: Optional[datetime]
    expires_at: Optional[datetime]
    updated_at: Optional[datetime]
    # キー自体は初回作成時のみ返す（セキュリティのため）
    key: Optional[str] = Field(None, description="APIキー（初回作成時のみ表示）")
    
    class Config:
        from_attributes = True


class ApiKeyListResponse(BaseModel):
    """APIキー一覧レスポンス"""
    keys: list[ApiKeyResponse]
    total: int


class ApiKeyUsageResponse(BaseModel):
    """APIキー使用量レスポンス"""
    id: str
    api_key_id: str
    month: str
    request_count: int
    plan_generation_count: int
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

