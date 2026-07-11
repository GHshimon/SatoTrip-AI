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
    
    plan_name = get_user_plan(db, user_id)
    
    plan = PLANS[plan_name]
    
    # 無制限プラン
    if plan["monthly_plans"] == -1:
        return True, "", -1
    
    # 使用量取得
    now = datetime.now()
    current_month = f"{now.year}-{now.month:02d}"
    
    usage = db.query(Usage).filter(
        and_(
            Usage.user_id == user_id,
            Usage.month == current_month
        )
    ).first()
    
    monthly_usage = usage.count if usage else 0
    
    remaining = plan["monthly_plans"] - monthly_usage
    
    if remaining > 0:
        return True, f"残り{remaining}回", remaining
    else:
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


def upgrade_plan(
    db: Session,
    user_id: str,
    plan_name: str,
    months: int = 1,
    stripe_customer_id: Optional[str] = None,
    stripe_subscription_id: Optional[str] = None,
):
    """プランをアップグレード（Stripe の突合用IDも任意で保存する）"""
    expires_at = datetime.now() + timedelta(days=30 * months)

    subscription = db.query(Subscription).filter(
        Subscription.user_id == user_id
    ).first()

    if subscription:
        subscription.plan_name = plan_name
        subscription.upgraded_at = datetime.now()
        subscription.expires_at = expires_at
        subscription.updated_at = datetime.now()
        if stripe_customer_id:
            subscription.stripe_customer_id = stripe_customer_id
        if stripe_subscription_id:
            subscription.stripe_subscription_id = stripe_subscription_id
    else:
        subscription = Subscription(
            user_id=user_id,
            plan_name=plan_name,
            expires_at=expires_at,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
        )
        db.add(subscription)

    db.commit()


def get_subscription_by_stripe_ids(
    db: Session,
    stripe_subscription_id: Optional[str] = None,
    stripe_customer_id: Optional[str] = None,
) -> Optional[Subscription]:
    """Stripe の subscription_id（優先）/ customer_id からサブスクリプションを特定"""
    if stripe_subscription_id:
        subscription = db.query(Subscription).filter(
            Subscription.stripe_subscription_id == stripe_subscription_id
        ).first()
        if subscription:
            return subscription
    if stripe_customer_id:
        return db.query(Subscription).filter(
            Subscription.stripe_customer_id == stripe_customer_id
        ).first()
    return None


def extend_subscription(db: Session, subscription: Subscription, expires_at: datetime):
    """継続課金の入金を受けて有効期限を延長する（プラン名は維持）"""
    # 期限を過去方向へ短縮しない（イベントの順不同・再送に対する安全策）
    if not subscription.expires_at or expires_at > subscription.expires_at:
        subscription.expires_at = expires_at
        subscription.updated_at = datetime.now()
    # 呼び出し元での付随変更（stripe_subscription_id の補完等）も含めて確定する
    db.commit()


def downgrade_to_free(db: Session, user_id: str):
    """プランを free に降格する（解約・支払失敗時）"""
    subscription = db.query(Subscription).filter(
        Subscription.user_id == user_id
    ).first()
    if not subscription:
        return
    subscription.plan_name = "free"
    subscription.expires_at = None
    subscription.stripe_subscription_id = None
    subscription.updated_at = datetime.now()
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

