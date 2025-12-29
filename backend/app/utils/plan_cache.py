"""
プラン生成キャッシュ機能（データベースベース）
"""
import json
import hashlib
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.models.plan_cache import PlanCache

CACHE_EXPIRY_DAYS = 30


def _get_cache_key(
    destination: str,
    days: int,
    budget: str,
    themes: List[str],
    pending_spots: List[Dict[str, Any]],
    preferences: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    transportation: Optional[str] = None,
) -> str:
    """キャッシュキーを生成"""
    # スポット名のリストをソート
    spot_names = sorted([spot.get("name", "") for spot in pending_spots])
    
    cache_data = {
        "destination": destination,
        "days": days,
        "budget": budget,
        "themes": sorted(themes) if themes else [],
        "spot_names": spot_names,
        "preferences": preferences or "",
        "start_time": start_time or "",
        "end_time": end_time or "",
        "transportation": transportation or "",
    }
    cache_str = json.dumps(cache_data, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(cache_str.encode('utf-8')).hexdigest()


def get_cached_plan(
    db: Session,
    destination: str,
    days: int,
    budget: str,
    themes: List[str],
    pending_spots: List[Dict[str, Any]],
    preferences: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    transportation: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """キャッシュからプランを取得"""
    cache_key = _get_cache_key(
        destination, days, budget, themes, pending_spots,
        preferences, start_time, end_time, transportation
    )
    
    # 期限切れでないキャッシュを取得
    now = datetime.now()
    cached_entry = db.query(PlanCache).filter(
        PlanCache.cache_key == cache_key,
        PlanCache.expires_at > now
    ).first()
    
    if cached_entry:
        return cached_entry.plan_data
    
    return None


def save_cached_plan(
    db: Session,
    destination: str,
    days: int,
    budget: str,
    themes: List[str],
    pending_spots: List[Dict[str, Any]],
    plan: Dict[str, Any],
    preferences: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    transportation: Optional[str] = None,
):
    """プランをキャッシュに保存"""
    cache_key = _get_cache_key(
        destination, days, budget, themes, pending_spots,
        preferences, start_time, end_time, transportation
    )
    
    expires_at = datetime.now() + timedelta(days=CACHE_EXPIRY_DAYS)
    
    # 既存のキャッシュを確認
    existing_cache = db.query(PlanCache).filter(
        PlanCache.cache_key == cache_key
    ).first()
    
    if existing_cache:
        # 既存のキャッシュを更新
        existing_cache.plan_data = plan
        existing_cache.cached_at = datetime.now()
        existing_cache.expires_at = expires_at
    else:
        # 新しいキャッシュを作成
        new_cache = PlanCache(
            cache_key=cache_key,
            plan_data=plan,
            expires_at=expires_at
        )
        db.add(new_cache)
    
    db.commit()


def clear_old_cache(db: Session):
    """期限切れキャッシュを削除"""
    now = datetime.now()
    deleted_count = db.query(PlanCache).filter(
        PlanCache.expires_at <= now
    ).delete()
    db.commit()
    return deleted_count

