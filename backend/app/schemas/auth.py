"""
認証関連のPydanticスキーマ
"""
from pydantic import BaseModel, EmailStr, Field


class UserRegister(BaseModel):
    """ユーザー登録リクエスト"""
    username: str
    email: EmailStr
    password: str
    name: str


class UserLogin(BaseModel):
    """ログインリクエスト"""
    username: str
    password: str


class TokenResponse(BaseModel):
    """トークンレスポンス"""
    access_token: str
    token_type: str = "bearer"
    user_id: str
    username: str
    email: str
    role: str


class TokenRefresh(BaseModel):
    """トークンリフレッシュリクエスト"""
    refresh_token: str


class PasswordResetRequest(BaseModel):
    """パスワードリセット要求リクエスト"""
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """パスワードリセット確定リクエスト"""
    token: str
    new_password: str = Field(min_length=8, description="新しいパスワード（8文字以上）")


class GoogleLoginRequest(BaseModel):
    """Googleログインリクエスト（Google Identity Services の ID トークン）"""
    id_token: str

