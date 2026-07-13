"""
merge_spot_data の「検証ステータスは上げる方向のみ」「Places事実カラムの補完」
の回帰テスト（コードレビュー指摘 #1 の修正を固定する）。

マージ経路でこれが壊れると、既存/再ヒットのスポットが営業時間や検証済み状態を
取りこぼす（Phase1 の価値が無効化される）。DBは不要（Spotオブジェクトの属性操作のみ）。
"""
from app.models.spot import Spot
from app.services.spot_import_service import merge_spot_data


def test_status_upgrades_unverified_to_verified():
    existing = Spot(name="X温泉", verification_status="unverified")
    new_data = {"verification_status": "verified", "verification_score": 0.9}
    merge_spot_data(existing, new_data)
    assert existing.verification_status == "verified"
    assert existing.verified_at is not None
    assert existing.verification_score == 0.9


def test_status_does_not_downgrade():
    existing = Spot(name="X温泉", verification_status="verified")
    new_data = {"verification_status": "needs_review", "verification_score": 0.6}
    merge_spot_data(existing, new_data)
    # verified は needs_review に下げない
    assert existing.verification_status == "verified"


def test_facts_backfilled_when_existing_empty():
    existing = Spot(name="X温泉", verification_status="unverified")
    assert existing.opening_hours is None and existing.rating is None
    new_data = {
        "verification_status": "verified",
        "business_status": "OPERATIONAL",
        "rating": 4.2,
        "rating_count": 123,
        "opening_hours": {"weekdayDescriptions": ["月曜日: 9:00〜17:00"]},
        "price_level": 2,
    }
    merge_spot_data(existing, new_data)
    assert existing.business_status == "OPERATIONAL"
    assert existing.rating == 4.2
    assert existing.rating_count == 123
    assert existing.opening_hours == {"weekdayDescriptions": ["月曜日: 9:00〜17:00"]}
    assert existing.price_level == 2


def test_existing_facts_not_overwritten():
    existing = Spot(name="X温泉", verification_status="verified", rating=4.5)
    new_data = {"verification_status": "verified", "rating": 3.0}
    merge_spot_data(existing, new_data)
    # 既存の rating は上書きしない（既存優先）
    assert existing.rating == 4.5
