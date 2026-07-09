"""
ユーザー管理APIエンドポイント
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
from app.utils.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import (
    UserResponse,
    UserUpdate,
    UserPreferencesResponse,
    UserPreferencesUpdate,
    PasswordChangeRequest,
)
from app.services.user_service import update_user
from app.services.plan_service import get_user_plans
from app.services import preferences_service
from app.schemas.plan import PlanResponse
from app.utils.security import hash_password, verify_password
from app.utils.storage import save_avatar, ALLOWED_IMAGE_TYPES
from app.config import settings

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """現在のユーザー情報取得"""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ユーザー情報更新"""
    user_dict = user_data.model_dump(exclude_unset=True)
    updated_user = update_user(db, current_user.id, user_dict)
    return updated_user


@router.get("/me/plans", response_model=List[PlanResponse])
async def get_current_user_plans(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """ユーザーのプラン一覧（/api/plansのエイリアス）"""
    plans = get_user_plans(db, current_user.id, skip, limit)
    return plans


@router.get("/me/preferences", response_model=UserPreferencesResponse)
async def get_my_preferences(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """現在のユーザーの設定を取得（無ければデフォルトを作成）"""
    return preferences_service.get_or_create_preferences(db, current_user.id)


@router.put("/me/preferences", response_model=UserPreferencesResponse)
async def update_my_preferences(
    prefs: UserPreferencesUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """現在のユーザーの設定を更新"""
    return preferences_service.update_preferences(
        db, current_user.id, prefs.model_dump(exclude_unset=True)
    )


@router.post("/me/avatar", response_model=UserResponse)
async def upload_my_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """アバター画像をアップロードして現在のユーザーに設定する"""
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="対応していない画像形式です（JPEG / PNG / WebP / GIF のみ）"
        )
    content = await file.read()
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ファイルが空です"
        )
    if len(content) > settings.AVATAR_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"ファイルサイズが大きすぎます（上限 {settings.AVATAR_MAX_BYTES // (1024 * 1024)}MB）"
        )
    url = save_avatar(content, file.content_type)
    current_user.avatar = url
    db.commit()
    db.refresh(current_user)
    return current_user


@router.put("/me/password", status_code=status.HTTP_200_OK)
async def change_my_password(
    payload: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """現在のユーザーのパスワードを変更する（現在のパスワード検証必須）"""
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="現在のパスワードが正しくありません"
        )
    if verify_password(payload.new_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="新しいパスワードは現在のパスワードと異なる必要があります"
        )
    current_user.hashed_password = hash_password(payload.new_password)
    db.commit()
    return {"message": "パスワードを変更しました"}

