"""test_split.py — 録音単位分割の検査(T-009 / T-010 / G-03 / SPEC §9)。

期待値の出所(HC-016):
  **SPEC §9 の条項**。同一録音から作ったセグメントが二つの split にまたがってはならない、
  という不変量である。件数ではなく集合の性質で書く。

HC-041 の規律により陽性対照(T-010)を対で置く。セグメント単位でランダム分割した集合を
同じ検査器に通し、**必ず落ちる**ことを確かめる。落ちないなら検査器が働いていない。
"""

from __future__ import annotations

import pytest

from folksound.split import (
    SplitViolation,
    assert_no_recording_leak,
    find_recording_leaks,
    split_by_recording,
)


def make_segments(n_recordings: int = 30, per: int = 5) -> list[dict]:
    """録音 n 件 × セグメント per 件。"""
    return [
        {"segment_id": f"folk_{r:06d}#{s}", "recording_id": f"folk_{r:06d}"}
        for r in range(n_recordings)
        for s in range(per)
    ]


@pytest.mark.unit
def test_split_assigns_every_segment_exactly_once():
    segs = make_segments()
    out = split_by_recording(segs, seed=42)
    seen = [s["segment_id"] for v in out.values() for s in v]
    assert sorted(seen) == sorted(s["segment_id"] for s in segs)
    assert len(seen) == len(set(seen)), "同じセグメントが二か所に出た"


@pytest.mark.unit
def test_no_recording_spans_two_splits():
    """T-009 / G-03: 本命の不変量。"""
    out = split_by_recording(make_segments(), seed=42)
    assert find_recording_leaks(out) == []


@pytest.mark.unit
def test_split_is_deterministic_for_a_seed():
    a = split_by_recording(make_segments(), seed=7)
    b = split_by_recording(make_segments(), seed=7)
    assert {k: [s["segment_id"] for s in v] for k, v in a.items()} == {
        k: [s["segment_id"] for s in v] for k, v in b.items()
    }


@pytest.mark.unit
def test_different_seeds_give_different_assignment():
    """対照が対照として成り立つ前提(HC-079): seed が実際に効いていること。

    これが成り立たないと「決定論である」検査は何も言っていない。
    """
    a = split_by_recording(make_segments(), seed=1)
    b = split_by_recording(make_segments(), seed=2)
    assert {s["segment_id"] for s in a["train"]} != {s["segment_id"] for s in b["train"]}


@pytest.mark.unit
def test_proportions_are_close_to_spec():
    """SPEC §9 の 70/15/15。録音数で測る(セグメント数ではない)。"""
    out = split_by_recording(make_segments(n_recordings=200, per=3), seed=42)
    recs = {k: {s["recording_id"] for s in v} for k, v in out.items()}
    total = sum(len(v) for v in recs.values())
    assert total == 200
    assert 0.60 <= len(recs["train"]) / total <= 0.80
    assert 0.08 <= len(recs["val"]) / total <= 0.22
    assert 0.08 <= len(recs["test"]) / total <= 0.22


@pytest.mark.unit
def test_leak_detector_catches_segment_level_random_split():
    """T-010 / G-03 陽性対照: セグメント単位のランダム分割は**必ず**捕まること。

    これは「やってはいけない分割」そのものである(SPEC §9 / 仕様書 §27)。
    """
    import random

    segs = make_segments(n_recordings=30, per=5)
    rng = random.Random(0)
    shuffled = segs[:]
    rng.shuffle(shuffled)
    n = len(shuffled)
    bad = {
        "train": shuffled[: int(n * 0.7)],
        "val": shuffled[int(n * 0.7) : int(n * 0.85)],
        "test": shuffled[int(n * 0.85) :],
    }

    leaks = find_recording_leaks(bad)
    assert leaks, "セグメント単位のランダム分割を漏れとして検出できていない"

    with pytest.raises(SplitViolation):
        assert_no_recording_leak(bad)


@pytest.mark.unit
def test_positive_control_precondition_holds():
    """陽性対照が発火しうる入力であることを固定する(HC-070)。

    録音あたり 2 セグメント以上ないと、ランダム分割でも漏れは起きえない。
    """
    segs = make_segments(n_recordings=30, per=5)
    per_recording: dict[str, int] = {}
    for s in segs:
        per_recording[s["recording_id"]] = per_recording.get(s["recording_id"], 0) + 1
    assert min(per_recording.values()) >= 2, "対照が発火しえない入力になっている"
