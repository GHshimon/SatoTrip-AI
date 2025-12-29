
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.utils.database import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import UserResponse
from app.services.settings_service import get_settings, update_settings
from app.services.admin_service import get_admin_stats, get_system_alerts, get_trending_areas

router = APIRouter(prefix="/api/admin", tags=["admin"])

def get_current_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user

# --- User Management ---

@router.get("/users", response_model=List[UserResponse])
async def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """ユーザー一覧取得（管理者のみ）"""
    users = db.query(User).offset(skip).limit(limit).all()
    return users

@router.put("/users/{user_id}/role")
async def update_user_role(
    user_id: str,
    role: str,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """ユーザーロール更新（管理者のみ）"""
    if role not in ["user", "admin"]:
        raise HTTPException(status_code=400, detail="Invalid role")
        
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.role = role
    db.commit()
    db.refresh(user)
    return {"message": "Role updated", "user_id": user.id, "new_role": user.role}

@router.put("/users/{user_id}/status")
async def update_user_status(
    user_id: str,
    is_active: bool,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """ユーザーステータス更新（管理者のみ）"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    user.is_active = is_active
    db.commit()
    db.refresh(user)
    return {"message": "Status updated", "user_id": user.id, "is_active": user.is_active}

# --- Settings Management ---

@router.get("/settings")
async def get_system_settings(
    admin: User = Depends(get_current_admin)
):
    """システム設定取得（管理者のみ）"""
    return get_settings()

@router.put("/settings")
async def update_system_settings(
    settings: Dict[str, Any],
    admin: User = Depends(get_current_admin)
):
    """システム設定更新（管理者のみ）"""
    return update_settings(settings)

# --- Statistics & Dashboard ---

@router.get("/stats")
async def get_stats(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """統計情報取得（管理者のみ）"""
    return get_admin_stats(db)

@router.get("/alerts")
async def get_alerts(
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """システムアラート取得（管理者のみ）"""
    return get_system_alerts(db)

@router.get("/trending-areas")
async def get_trending_areas_endpoint(
    limit: int = 3,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin)
):
    """人気急上昇エリア取得（管理者のみ）"""
    return get_trending_areas(db, limit)
