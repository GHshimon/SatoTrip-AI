"""
APIキー管理サービス
"""
import secrets
import string
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime, timedelta
from typing import Optional, Tuple
from app.models.api_key import ApiKey, ApiKeyUsage
from app.utils.security import hash_password, verify_password
from fastapi import HTTPException, status


def generate_api_key() -> Tuple[str, str]:
    """
    APIキーを生成
    Returns: (plain_key, hashed_key)
    """
    # st_ + 32文字のランダム文字列
    alphabet = string.ascii_letters + string.digits
    random_part = ''.join(secrets.choice(alphabet) for _ in range(32))
    plain_key = f"st_{random_part}"
    
    # bcryptでハッシュ化
    hashed_key = hash_password(plain_key)
    
    return plain_key, hashed_key


def verify_api_key_hash(plain_key: str, key_hash: str) -> bool:
    """APIキーのハッシュを検証"""
    return verify_password(plain_key, key_hash)


def get_api_key_by_hash(db: Session, key_hash: str) -> Optional[ApiKey]:
    """ハッシュからAPIキーを取得"""
    # すべてのAPIキーを取得してハッシュを検証
    # 注意: これは非効率だが、bcryptは一方向ハッシュのため必要
    # 本番環境では、キーのプレフィックス（st_）とランダム部分を別途保存するなどの最適化を検討
    api_keys = db.query(ApiKey).filter(ApiKey.is_active == True).all()
    
    for api_key in api_keys:
        if verify_api_key_hash(plain_key=None, key_hash=api_key.key_hash):
            # 実際には、リクエストから受け取ったplain_keyと比較する必要がある
            # この関数は呼び出し側でplain_keyを検証する必要がある
            pass
    
    # より効率的な方法: リクエストから受け取ったplain_keyをハッシュ化して比較
    # しかし、bcryptは毎回異なるハッシュを生成するため、verify_passwordを使用
    return None


def get_api_key_by_plain_key(db: Session, plain_key: str) -> Optional[ApiKey]:
    """
    平文のAPIキーからApiKeyオブジェクトを取得
    すべてのアクティブなAPIキーをチェックして検証
    """
    if not plain_key or not plain_key.startswith("st_"):
        return None
    
    # すべてのアクティブなAPIキーを取得
    api_keys = db.query(ApiKey).filter(ApiKey.is_active == True).all()
    
    for api_key in api_keys:
        if verify_api_key_hash(plain_key, api_key.key_hash):
            return api_key
    
    return None


def create_api_key(
    db: Session,
    name: str,
    user_id: Optional[str] = None,
    rate_limit_per_minute: int = 10,
    rate_limit_per_hour: int = 100,
    rate_limit_per_day: int = 1000,
    monthly_plan_limit: int = 100,
    expires_at: Optional[datetime] = None
) -> Tuple[ApiKey, str]:
    """
    APIキーを作成
    Returns: (ApiKey, plain_key)
    """
    plain_key, hashed_key = generate_api_key()
    
    api_key = ApiKey(
        key_hash=hashed_key,
        name=name,
        user_id=user_id,
        is_active=True,
        rate_limit_per_minute=rate_limit_per_minute,
        rate_limit_per_hour=rate_limit_per_hour,
        rate_limit_per_day=rate_limit_per_day,
        monthly_plan_limit=monthly_plan_limit,
        expires_at=expires_at
    )
    
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    
    return api_key, plain_key


def update_api_key_usage(db: Session, api_key_id: str):
    """APIキーの使用量を更新（last_used_atを更新）"""
    api_key = db.query(ApiKey).filter(ApiKey.id == api_key_id).first()
    if api_key:
        api_key.last_used_at = datetime.now()
        db.commit()


def record_api_key_request(db: Session, api_key_id: str, is_plan_generation: bool = False):
    """
    APIキーのリクエストを記録
    """
    now = datetime.now()
    current_month = f"{now.year}-{now.month:02d}"
    
    usage = db.query(ApiKeyUsage).filter(
        and_(
            ApiKeyUsage.api_key_id == api_key_id,
            ApiKeyUsage.month == current_month
        )
    ).first()
    
    if usage:
        usage.request_count += 1
        if is_plan_generation:
            usage.plan_generation_count += 1
        usage.updated_at = datetime.now()
    else:
        usage = ApiKeyUsage(
            api_key_id=api_key_id,
            month=current_month,
            request_count=1,
            plan_generation_count=1 if is_plan_generation else 0
        )
        db.add(usage)
    
    db.commit()


def check_api_key_plan_limit(db: Session, api_key_id: str) -> Tuple[bool, str, int]:
    """
    プラン生成上限をチェック
    Returns: (can_generate, message, remaining)
    """
    api_key = db.query(ApiKey).filter(ApiKey.id == api_key_id).first()
    if not api_key:
        return False, "APIキーが見つかりません", 0
    
    # 無制限プラン
    if api_key.monthly_plan_limit == -1:
        return True, "", -1
    
    # 使用量取得
    now = datetime.now()
    current_month = f"{now.year}-{now.month:02d}"
    
    usage = db.query(ApiKeyUsage).filter(
        and_(
            ApiKeyUsage.api_key_id == api_key_id,
            ApiKeyUsage.month == current_month
        )
    ).first()
    
    monthly_usage = usage.plan_generation_count if usage else 0
    remaining = api_key.monthly_plan_limit - monthly_usage
    
    if remaining > 0:
        return True, f"残り{remaining}回", remaining
    else:
        return False, f"今月のプラン生成上限に達しました。", 0


def get_api_key_usage(db: Session, api_key_id: str, month: Optional[str] = None) -> Optional[ApiKeyUsage]:
    """APIキーの使用量を取得"""
    if month:
        return db.query(ApiKeyUsage).filter(
            and_(
                ApiKeyUsage.api_key_id == api_key_id,
                ApiKeyUsage.month == month
            )
        ).first()
    else:
        # 最新月を取得
        return db.query(ApiKeyUsage).filter(
            ApiKeyUsage.api_key_id == api_key_id
        ).order_by(ApiKeyUsage.month.desc()).first()

