"""
JWT を使用したセッション管理機能
既存のSatoTripプロジェクトの実装を参考
"""
import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict
from app.config import settings


def generate_token(user_id: str, username: str, email: str) -> str:
    """
    ユーザー情報に基づいて JWT トークンを生成します。
    
    Args:
        user_id: ユーザーの一意の識別子
        username: ユーザー名
        email: ユーザーのメールアドレス
    
    Returns:
        生成された JWT トークン
    """
    payload = {
        "user_id": user_id,
        "username": username,
        "email": email,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(hours=settings.JWT_EXPIRATION_HOURS),
    }
    token = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return token


def verify_token(token: str) -> tuple[bool, Optional[Dict]]:
    """
    JWT トークンを検証し、ペイロードを取得します。
    
    Args:
        token: 検証する JWT トークン
    
    Returns:
        Tuple[bool, Optional[Dict]]: (検証結果, ペイロード)
            - 検証成功: (True, ペイロード辞書)
            - 検証失敗: (False, None)
    """
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return True, payload
    except jwt.ExpiredSignatureError:
        return False, None
    except jwt.InvalidTokenError:
        return False, None


def refresh_token(token: str) -> tuple[bool, Optional[str]]:
    """
    JWT トークンをリフレッシュします。
    
    Args:
        token: リフレッシュするトークン
    
    Returns:
        Tuple[bool, Optional[str]]: (リフレッシュ結果, 新しいトークン)
            - リフレッシュ成功: (True, 新しいトークン)
            - リフレッシュ失敗: (False, None)
    """
    is_valid, payload = verify_token(token)
    if not is_valid:
        return False, None
    
    # 新しいトークンを生成
    new_token = generate_token(
        user_id=payload["user_id"],
        username=payload["username"],
        email=payload["email"],
    )
    return True, new_token

