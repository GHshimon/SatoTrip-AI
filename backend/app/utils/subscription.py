"""
サブスクリプション管理機能
有料プラン、使用量追跡、制限チェック
"""
import os
from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from app.models.subscription import Subscription, Usage

# #region agent log
LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".cursor", "debug.log")
def _log(hypothesis_id, location, message, data):
    try:
        import json as _json
        log_entry = {
            "sessionId": "debug-session",
            "runId": "run1",
            "hypothesisId": hypothesis_id,
            "location": location,
            "message": message,
            "data": data,
            "timestamp": int(datetime.now().timestamp() * 1000)
        }
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(_json.dumps(log_entry, ensure_ascii=False) + "\n")
    except: pass
# #endregion

# プラン定義
PLANS = {
    "free": {
        "name": "無料プラン",
        "price": 0,
        "monthly_plans": 5,
        "features": ["basic_plan", "ads"],
        "api_limit": 5,
        "pdf_export": False,
        "advanced_optimization": False,
    },
    "basic": {
        "name": "ベーシックプラン",
        "price": 980,
        "monthly_plans": 50,
        "features": ["all_basic", "no_ads", "pdf_export"],
        "api_limit": 50,
        "pdf_export": True,
        "advanced_optimization": False,
    },
    "premium": {
        "name": "プレミアムプラン",
        "price": 2980,
        "monthly_plans": -1,  # unlimited
        "features": ["all_features", "priority_support", "custom_plans"],
        "api_limit": -1,  # unlimited
        "pdf_export": True,
        "advanced_optimization": True,
    }
}


def get_user_plan(db: Session, user_id: str) -> str:
    """ユーザーのプランを取得（デフォルト: free）"""
    subscription = db.query(Subscription).filter(
        Subscription.user_id == user_id
    ).first()
    
    if not subscription:
        return "free"
    
    # 有効期限チェック
    if subscription.expires_at and datetime.now() > subscription.expires_at:
        return "free"
    
    return subscription.plan_name


def can_generate_plan(db: Session, user_id: str) -> Tuple[bool, str, int]:
    """
    プラン生成可能かチェック
    Returns: (can_generate, message, remaining)
    """
    # #region agent log
    _log("A", "subscription.py:59", "can_generate_plan called", {"user_id": user_id})
    # #endregion
    
    plan_name = get_user_plan(db, user_id)
    # #region agent log
    _log("A", "subscription.py:64", "plan_name retrieved", {"plan_name": plan_name, "user_id": user_id})
    # #endregion
    
    plan = PLANS[plan_name]
    # #region agent log
    _log("C", "subscription.py:65", "plan retrieved", {"plan_name": plan_name, "monthly_plans": plan.get("monthly_plans")})
    # #endregion
    
    # 無制限プラン
    if plan["monthly_plans"] == -1:
        # #region agent log
        _log("C", "subscription.py:68", "unlimited plan detected", {"plan_name": plan_name})
        # #endregion
        return True, "", -1
    
    # 使用量取得
    now = datetime.now()
    current_month = f"{now.year}-{now.month:02d}"
    # #region agent log
    _log("B", "subscription.py:73", "current_month calculated", {"current_month": current_month, "now": now.isoformat(), "year": now.year, "month": now.month})
    # #endregion
    
    usage = db.query(Usage).filter(
        and_(
            Usage.user_id == user_id,
            Usage.month == current_month
        )
    ).first()
    # #region agent log
    _log("E", "subscription.py:75", "usage queried from db", {"user_id": user_id, "current_month": current_month, "usage_exists": usage is not None})
    # #endregion
    
    monthly_usage = usage.count if usage else 0
    # #region agent log
    _log("B", "subscription.py:82", "monthly_usage retrieved", {"current_month": current_month, "monthly_usage": monthly_usage})
    # #endregion
    
    remaining = plan["monthly_plans"] - monthly_usage
    # #region agent log
    _log("D", "subscription.py:83", "remaining calculated", {"monthly_plans": plan["monthly_plans"], "monthly_usage": monthly_usage, "remaining": remaining})
    # #endregion
    
    if remaining > 0:
        # #region agent log
        _log("D", "subscription.py:85", "remaining > 0, allowing", {"remaining": remaining})
        # #endregion
        return True, f"残り{remaining}回", remaining
    else:
        # #region agent log
        _log("D", "subscription.py:87", "remaining <= 0, blocking", {"remaining": remaining, "monthly_plans": plan["monthly_plans"], "monthly_usage": monthly_usage})
        # #endregion
        return False, f"今月のプラン生成上限に達しました（{monthly_usage}/{plan['monthly_plans']}回使用済み）。来月までお待ちいただくか、プランをアップグレードしてください。", 0


def record_plan_generation(db: Session, user_id: str):
    """プラン生成を記録"""
    now = datetime.now()
    current_month = f"{now.year}-{now.month:02d}"
    
    usage = db.query(Usage).filter(
        and_(
            Usage.user_id == user_id,
            Usage.month == current_month
        )
    ).first()
    
    if usage:
        usage.count += 1
        usage.updated_at = datetime.now()
    else:
        usage = Usage(
            user_id=user_id,
            month=current_month,
            count=1
        )
        db.add(usage)
    
    db.commit()


def upgrade_plan(db: Session, user_id: str, plan_name: str, months: int = 1):
    """プランをアップグレード"""
    expires_at = datetime.now() + timedelta(days=30 * months)
    
    subscription = db.query(Subscription).filter(
        Subscription.user_id == user_id
    ).first()
    
    if subscription:
        subscription.plan_name = plan_name
        subscription.upgraded_at = datetime.now()
        subscription.expires_at = expires_at
        subscription.updated_at = datetime.now()
    else:
        subscription = Subscription(
            user_id=user_id,
            plan_name=plan_name,
            expires_at=expires_at
        )
        db.add(subscription)
    
    db.commit()


def get_plan_features(db: Session, user_id: str) -> Dict[str, Any]:
    """ユーザーのプランの機能を取得"""
    plan_name = get_user_plan(db, user_id)
    return PLANS[plan_name]


def check_feature_access(db: Session, user_id: str, feature: str) -> bool:
    """特定機能へのアクセス権をチェック"""
    plan_features = get_plan_features(db, user_id)
    plan = PLANS[get_user_plan(db, user_id)]
    
    if feature == "pdf_export":
        return plan["pdf_export"]
    elif feature == "advanced_optimization":
        return plan["advanced_optimization"]
    elif feature == "no_ads":
        return "no_ads" in plan_features["features"]
    
    return True  # デフォルトは許可

