"""
_coords_in_prefecture（座標の県境界チェック）の回帰テスト。

誤同定した別地域のスポットを needs_review に落とすための判定。
True=境界内 / False=境界外 / None=判定不能。
"""
from app.services.spot_import_service import _coords_in_prefecture


def test_inside_prefecture_is_true():
    assert _coords_in_prefecture(31.6, 130.55, "鹿児島県") is True


def test_outside_prefecture_is_false():
    # 東京の座標は鹿児島の境界外
    assert _coords_in_prefecture(35.68, 139.76, "鹿児島県") is False


def test_unknown_prefecture_is_none():
    assert _coords_in_prefecture(31.6, 130.55, None) is None
    assert _coords_in_prefecture(31.6, 130.55, "存在しない県") is None


def test_missing_coords_is_none():
    assert _coords_in_prefecture(None, 130.55, "鹿児島県") is None
    assert _coords_in_prefecture(31.6, None, "鹿児島県") is None
