"""
Googleログインサービス（Google Identity Services の ID トークン検証方式）
フロントで取得した ID トークンをサーバーで検証し、find-or-create でユーザーを解決する。
GOOGLE_CLIENT_ID 未設定時は利用不可。
"""
import uuid
import secrets
import logging
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user import User
from app.utils.security import hash_password
from app.config import settings

logger = logging.getLogger(__name__)


def is_configured() -> bool:
    return bool(settings.GOOGLE_CLIENT_ID)


def verify_google_id_token(id_token_str: str) -> dict:
    """
    Google の ID トークンを検証し、ペイロード（email, name, sub 等）を返す。
    検証失敗時は 401。
    """
    # 遅延 import（google-auth 未導入環境でモジュール読み込み自体は失敗させない）
    from google.oauth2 import id_token as google_id_token
    from google.auth.transport import requests as google_requests

    try:
        idinfo = google_id_token.verify_oauth2_token(
            id_token_str,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except ValueError as e:
        logger.warning("Google IDトークン検証失敗: %s", str(e))
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Googleトークンの検証に失敗しました"
        )

    if not idinfo.get("email_verified", False):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Googleアカウントのメールが未確認です"
        )
    return idinfo


def get_or_create_google_user(db: Session, idinfo: dict) -> User:
    """
    検証済みペイロードから、既存ユーザーを解決するか新規作成する。
    """
    email = idinfo.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Googleアカウントからメールを取得できませんでした"
        )

    user = db.query(User).filter(User.email == email).first()
    if user:
        return user

    # 新規ユーザー作成。username はメールのローカル部を基本に一意化する。
    base_username = (email.split("@")[0] or "user")[:20]
    username = base_username
    while db.query(User).filter(User.username == username).first():
        username = f"{base_username}_{secrets.token_hex(3)}"

    user = User(
        id=str(uuid.uuid4()),
        username=username,
        email=email,
        # OAuthユーザーはパスワードログインしないが、NOT NULL のためランダム値を設定
        hashed_password=hash_password(secrets.token_urlsafe(32)),
        name=idinfo.get("name") or base_username,
        avatar=idinfo.get("picture"),
        role="user",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    logger.info("Googleログインで新規ユーザーを作成しました")
    return user
