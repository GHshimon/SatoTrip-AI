"""
認証APIエンドポイント
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.utils.database import get_db
from app.schemas.auth import (
    UserRegister, UserLogin, TokenResponse, TokenRefresh,
    PasswordResetRequest, PasswordResetConfirm, GoogleLoginRequest,
)
from app.schemas.user import UserResponse
from app.services.auth_service import create_user, authenticate_user
from app.services import password_reset_service, google_auth_service
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


@router.post("/password-reset/request", status_code=status.HTTP_200_OK)
async def password_reset_request(
    payload: PasswordResetRequest,
    db: Session = Depends(get_db)
):
    """
    パスワードリセットを要求する。メールアドレスの存在有無に関わらず同じ応答を返す
    （アカウント列挙攻撃を防ぐため）。登録済みならリセットリンクをメール送信（SMTP未設定時はログ出力）。
    """
    password_reset_service.request_password_reset(db, payload.email)
    return {"message": "パスワード再設定用のメールを送信しました（登録済みの場合）"}


@router.post("/password-reset/confirm", status_code=status.HTTP_200_OK)
async def password_reset_confirm(
    payload: PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    """トークンを検証して新しいパスワードを設定する"""
    ok = password_reset_service.reset_password(db, payload.token, payload.new_password)
    if not ok:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="リンクが無効か有効期限が切れています。お手数ですが再度お試しください。"
        )
    return {"message": "パスワードを再設定しました"}


@router.post("/google", response_model=TokenResponse)
async def google_login(
    payload: GoogleLoginRequest,
    db: Session = Depends(get_db)
):
    """
    Google Identity Services の ID トークンでログイン/新規登録する。
    GOOGLE_CLIENT_ID 未設定時は 503。
    """
    if not google_auth_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Googleログインは現在利用できません（サーバー未設定）"
        )
    idinfo = google_auth_service.verify_google_id_token(payload.id_token)
    user = google_auth_service.get_or_create_google_user(db, idinfo)

    token = generate_token(user_id=user.id, username=user.username, email=user.email)
    return TokenResponse(
        access_token=token,
        token_type="bearer",
        user_id=user.id,
        username=user.username,
        email=user.email,
        role=user.role,
    )

