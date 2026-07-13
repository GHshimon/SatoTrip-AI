"""
月次 Enterprise 予算ガードの回帰テスト（過剰課金の防止）。

Place Details 呼び出しの月次累計と、安全上限（SOFT_LIMIT）到達判定を固定する。
インメモリSQLite（db_session フィクスチャ）で完結。
"""
from app.config import settings
from app.services.places_usage_service import (
    add_details_usage,
    get_details_used_this_month,
    check_details_budget,
)


def test_usage_starts_at_zero(db_session):
    assert get_details_used_this_month(db_session) == 0
    budget = check_details_budget(db_session)
    assert budget["used"] == 0
    assert budget["exhausted"] is False


def test_add_usage_accumulates(db_session):
    add_details_usage(db_session, 100)
    add_details_usage(db_session, 50)
    assert get_details_used_this_month(db_session) == 150


def test_zero_or_negative_is_noop(db_session):
    add_details_usage(db_session, 0)
    add_details_usage(db_session, -5)
    assert get_details_used_this_month(db_session) == 0


def test_exhausted_at_soft_limit(db_session):
    add_details_usage(db_session, settings.PLACES_MONTHLY_DETAILS_SOFT_LIMIT)
    budget = check_details_budget(db_session)
    assert budget["exhausted"] is True
    assert budget["remaining"] == 0


def test_not_exhausted_below_soft_limit(db_session):
    add_details_usage(db_session, settings.PLACES_MONTHLY_DETAILS_SOFT_LIMIT - 1)
    budget = check_details_budget(db_session)
    assert budget["exhausted"] is False
    assert budget["remaining"] == 1
