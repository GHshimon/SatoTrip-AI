"""
スポットモデル
"""
from sqlalchemy import Column, String, Integer, Float, Text, DateTime, JSON
from sqlalchemy.sql import func
from app.utils.database import Base
import uuid


class Spot(Base):
    """スポットテーブル"""
    __tablename__ = "spots"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False, index=True)
    description = Column(Text, nullable=True)
    area = Column(String, nullable=True, index=True)
    address = Column(String, nullable=True, index=True)
    category = Column(String, nullable=True)
    duration_minutes = Column(Integer, nullable=True)
    rating = Column(Float, nullable=True)
    image = Column(String, nullable=True)
    price = Column(Float, nullable=True)
    tags = Column(JSON, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    place_id = Column(String, nullable=True, unique=True, index=True)
    phone = Column(String, nullable=True)
    website = Column(String, nullable=True)
    source_videos = Column(JSON, nullable=True)

    # 出所・検証（ハルシネーション対策。docs/design/SPOT_FIELD_SPEC.md §2）
    # source: 初回登録経路 'youtube'|'sns'|'csv'|'manual'|'places'
    source = Column(String, nullable=True, index=True)
    # verification_status: 'verified'（自動合格）|'needs_review'（要人手）|
    #                      'rejected'（棄却）|'unverified'（既存データ移行用）
    verification_status = Column(String, nullable=False, default="unverified", index=True)
    verified_at = Column(DateTime(timezone=True), nullable=True)      # 最終Places照合成功日時
    verification_score = Column(Float, nullable=True)                 # 照合スコア（matched_score）
    # business_status: 'OPERATIONAL'|'CLOSED_TEMPORARILY'|'CLOSED_PERMANENTLY'
    business_status = Column(String, nullable=True)

    # 事実データ（Placesから取得。rating と price は一次ソース限定）
    rating_count = Column(Integer, nullable=True)      # Places userRatingCount。rating とセットでのみ表示
    price_level = Column(Integer, nullable=True)       # Places priceLevel の序数 0..4（金額ではない）
    price_range_min = Column(Integer, nullable=True)   # Places priceRange.startPrice（円。揃った時のみ）
    price_range_max = Column(Integer, nullable=True)   # Places priceRange.endPrice
    opening_hours = Column(JSON, nullable=True)        # Places regularOpeningHours（periods/weekdayDescriptions）

    # 出所トレース・表示制御
    description_source = Column(String, nullable=True)  # 'ai'|'manual'|'places'（AI生成の明示用）
    field_provenance = Column(JSON, nullable=True)      # {"address":"places","rating":"places",...}
    rejected_reason = Column(String, nullable=True)     # 'no_places_hit'|'low_score'|'closed'|'duplicate'|'admin'

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
