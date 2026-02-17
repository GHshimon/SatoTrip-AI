"""
認証APIエンドポイント
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.utils.database import get_db
from app.schemas.auth import UserRegister, UserLogin, TokenResponse, TokenRefresh
from app.schemas.user import UserResponse
from app.services.auth_service import create_user, authenticate_user
from app.utils.jwt_manager import generate_token, refresh_token

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    db: Session = Depends(get_db)
):
    """ユーザー登録"""
    user = create_user(
        db=db,
        username=user_data.username,
        email=user_data.email,
        password=user_data.password,
        name=user_data.name
    )
    
    # トークン生成
    token = generate_token(
        user_id=user.id,
        username=user.username,
        email=user.email
    )
    
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        username=user.username,
        email=user.email,
        role=user.role
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    """ログイン"""
    user = authenticate_user(
        db=db,
        username=login_data.username,
        password=login_data.password
    )
    
    # トークン生成
    token = generate_token(
        user_id=user.id,
        username=user.username,
        email=user.email
    )
    
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        username=user.username,
        email=user.email,
        role=user.role
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh(
    refresh_data: TokenRefresh
):
    """トークンリフレッシュ"""
    is_valid, new_token = refresh_token(refresh_data.refresh_token)
    
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無効なトークンです"
        )
    
    # トークンからユーザー情報を取得（簡易実装）
    from app.utils.jwt_manager import verify_token
    _, payload = verify_token(new_token)
    
    return TokenResponse(
        access_token=new_token,
        token_type="bearer",
        user_id=payload["user_id"],
        username=payload["username"],
        email=payload["email"],
        role="user"  # トークンに含まれていない場合はデフォルト値
    )


@router.post("/logout")
async def logout():
    """ログアウト（クライアント側でトークンを削除）"""
    return {"message": "ログアウトしました"}

