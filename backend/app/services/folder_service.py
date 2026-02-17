"""
フォルダサービス
"""
from sqlalchemy.orm import Session
from app.models.plan_folder import PlanFolder
from app.models.plan import Plan
from typing import List, Optional
from fastapi import HTTPException, status
import uuid
from datetime import datetime


def create_folder(db: Session, user_id: str, folder_data: dict) -> PlanFolder:
    """フォルダを作成"""
    # #region agent log
    import json
    log_data = {"location": "folder_service.py:13", "message": "create_folder called", "data": {"name": folder_data.get("name", ""), "name_length": len(folder_data.get("name", "")), "name_trimmed_length": len(folder_data.get("name", "").strip()) if folder_data.get("name") else 0}, "timestamp": int(datetime.now().timestamp() * 1000), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "C"}
    try:
        with open(r"c:\projects\SatoTrip\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps(log_data, ensure_ascii=False) + "\n")
    except: pass
    # #endregion
    folder = PlanFolder(
        id=str(uuid.uuid4()),
        user_id=user_id,
        name=folder_data["name"],
        parent_id=folder_data.get("parent_id")
    )
    # #region agent log
    log_data = {"location": "folder_service.py:24", "message": "Folder created in DB", "data": {"folder_id": folder.id, "name": folder.name}, "timestamp": int(datetime.now().timestamp() * 1000), "sessionId": "debug-session", "runId": "run1", "hypothesisId": "C"}
    try:
        with open(r"c:\projects\SatoTrip\.cursor\debug.log", "a", encoding="utf-8") as f:
            f.write(json.dumps(log_data, ensure_ascii=False) + "\n")
    except: pass
    # #endregion
    db.add(folder)
    db.commit()
    db.refresh(folder)
    return folder


def get_folders(db: Session, user_id: str) -> List[PlanFolder]:
    """ユーザーの全フォルダを取得"""
    return db.query(PlanFolder).filter(
        PlanFolder.user_id == user_id
    ).order_by(PlanFolder.created_at.desc()).all()


def get_folder(db: Session, folder_id: str, user_id: str) -> Optional[PlanFolder]:
    """フォルダを取得"""
    return db.query(PlanFolder).filter(
        PlanFolder.id == folder_id,
        PlanFolder.user_id == user_id
    ).first()


def update_folder(db: Session, folder_id: str, user_id: str, folder_data: dict) -> PlanFolder:
    """フォルダを更新"""
    folder = get_folder(db, folder_id, user_id)
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="フォルダが見つかりません"
        )
    
    if "name" in folder_data and folder_data["name"]:
        folder.name = folder_data["name"]
    if "parent_id" in folder_data:
        # Check for circular reference if moving
        if folder_data["parent_id"] == folder_id:
             raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="自分自身を親にすることはできません"
            )
        folder.parent_id = folder_data["parent_id"]
    
    folder.updated_at = datetime.now()
    db.commit()
    db.refresh(folder)
    return folder


def delete_folder(db: Session, folder_id: str, user_id: str) -> bool:
    """フォルダを削除"""
    folder = get_folder(db, folder_id, user_id)
    if not folder:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="フォルダが見つかりません"
        )
    
    # 子フォルダやプランの処理は？
    # 今回は単純に、中身がある場合は削除不可とするか、ルートに移動するか。
    # 実装計画では「ルートに移動」か「削除不可」。
    # ここでは安全のため、紐づくプランや子フォルダのparent_id/folder_idをNULLにする（ルートへ移動）
    
    # 子フォルダをルートへ
    children = db.query(PlanFolder).filter(PlanFolder.parent_id == folder_id).all()
    for child in children:
        child.parent_id = None
        
    # プランをルートへ
    plans = db.query(Plan).filter(Plan.folder_id == folder_id).all()
    for plan in plans:
        plan.folder_id = None
        
    db.delete(folder)
    db.commit()
    return True
