"""
パスワードリセットサービス
"""
import hashlib
import secrets
import logging
from datetime import datetime, timedelta
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.password_reset_token import PasswordResetToken
from app.utils.security import hash_password
from app.utils.email_sender import send_email
from app.config import settings

logger = logging.getLogger(__name__)


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def request_password_reset(db: Session, email: str) -> None:
    """
    リセットを要求する。ユーザーが存在すればトークンを発行しメール送信（またはdevログ）。
    メールアドレスの存在有無を漏らさないため、戻り値は常に None（呼び出し側は常に200を返す）。
    """
    user = db.query(User).filter(User.email == email).first()
    if not user:
        # 存在しないメールでも同じ挙動にして列挙攻撃を防ぐ
        logger.info("パスワードリセット要求: 未登録のメール（何もしない）")
        return

    # 既存の未使用トークンを無効化（1通のみ有効にする）
    db.query(PasswordResetToken).filter(
        PasswordResetToken.user_id == user.id,
        PasswordResetToken.used == False  # noqa: E712
    ).update({"used": True})

    raw_token = secrets.token_urlsafe(32)
    reset = PasswordResetToken(
        user_id=user.id,
        token_hash=_hash_token(raw_token),
        expires_at=datetime.utcnow() + timedelta(minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES),
        used=False,
    )
    db.add(reset)
    db.commit()

    reset_url = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password?token={raw_token}"
    body = (
        f"{user.name} 様\n\n"
        "SatoTrip のパスワード再設定のリクエストを受け付けました。\n"
        "以下のリンクから新しいパスワードを設定してください（有効期限"
        f"{settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES}分）:\n\n"
        f"{reset_url}\n\n"
        "このリクエストに心当たりがない場合は、このメールを破棄してください。"
    )
    send_email(user.email, "【SatoTrip】パスワード再設定のご案内", body)


def reset_password(db: Session, raw_token: str, new_password: str) -> bool:
    """
    トークンを検証してパスワードを更新する。成功で True。
    無効・期限切れ・使用済みトークンは False。
    """
    token_hash = _hash_token(raw_token)
    token = db.query(PasswordResetToken).filter(
        PasswordResetToken.token_hash == token_hash
    ).first()

    if not token or token.used or token.expires_at < datetime.utcnow():
        return False

    user = db.query(User).filter(User.id == token.user_id).first()
    if not user:
        return False

    user.hashed_password = hash_password(new_password)
    token.used = True
    db.commit()
    return True
