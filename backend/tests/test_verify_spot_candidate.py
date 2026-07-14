"""
verify_spot_candidate（スポット3値判定）の回帰テスト。

この関数はスポット収集の品質ゲートの心臓部。無人のスケジュール実行で
サイレントに壊れると「全棄却（0件収集）」または「ゴミ混入」になるため、
全分岐を固定する。ライブAPIは使わない（純ロジック）。

しきい値は config の既定（AUTO_PASS=0.75 / REVIEW=0.50）を前提にする。
鹿児島県の境界（_PREFECTURE_BOUNDS）: lat 30.9〜32.6 / lng 129.2〜131.6。
"""
from app.services.spot_import_service import verify_spot_candidate

# 鹿児島市付近（県境界内）／東京付近（鹿児島から見て境界外）
KAGOSHIMA = {"latitude": 31.6, "longitude": 130.55}
TOKYO = {"latitude": 35.68, "longitude": 139.76}


def _info(**kwargs):
    base = {"matched_score": 0.9, "business_status": "OPERATIONAL"}
    base.update(KAGOSHIMA)
    base.update(kwargs)
    return base


def test_no_places_info_is_rejected_no_hit():
    r = verify_spot_candidate(None, "鹿児島県")
    assert r["status"] == "rejected"
    assert r["reason"] == "no_places_hit"


def test_permanently_closed_is_rejected():
    r = verify_spot_candidate(_info(business_status="CLOSED_PERMANENTLY"), "鹿児島県")
    assert r["status"] == "rejected"
    assert r["reason"] == "closed"


def test_high_score_operational_in_bounds_is_verified():
    r = verify_spot_candidate(_info(matched_score=0.9), "鹿児島県")
    assert r["status"] == "verified"
    assert r["reason"] is None


def test_high_score_unknown_prefecture_is_verified():
    # 都道府県が不明なら県境界チェックはスキップ（判定不能→verifiedを妨げない）
    r = verify_spot_candidate(_info(matched_score=0.8), None)
    assert r["status"] == "verified"


def test_high_score_but_out_of_bounds_is_needs_review():
    info = _info(matched_score=0.9, **TOKYO)
    r = verify_spot_candidate(info, "鹿児島県")
    assert r["status"] == "needs_review"
    assert r["reason"] == "out_of_bounds"


def test_mid_score_is_needs_review():
    r = verify_spot_candidate(_info(matched_score=0.6), "鹿児島県")
    assert r["status"] == "needs_review"


def test_temporarily_closed_is_needs_review():
    r = verify_spot_candidate(_info(matched_score=0.9, business_status="CLOSED_TEMPORARILY"), "鹿児島県")
    assert r["status"] == "needs_review"
    assert r["reason"] == "temporarily_closed"


def test_low_score_is_rejected():
    r = verify_spot_candidate(_info(matched_score=0.3), "鹿児島県")
    assert r["status"] == "rejected"
    assert r["reason"] == "low_score"


def test_score_just_below_auto_pass_is_needs_review():
    # 0.74 < 0.75(AUTO_PASS) かつ >= 0.50(REVIEW) → needs_review
    r = verify_spot_candidate(_info(matched_score=0.74), "鹿児島県")
    assert r["status"] == "needs_review"
