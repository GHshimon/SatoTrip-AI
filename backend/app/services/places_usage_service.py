"""
Places API 月次使用量サービス（Enterprise 予算ガード）

Place Details（Enterprise ティア・無料枠 月1,000回）の呼び出し回数を月単位で
永続集計し、無料枠超過の課金事故を防ぐための判定を提供する。
"""
import logging
from datetime import datetime
from sqlalchemy.orm import Session

from app.models.places_usage import PlacesMonthlyUsage
from app.config import settings

logger = logging.getLogger(__name__)


def _current_month_key() -> str:
    """現在の年月キー 'YYYY-MM'（無料枠は毎月1日にリセット）"""
    return datetime.now().strftime("%Y-%m")


def get_details_used_this_month(db: Session) -> int:
    """今月の Place Details 呼び出し累計を返す（記録が無ければ0）"""
    row = (
        db.query(PlacesMonthlyUsage)
        .filter(PlacesMonthlyUsage.year_month == _current_month_key())
        .first()
    )
    return int(row.details_call_count or 0) if row else 0


def add_details_usage(db: Session, count: int) -> None:
    """今月の Place Details 呼び出し累計に count を加算する（0以下は無視）。

    失敗しても収集自体は止めない（ベストエフォート。ログのみ）。
    """
    if not count or count <= 0:
        return
    key = _current_month_key()
    try:
        row = (
            db.query(PlacesMonthlyUsage)
            .filter(PlacesMonthlyUsage.year_month == key)
            .first()
        )
        if row:
            row.details_call_count = int(row.details_call_count or 0) + int(count)
        else:
            db.add(PlacesMonthlyUsage(year_month=key, details_call_count=int(count)))
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning("Places 月次使用量の記録に失敗しました month=%s count=%s: %s", key, count, e)


def check_details_budget(db: Session) -> dict:
    """今月の Details 使用量と予算状態を返す。

    exhausted=True のとき、新規の一括追加は停止すべき（SOFT_LIMIT 到達）。
    """
    used = get_details_used_this_month(db)
    soft = settings.PLACES_MONTHLY_DETAILS_SOFT_LIMIT
    budget = settings.PLACES_MONTHLY_DETAILS_BUDGET
    return {
        "used": used,
        "soft_limit": soft,
        "budget": budget,
        "remaining": max(0, soft - used),
        "exhausted": used >= soft,
        "month": _current_month_key(),
    }
