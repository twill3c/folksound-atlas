"""test_preprocess.py — 音声正規化とセグメント化(T-005 / T-006 / F-03 / SPEC §7)。

期待値の出所(HC-016): **SPEC §7 の内部標準**(mono / 22050Hz / float32 /
セグメント 5.0 秒 / ホップ 2.5 秒)。外部データの実測値ではない。
"""

from __future__ import annotations

import numpy as np
import pytest

from folksound.preprocess import (
    HOP_SECONDS,
    SEGMENT_SECONDS,
    TARGET_SR,
    segment_signal,
    to_mono,
)


@pytest.mark.unit
def test_spec_constants_match_spec_section_7():
    """SPEC §7 の値がコードと一致すること。数値の出所は SPEC の条項である。"""
    assert TARGET_SR == 22050
    assert SEGMENT_SECONDS == 5.0
    assert HOP_SECONDS == 2.5


@pytest.mark.unit
def test_to_mono_averages_channels():
    """(channels, samples) を平均して 1 次元にする。"""
    stereo = np.array([[1.0, 0.0, -1.0], [1.0, 1.0, 1.0]], dtype=np.float32)
    got = to_mono(stereo)
    assert got.ndim == 1
    assert np.allclose(got, [1.0, 0.5, 0.0])


@pytest.mark.unit
def test_to_mono_passes_through_1d():
    x = np.array([0.1, -0.2, 0.3], dtype=np.float32)
    assert np.allclose(to_mono(x), x)


@pytest.mark.unit
def test_to_mono_output_is_float32():
    """dtype も内部標準の一部である(SPEC §7)。"""
    x = np.array([[1, 2, 3], [4, 5, 6]], dtype=np.int16)
    assert to_mono(x).dtype == np.float32


@pytest.mark.unit
def test_segment_lengths_and_hop():
    """T-006: 各セグメントが 5 秒ちょうど、開始が 2.5 秒刻みであること。"""
    sr = TARGET_SR
    x = np.zeros(int(sr * 20), dtype=np.float32)  # 20 秒
    segs = segment_signal(x, sr)
    assert len(segs) > 0
    want = int(round(SEGMENT_SECONDS * sr))
    for s in segs:
        assert len(s["samples"]) == want
    starts = [s["start_sample"] for s in segs]
    step = int(round(HOP_SECONDS * sr))
    assert starts == list(range(0, starts[-1] + 1, step))


@pytest.mark.unit
def test_segments_do_not_run_past_the_end():
    sr = TARGET_SR
    n = int(sr * 12.3)
    x = np.zeros(n, dtype=np.float32)
    for s in segment_signal(x, sr):
        assert s["start_sample"] + len(s["samples"]) <= n


@pytest.mark.unit
def test_short_signal_is_padded_to_one_segment():
    """SPEC §7「短い録音には適応的処理を行う」の具体化。

    5 秒未満は捨てずに 1 セグメントへゼロ詰めする。**捨てると国の偏りが増える**ので、
    短いものを落とす方向には倒さない。
    """
    sr = TARGET_SR
    x = np.ones(int(sr * 1.2), dtype=np.float32)
    segs = segment_signal(x, sr)
    assert len(segs) == 1
    assert len(segs[0]["samples"]) == int(round(SEGMENT_SECONDS * sr))
    assert segs[0]["padded"] is True
    # 元の中身は先頭に残っていること(無音で置き換えていない)
    assert np.allclose(segs[0]["samples"][: int(sr * 1.2)], 1.0)


@pytest.mark.unit
def test_empty_signal_yields_no_segments():
    assert segment_signal(np.zeros(0, dtype=np.float32), TARGET_SR) == []


@pytest.mark.unit
def test_segment_ids_are_unique_and_ordered():
    segs = segment_signal(np.zeros(TARGET_SR * 30, dtype=np.float32), TARGET_SR)
    idx = [s["index"] for s in segs]
    assert idx == sorted(idx)
    assert len(set(idx)) == len(idx)
