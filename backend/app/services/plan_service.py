"""
プランサービス
"""
from sqlalchemy.orm import Session
from app.models.plan import Plan
from app.models.user import User
from typing import List, Optional
from fastapi import HTTPException, status
import uuid
from datetime import datetime


def create_plan(db: Session, user_id: str, plan_data: dict) -> Plan:
    """プランを作成"""
    plan = Plan(
        id=str(uuid.uuid4()),
        user_id=user_id,
        title=plan_data["title"],
        area=plan_data.get("area", ""),
        days=plan_data["days"],
        people=plan_data.get("people"),
        budget=plan_data.get("budget"),
        thumbnail=plan_data.get("thumbnail"),
        spots=plan_data["spots"],
        grounding_urls=plan_data.get("grounding_urls")
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def get_user_plans(db: Session, user_id: str, skip: int = 0, limit: int = 100) -> List[Plan]:
    """ユーザーのプラン一覧を取得"""
    return db.query(Plan).filter(
        Plan.user_id == user_id
    ).order_by(Plan.created_at.desc()).offset(skip).limit(limit).all()


def get_plan(db: Session, plan_id: str, user_id: Optional[str] = None) -> Optional[Plan]:
    """プランを取得"""
    query = db.query(Plan).filter(Plan.id == plan_id)
    if user_id:
        query = query.filter(Plan.user_id == user_id)
    return query.first()


def update_plan(db: Session, plan_id: str, user_id: str, plan_data: dict) -> Plan:
    """プランを更新"""
    plan = get_plan(db, plan_id, user_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="プランが見つかりません"
        )
    
    # 更新
    if "title" in plan_data:
        plan.title = plan_data["title"]
    if "area" in plan_data:
        plan.area = plan_data["area"]
    if "days" in plan_data:
        plan.days = plan_data["days"]
    if "people" in plan_data:
        plan.people = plan_data["people"]
    if "budget" in plan_data:
        plan.budget = plan_data["budget"]
    if "thumbnail" in plan_data:
        plan.thumbnail = plan_data["thumbnail"]
    if "spots" in plan_data:
        plan.spots = plan_data["spots"]
    if "grounding_urls" in plan_data:
        plan.grounding_urls = plan_data["grounding_urls"]
    
    plan.updated_at = datetime.now()
    db.commit()
    db.refresh(plan)
    return plan


def delete_plan(db: Session, plan_id: str, user_id: str) -> bool:
    """プランを削除"""
    plan = get_plan(db, plan_id, user_id)
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="プランが見つかりません"
        )
    
    db.delete(plan)
    db.commit()
    return True

