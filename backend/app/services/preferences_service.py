"""
ユーザー設定サービス
"""
from sqlalchemy.orm import Session

from app.models.user_preferences import UserPreferences


def get_or_create_preferences(db: Session, user_id: str) -> UserPreferences:
    """ユーザー設定を取得する。無ければデフォルト値で作成して返す"""
    prefs = db.query(UserPreferences).filter(
        UserPreferences.user_id == user_id
    ).first()
    if not prefs:
        prefs = UserPreferences(user_id=user_id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return prefs


def update_preferences(db: Session, user_id: str, data: dict) -> UserPreferences:
    """ユーザー設定を部分更新する"""
    prefs = get_or_create_preferences(db, user_id)
    for field in ("notifications_enabled", "email_notifications", "language"):
        if field in data and data[field] is not None:
            setattr(prefs, field, data[field])
    db.commit()
    db.refresh(prefs)
    return prefs
