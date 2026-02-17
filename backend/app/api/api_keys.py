"""
APIキー管理APIエンドポイント
管理者のみがアクセス可能
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.utils.database import get_db
from app.dependencies import get_current_admin_user
from app.models.user import User
from app.models.api_key import ApiKey, ApiKeyUsage
from app.schemas.api_key import (
    ApiKeyCreate,
    ApiKeyUpdate,
    ApiKeyResponse,
    ApiKeyListResponse,
    ApiKeyUsageResponse
)
from app.services.api_key_service import (
    create_api_key,
    get_api_key_usage
)
from datetime import datetime

router = APIRouter(prefix="/api/admin/api-keys", tags=["api-keys"])


@router.post("", response_model=ApiKeyResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key_endpoint(
    request: ApiKeyCreate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """APIキー作成（管理者のみ）"""
    # user_idが指定されていない場合は、現在のユーザー（管理者）を所有者として設定
    owner_user_id = request.user_id if request.user_id else current_user.id
    
    api_key, plain_key = create_api_key(
        db=db,
        name=request.name,
        user_id=owner_user_id,
        rate_limit_per_minute=request.rate_limit_per_minute,
        rate_limit_per_hour=request.rate_limit_per_hour,
        rate_limit_per_day=request.rate_limit_per_day,
        monthly_plan_limit=request.monthly_plan_limit,
        expires_at=request.expires_at
    )
    
    # レスポンスには平文のキーを含める（初回のみ）
    response_data = ApiKeyResponse(
        id=api_key.id,
        name=api_key.name,
        user_id=api_key.user_id,
        is_active=api_key.is_active,
        rate_limit_per_minute=api_key.rate_limit_per_minute,
        rate_limit_per_hour=api_key.rate_limit_per_hour,
        rate_limit_per_day=api_key.rate_limit_per_day,
        monthly_plan_limit=api_key.monthly_plan_limit,
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
        expires_at=api_key.expires_at,
        updated_at=api_key.updated_at,
        key=plain_key  # 初回のみ表示
    )
    
    return response_data


@router.get("", response_model=ApiKeyListResponse)
async def list_api_keys(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """APIキー一覧取得（管理者のみ）"""
    api_keys = db.query(ApiKey).offset(skip).limit(limit).all()
    total = db.query(ApiKey).count()
    
    keys_response = [
        ApiKeyResponse(
            id=key.id,
            name=key.name,
            user_id=key.user_id,
            is_active=key.is_active,
            rate_limit_per_minute=key.rate_limit_per_minute,
            rate_limit_per_hour=key.rate_limit_per_hour,
            rate_limit_per_day=key.rate_limit_per_day,
            monthly_plan_limit=key.monthly_plan_limit,
            created_at=key.created_at,
            last_used_at=key.last_used_at,
            expires_at=key.expires_at,
            updated_at=key.updated_at,
            key=None  # 一覧ではキーを表示しない
        )
        for key in api_keys
    ]
    
    return ApiKeyListResponse(keys=keys_response, total=total)


@router.get("/{key_id}", response_model=ApiKeyResponse)
async def get_api_key(
    key_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """APIキー詳細取得（管理者のみ）"""
    api_key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="APIキーが見つかりません"
        )
    
    return ApiKeyResponse(
        id=api_key.id,
        name=api_key.name,
        user_id=api_key.user_id,
        is_active=api_key.is_active,
        rate_limit_per_minute=api_key.rate_limit_per_minute,
        rate_limit_per_hour=api_key.rate_limit_per_hour,
        rate_limit_per_day=api_key.rate_limit_per_day,
        monthly_plan_limit=api_key.monthly_plan_limit,
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
        expires_at=api_key.expires_at,
        updated_at=api_key.updated_at,
        key=None  # 詳細でもキーは表示しない（セキュリティのため）
    )


@router.put("/{key_id}", response_model=ApiKeyResponse)
async def update_api_key(
    key_id: str,
    request: ApiKeyUpdate,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """APIキー更新（管理者のみ）"""
    api_key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="APIキーが見つかりません"
        )
    
    # 更新可能なフィールドを更新
    if request.name is not None:
        api_key.name = request.name
    if request.is_active is not None:
        api_key.is_active = request.is_active
    if request.rate_limit_per_minute is not None:
        api_key.rate_limit_per_minute = request.rate_limit_per_minute
    if request.rate_limit_per_hour is not None:
        api_key.rate_limit_per_hour = request.rate_limit_per_hour
    if request.rate_limit_per_day is not None:
        api_key.rate_limit_per_day = request.rate_limit_per_day
    if request.monthly_plan_limit is not None:
        api_key.monthly_plan_limit = request.monthly_plan_limit
    if request.expires_at is not None:
        api_key.expires_at = request.expires_at
    
    api_key.updated_at = datetime.now()
    db.commit()
    db.refresh(api_key)
    
    return ApiKeyResponse(
        id=api_key.id,
        name=api_key.name,
        user_id=api_key.user_id,
        is_active=api_key.is_active,
        rate_limit_per_minute=api_key.rate_limit_per_minute,
        rate_limit_per_hour=api_key.rate_limit_per_hour,
        rate_limit_per_day=api_key.rate_limit_per_day,
        monthly_plan_limit=api_key.monthly_plan_limit,
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
        expires_at=api_key.expires_at,
        updated_at=api_key.updated_at,
        key=None
    )


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_api_key(
    key_id: str,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """APIキー削除（管理者のみ）"""
    api_key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="APIキーが見つかりません"
        )
    
    db.delete(api_key)
    db.commit()
    return None


@router.get("/{key_id}/usage", response_model=ApiKeyUsageResponse)
async def get_api_key_usage_endpoint(
    key_id: str,
    month: Optional[str] = None,
    current_user: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """APIキー使用量取得（管理者のみ）"""
    api_key = db.query(ApiKey).filter(ApiKey.id == key_id).first()
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="APIキーが見つかりません"
        )
    
    usage = get_api_key_usage(db, key_id, month)
    if not usage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="使用量データが見つかりません"
        )
    
    return ApiKeyUsageResponse(
        id=usage.id,
        api_key_id=usage.api_key_id,
        month=usage.month,
        request_count=usage.request_count,
        plan_generation_count=usage.plan_generation_count,
        created_at=usage.created_at,
        updated_at=usage.updated_at
    )

