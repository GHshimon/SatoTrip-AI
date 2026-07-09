"""
パスワードリセットトークンモデル
生のトークンはメールリンクにのみ載せ、DBにはハッシュを保存する
"""
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey
from sqlalchemy.sql import func
from app.utils.database import Base
import uuid


class PasswordResetToken(Base):
    """パスワードリセットトークンテーブル"""
    __tablename__ = "password_reset_tokens"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    # 生トークンの sha256 ハッシュ（DBに生の値は保存しない）
    token_hash = Column(String, nullable=False, unique=True, index=True)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
