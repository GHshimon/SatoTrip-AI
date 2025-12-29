"""
サブスクリプション関連のPydanticスキーマ
"""
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime


class SubscriptionResponse(BaseModel):
    """サブスクリプション情報のレスポンス"""
    id: str
    user_id: str
    plan_name: str
    upgraded_at: datetime
    expires_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class UsageResponse(BaseModel):
    """使用量情報のレスポンス"""
    id: str
    user_id: str
    month: str  # YYYY-MM形式
    count: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class PlanFeaturesResponse(BaseModel):
    """プラン機能のレスポンス"""
    name: str
    price: int
    monthly_plans: int  # -1 は無制限
    features: List[str]
    api_limit: int  # -1 は無制限
    pdf_export: bool
    advanced_optimization: bool


class PlanStatusResponse(BaseModel):
    """プラン生成可能状態のレスポンス"""
    can_generate: bool
    message: str
    remaining: int  # -1 は無制限
    plan_name: str
    plan_features: PlanFeaturesResponse

