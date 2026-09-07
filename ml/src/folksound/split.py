"""split.py — 録音単位の train/val/test 分割(SPEC §9 / G-03 / 仕様書 §27)。

**同一録音から作った複数セグメントを、二つの split へまたがせてはならない。**
またがると、学習時に見た録音の別の断片で評価することになり、
「音楽が似ている」ではなく「同じ録音である」を測ってしまう。

漏れの検出器(`find_recording_leaks`)は分割器とは独立に書く。分割器の内部を信じずに
**出力だけ**を見るので、分割器を差し替えても検査は生き続ける。
"""

from __future__ import annotations

import random
from collections import defaultdict

SPLITS = ("train", "val", "test")
DEFAULT_RATIOS = (0.70, 0.15, 0.15)  # SPEC §9


class SplitViolation(Exception):
    """録音がふたつ以上の split にまたがっている。"""


def split_by_recording(
    segments: list[dict],
    seed: int = 42,
    ratios: tuple[float, float, float] = DEFAULT_RATIOS,
    recording_key: str = "recording_id",
) -> dict[str, list[dict]]:
    """録音を単位に分割する。

    セグメントではなく **録音** をシャッフルして割り当てる。
    比率は録音数に対して適用する(セグメント数ではない —— 録音ごとに
    セグメント数が違うので、セグメント数で切ると録音が割れる)。
    """
    by_rec: dict[str, list[dict]] = defaultdict(list)
    for s in segments:
        by_rec[s[recording_key]].append(s)

    rec_ids = sorted(by_rec)  # 入力順に依存させない
    rng = random.Random(seed)
    rng.shuffle(rec_ids)

    n = len(rec_ids)
    n_train = int(round(n * ratios[0]))
    n_val = int(round(n * ratios[1]))
    # 端数は test へ寄せる(必ず全件が割り当たるように)
    bounds = {
        "train": rec_ids[:n_train],
        "val": rec_ids[n_train : n_train + n_val],
        "test": rec_ids[n_train + n_val :],
    }

    return {k: [s for r in v for s in by_rec[r]] for k, v in bounds.items()}


def find_recording_leaks(
    splits: dict[str, list[dict]], recording_key: str = "recording_id"
) -> list[tuple[str, list[str]]]:
    """複数の split に現れた録音を返す。

    返り値は `(recording_id, [その録音が現れた split 名...])` の一覧。
    空リストなら漏れなし。
    """
    where: dict[str, set[str]] = defaultdict(set)
    for name, segs in splits.items():
        for s in segs:
            where[s[recording_key]].add(name)
    return sorted(
        (rec, sorted(names)) for rec, names in where.items() if len(names) > 1
    )


def assert_no_recording_leak(
    splits: dict[str, list[dict]], recording_key: str = "recording_id"
) -> None:
    """漏れがあれば例外で止める(黙って通る道を作らない —— HC-075)。"""
    leaks = find_recording_leaks(splits, recording_key)
    if leaks:
        head = ", ".join(f"{r}({'/'.join(w)})" for r, w in leaks[:5])
        raise SplitViolation(
            f"録音が複数の split にまたがっている: {len(leaks)} 件 — {head}"
        )
