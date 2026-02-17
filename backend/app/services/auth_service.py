"""
認証サービス
"""
from sqlalchemy.orm import Session
from app.models.user import User
from app.utils.security import (
    hash_password,
    verify_password,
    validate_password,
    check_login_lockout,
    record_login_attempt
)
from app.utils.jwt_manager import generate_token
from fastapi import HTTPException, status


def create_user(db: Session, username: str, email: str, password: str, name: str) -> User:
    """ユーザーを作成"""
    # 既存ユーザーチェック
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="このユーザー名は既に使用されています"
        )
    
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="このメールアドレスは既に使用されています"
        )
    
    # パスワード強度チェック
    is_valid, message = validate_password(password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    # ユーザー作成
    hashed_password = hash_password(password)
    user = User(
        username=username,
        email=email,
        hashed_password=hashed_password,
        name=name,
        role="user"
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, username: str, password: str) -> User:
    """ユーザーを認証"""
    # ロックアウトチェック
    is_locked, lockout_message = check_login_lockout(username)
    if is_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=lockout_message
        )
    
    # ユーザー取得
    user = db.query(User).filter(User.username == username).first()
    if not user:
        record_login_attempt(username, False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザー名またはパスワードが正しくありません"
        )
    
    # パスワード検証
    if not verify_password(password, user.hashed_password):
        record_login_attempt(username, False)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザー名またはパスワードが正しくありません"
        )
    
    # アクティブチェック
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="このアカウントは無効です"
        )
    
    # ログイン成功
    record_login_attempt(username, True)
    return user

