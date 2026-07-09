"""
依存性注入
認証などの共通機能を提供
"""
from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.utils.database import get_db
from app.utils.jwt_manager import verify_token
from app.models.user import User
from app.models.api_key import ApiKey
from app.services.api_key_service import get_api_key_by_plain_key, update_api_key_usage
from datetime import datetime
from typing import Optional

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    現在の認証済みユーザーを取得
    JWTトークンからユーザー情報を取得します
    """
    token = credentials.credentials
    is_valid, payload = verify_token(token)
    
    if not is_valid or not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="認証トークンが無効です",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("user_id")
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザーが見つからないか、無効です",
        )
    
    return user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """
    現在の認証済み管理者ユーザーを取得
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="管理者権限が必要です",
        )
    return current_user


async def verify_api_key(
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db)
) -> ApiKey:
    """
    APIキーを検証
    リクエストヘッダーからX-API-Keyを取得して検証します
    """
    
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="APIキーが必要です。X-API-Keyヘッダーを設定してください。",
        )
    
    # APIキーを検証
    
    api_key = get_api_key_by_plain_key(db, x_api_key)
    
    
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無効なAPIキーです",
        )
    
    # 有効性チェック
    if not api_key.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="このAPIキーは無効です",
        )
    
    # 有効期限チェック
    if api_key.expires_at and datetime.now() > api_key.expires_at:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="このAPIキーは有効期限が切れています",
        )
    
    # 使用量を更新
    update_api_key_usage(db, api_key.id)
    
    return api_key

