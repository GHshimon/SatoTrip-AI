"""
Places API 月次使用量モデル

Place Details（Enterprise ティア。無料枠 月1,000回）の呼び出し回数を月単位で
永続カウントし、月次予算ガードで無料枠超過の課金事故を防ぐために使う。
（docs/design/SPOT_ROLLOUT_SCHEDULE.md）
"""
from sqlalchemy import Column, String, Integer, DateTime
from sqlalchemy.sql import func
from app.utils.database import Base


class PlacesMonthlyUsage(Base):
    """月ごとの Place Details 呼び出し回数"""
    __tablename__ = "places_monthly_usage"

    # 'YYYY-MM' 形式（例: '2026-07'）。無料枠は毎月1日にリセットされる。
    year_month = Column(String, primary_key=True)
    details_call_count = Column(Integer, nullable=False, default=0)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
