"""
交通手段別の所要時間補正（_duration_for_mode）の回帰テスト。

公開OSRMデモは profile を無視して常に車の所要時間を返すため、徒歩/自転車は距離から
再計算し、電車/バスは車時間ベースの概算にする。ここが壊れると移動時間が非現実的になる
（徒歩が車速で表示される等）。
"""
from app.utils.route_service import _duration_for_mode

# 6.18km, 車の所要 744秒（=12.4分）を基準にする
DIST_M = 6180.0
CAR_S = 744.0


def test_driving_uses_osrm_duration():
    dur, src = _duration_for_mode("driving", DIST_M, CAR_S)
    assert dur == CAR_S
    assert src == "osrm"


def test_walking_recomputed_from_distance():
    dur, src = _duration_for_mode("walking", DIST_M, CAR_S)
    # 徒歩は車速より大幅に遅い（= 車時間よりずっと長い）
    assert dur > CAR_S * 3
    assert src == "osrm+walk_estimate"


def test_cycling_between_walk_and_car():
    walk, _ = _duration_for_mode("walking", DIST_M, CAR_S)
    bike, src = _duration_for_mode("cycling", DIST_M, CAR_S)
    assert CAR_S < bike < walk
    assert src == "osrm+bike_estimate"


def test_transit_adds_overhead_over_car():
    dur, src = _duration_for_mode("transit", DIST_M, CAR_S)
    # 車時間より長い（乗換・待ち・駅までの徒歩を見込む）
    assert dur > CAR_S
    assert src == "osrm+transit_estimate"


def test_unknown_profile_falls_back_to_car():
    dur, src = _duration_for_mode("その他", DIST_M, CAR_S)
    assert dur == CAR_S
    assert src == "osrm"


def test_zero_distance_walking_falls_back_to_car():
    # 距離0（座標欠損等）のときは補正できず車時間のまま
    dur, src = _duration_for_mode("walking", 0, CAR_S)
    assert dur == CAR_S
    assert src == "osrm"
