"""test_features.py — 従来型音響特徴量の検査(T-007 / T-008 / F-04)。

期待値の出所(HC-016):
  **閉形式**である。合成した信号の rms / zcr / spectral_centroid は解析的に決まるので、
  外部実装にも自分の実装にも依存しない非循環のオラクルになる。
  導出の前提(振幅・周波数・サンプル数が整数周期に乗ること)は、
  期待値を使う前にテスト内で assert して固定する(VERIF-FALSE の予防)。
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from folksound.features import extract_features, rms, spectral_centroid, zero_crossing_rate

SR = 22050


def sine(freq: float, seconds: float, amp: float = 1.0, sr: int = SR) -> np.ndarray:
    n = int(round(seconds * sr))
    t = np.arange(n, dtype=np.float64) / sr
    return (amp * np.sin(2 * math.pi * freq * t)).astype(np.float32)


@pytest.mark.unit
def test_rms_of_sine_is_amplitude_over_sqrt2():
    """正弦波の実効値は A/√2(整数周期ぶんを取れば厳密)。"""
    freq, secs, amp = 441.0, 1.0, 0.5
    # 前提: 441Hz × 1s は 22050Hz 上でちょうど 441 周期 = 整数周期
    assert (freq * secs) == int(freq * secs), "整数周期でないと A/√2 に一致しない"
    x = sine(freq, secs, amp)
    assert abs(rms(x) - amp / math.sqrt(2)) < 1e-4


@pytest.mark.unit
def test_rms_of_silence_is_zero():
    assert rms(np.zeros(1000, dtype=np.float32)) == 0.0


@pytest.mark.unit
def test_zcr_of_sine_matches_two_crossings_per_period():
    """正弦波は 1 周期に 2 回ゼロを跨ぐ。zcr ≒ 2f/sr。"""
    freq = 441.0
    x = sine(freq, 1.0)
    expected = 2 * freq / SR
    got = zero_crossing_rate(x)
    assert abs(got - expected) < expected * 0.02, f"{got} vs {expected}"


@pytest.mark.unit
def test_zcr_of_constant_signal_is_zero_not_nan():
    """T-008 陰性対照: 定数信号でも非有限にならないこと。

    無音・定数は「異常」ではなく正常系である(HC-002 の型)。
    """
    for v in (0.0, 0.3, -0.7):
        x = np.full(1000, v, dtype=np.float32)
        got = zero_crossing_rate(x)
        assert math.isfinite(got), f"定数 {v} で非有限: {got}"
        assert got == 0.0


@pytest.mark.unit
def test_spectral_centroid_of_pure_tone_is_near_its_frequency():
    """単一の正弦波の重心はその周波数に寄る。"""
    freq = 1000.0
    x = sine(freq, 1.0)
    c = spectral_centroid(x, SR)
    assert abs(c - freq) < 60.0, f"centroid={c}, expected≈{freq}"


@pytest.mark.unit
def test_spectral_centroid_rises_with_frequency():
    """順序の不変量。絶対値でなく大小関係で書く。"""
    lo = spectral_centroid(sine(300.0, 1.0), SR)
    hi = spectral_centroid(sine(3000.0, 1.0), SR)
    assert lo < hi


@pytest.mark.unit
def test_spectral_centroid_of_silence_is_finite():
    """T-008 陰性対照: 全ゼロで 0/0 を作らないこと。"""
    c = spectral_centroid(np.zeros(SR, dtype=np.float32), SR)
    assert math.isfinite(c)


@pytest.mark.unit
def test_extract_features_shape_and_finiteness():
    """出荷する特徴量の形(SPEC §7 / schemas/derived.schema.json)を固定する。"""
    x = sine(440.0, 3.0) + 0.01 * np.random.default_rng(0).standard_normal(3 * SR).astype(np.float32)
    f = extract_features(x.astype(np.float32), SR)

    assert len(f["mfcc"]) == 40, "n_mfcc は SPEC §7 で 40"
    assert len(f["chroma"]) == 12
    for k, v in f.items():
        vals = v if isinstance(v, list) else [v]
        assert all(math.isfinite(x_) for x_ in vals), f"{k} に非有限が混じった: {v}"


@pytest.mark.unit
def test_extract_features_on_silence_is_finite():
    """無音でも落ちず、非有限を出さないこと(実データには無音に近い断片が混じる)。"""
    f = extract_features(np.zeros(SR * 2, dtype=np.float32), SR)
    for k, v in f.items():
        vals = v if isinstance(v, list) else [v]
        assert all(math.isfinite(x_) for x_ in vals), f"{k} が非有限: {v}"
