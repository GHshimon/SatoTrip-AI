"""
ユーザー設定（プリファレンス）モデル
User と1対1。新規テーブルのため起動時の create_all で自動作成される
（既存 users テーブルにカラム追加するとマイグレーションが必要になるため別テーブルにする）
"""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.utils.database import Base


class UserPreferences(Base):
    """ユーザー設定テーブル"""
    __tablename__ = "user_preferences"

    user_id = Column(String, ForeignKey("users.id"), primary_key=True)
    # 通知設定
    notifications_enabled = Column(Boolean, nullable=False, default=True)
    email_notifications = Column(Boolean, nullable=False, default=True)
    # 言語（'ja' / 'en' など）
    language = Column(String, nullable=False, default="ja")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", backref="preferences")
