"""
ユーザーサービス
"""
from sqlalchemy.orm import Session
from app.models.user import User
from typing import Optional
from fastapi import HTTPException, status


def get_user(db: Session, user_id: str) -> Optional[User]:
    """ユーザーを取得"""
    return db.query(User).filter(User.id == user_id).first()


def update_user(db: Session, user_id: str, user_data: dict) -> User:
    """ユーザーを更新"""
    user = get_user(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ユーザーが見つかりません"
        )
    
    # 更新
    if "name" in user_data and user_data["name"] is not None:
        user.name = user_data["name"]
    if "email" in user_data and user_data["email"] is not None:
        # メールアドレスの重複チェック
        existing_user = db.query(User).filter(
            User.email == user_data["email"],
            User.id != user_id
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="このメールアドレスは既に使用されています"
            )
        user.email = user_data["email"]
    if "avatar" in user_data:
        user.avatar = user_data["avatar"]
    
    db.commit()
    db.refresh(user)
    return user

