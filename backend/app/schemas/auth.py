"""
認証関連のPydanticスキーマ
"""
from pydantic import BaseModel, EmailStr


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

