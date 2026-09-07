"""test_geo.py — 地理距離(F-12 / SPEC §5.5)。

期待値の出所(HC-016):
  **閉形式と外部権威**。地球を半径 6371 km の球とみなした大円距離(haversine)は
  解析的に決まる。加えて、よく知られた都市間距離を外部権威として置き、
  桁が合っていることを確かめる(出所はコメントに書く)。
"""

from __future__ import annotations

import math

import pytest

from folksound.geo import EARTH_RADIUS_KM, haversine_km


@pytest.mark.unit
def test_zero_distance_to_itself():
    assert haversine_km(35.0, 135.0, 35.0, 135.0) == pytest.approx(0.0, abs=1e-9)


@pytest.mark.unit
def test_quarter_meridian_is_a_quarter_of_the_circumference():
    """赤道から北極までは子午線の 1/4(閉形式)。"""
    want = 0.5 * math.pi * EARTH_RADIUS_KM  # = πR/2
    assert haversine_km(0.0, 0.0, 90.0, 0.0) == pytest.approx(want, rel=1e-9)


@pytest.mark.unit
def test_antipodes_are_half_the_circumference():
    """対蹠点までは πR(閉形式)。"""
    want = math.pi * EARTH_RADIUS_KM
    assert haversine_km(0.0, 0.0, 0.0, 180.0) == pytest.approx(want, rel=1e-9)


@pytest.mark.unit
def test_one_degree_of_latitude_is_about_111km():
    """緯度 1 度 = 2πR/360 ≒ 111.19 km(閉形式)。"""
    want = 2 * math.pi * EARTH_RADIUS_KM / 360.0
    assert haversine_km(0.0, 0.0, 1.0, 0.0) == pytest.approx(want, rel=1e-9)


@pytest.mark.unit
def test_longitude_degrees_shrink_toward_the_poles():
    """順序の不変量: 同じ経度差でも高緯度ほど短い。"""
    at_equator = haversine_km(0.0, 0.0, 0.0, 1.0)
    at_60 = haversine_km(60.0, 0.0, 60.0, 1.0)
    assert at_60 < at_equator
    # cos(60°) = 0.5 なので、およそ半分になるはず
    assert at_60 == pytest.approx(at_equator * 0.5, rel=1e-3)


@pytest.mark.unit
def test_known_city_pair_matches_published_distance():
    """外部権威との突き合わせ。

    東京(35.6895, 139.6917)– ロンドン(51.5074, -0.1278)の大円距離は
    一般に約 9,560 km とされる。球近似なので 1% の幅で見る。
    """
    d = haversine_km(35.6895, 139.6917, 51.5074, -0.1278)
    assert 9460 < d < 9660, d


@pytest.mark.unit
def test_symmetry():
    a = haversine_km(35.0, 135.0, -12.0, 20.0)
    b = haversine_km(-12.0, 20.0, 35.0, 135.0)
    assert a == pytest.approx(b, rel=1e-12)


@pytest.mark.unit
def test_result_is_finite_everywhere_on_the_grid():
    """陰性対照: 極・日付変更線でも非有限を出さないこと。"""
    pts = [(-90, -180), (-90, 180), (90, 0), (0, 180), (0, -180), (89.999, 179.999)]
    for a in pts:
        for b in pts:
            d = haversine_km(a[0], a[1], b[0], b[1])
            assert math.isfinite(d), f"{a}->{b} が非有限"
            assert d >= 0.0
