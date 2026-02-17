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
    # excluded_spotsはデータベースに保存しない（レスポンス専用）
    plan_dict = {k: v for k, v in plan_data.items() if k != "excluded_spots"}
    
    # 必須フィールドのバリデーション
    if not plan_dict.get("title"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="プランのタイトルは必須です"
        )
    if not plan_dict.get("days"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="プランの日数は必須です"
        )
    if not plan_dict.get("spots"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="プランのスポットは必須です"
        )
    
    # ユーザーの存在確認
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"ユーザーID '{user_id}' が見つかりません"
        )
    
    # 予算を数値に変換（文字列の場合）
    budget = plan_dict.get("budget")
    if budget is not None:
        if isinstance(budget, str):
            try:
                budget = float(budget)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"予算の値が無効です: {budget}"
                )
    
    plan = Plan(
        id=str(uuid.uuid4()),
        user_id=user_id,
        title=plan_dict["title"],
        area=plan_dict.get("area", ""),
        days=plan_dict["days"],
        people=plan_dict.get("people"),
        budget=budget,
        thumbnail=plan_dict.get("thumbnail"),
        spots=plan_dict["spots"],
        grounding_urls=plan_dict.get("grounding_urls"),
        check_in_date=plan_dict.get("check_in_date"),
        check_out_date=plan_dict.get("check_out_date")
    )
    db.add(plan)
    try:
        db.commit()
        db.refresh(plan)
    except Exception as e:
        db.rollback()
        
        # エラーの種類に応じて詳細なメッセージを返す
        error_str = str(e)
        error_type = type(e).__name__
        
        # 外部キー制約違反
        if "FOREIGN KEY constraint failed" in error_str or "foreign key" in error_str.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"データベース制約エラー: ユーザーID '{user_id}' が存在しないか、無効です。エラー詳細: {error_str}"
            )
        # 必須フィールドエラー
        elif "NOT NULL constraint failed" in error_str or "NOT NULL" in error_str:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"必須フィールドが不足しています。エラー詳細: {error_str}"
            )
        # その他のデータベースエラー
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"プランの作成に失敗しました。エラー: {error_type} - {error_str}"
            )
    
    # excluded_spotsをplanオブジェクトに一時的に追加（レスポンス用）
    if "excluded_spots" in plan_data:
        plan.excluded_spots = plan_data["excluded_spots"]
    
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
    if "is_favorite" in plan_data:
        plan.is_favorite = plan_data["is_favorite"]
    if "folder_id" in plan_data:
        plan.folder_id = plan_data["folder_id"]
    if "check_in_date" in plan_data:
        plan.check_in_date = plan_data["check_in_date"]
    if "check_out_date" in plan_data:
        plan.check_out_date = plan_data["check_out_date"]
    
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
    
    if plan.is_favorite:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="お気に入りに登録されたプランは削除できません"
        )
    
    db.delete(plan)
    db.commit()
    return True

