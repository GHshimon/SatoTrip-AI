"""
フォルダ管理API
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from app.utils.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.folder import FolderCreate, FolderUpdate, FolderResponse
from app.services import folder_service

router = APIRouter(
    prefix="/api/folders",
    tags=["folders"]
)


@router.post("", response_model=FolderResponse)
async def create_folder(
    folder: FolderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """フォルダ作成"""
    return folder_service.create_folder(db, current_user.id, folder.dict())


@router.get("", response_model=List[FolderResponse])
async def get_folders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """フォルダ一覧取得"""
    return folder_service.get_folders(db, current_user.id)


@router.put("/{folder_id}", response_model=FolderResponse)
async def update_folder(
    folder_id: str,
    folder: FolderUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """フォルダ更新"""
    return folder_service.update_folder(db, folder_id, current_user.id, folder.dict(exclude_unset=True))


@router.delete("/{folder_id}")
async def delete_folder(
    folder_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """フォルダ削除"""
    folder_service.delete_folder(db, folder_id, current_user.id)
    return {"message": "Folder deleted successfully"}
