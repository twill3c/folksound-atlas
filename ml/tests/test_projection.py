"""test_projection.py — 射影の再現性(T-013 / G-06 / 仕様書 §51)。

期待値の出所(HC-016): **SPEC §10 の G-06**「UMAP が乱数種込みで再現する」。

理論上一致しうるかを先に確かめる(HC-073):
    UMAP は `random_state` を与えると内部の並列化を切り、決定論的に走る。
    つまり**完全一致を要求してよい**。これが成り立たない実装(並列のまま)なら、
    完全一致は原理的に達成できないので、閾値の置き方から変えなければならない。
    ここでは「同じ種なら完全一致」「違う種なら違う配置」の両方を確かめ、
    後者で**種が実際に効いていること**を固定する(対照が成り立つ前提 — HC-079)。
"""

from __future__ import annotations

import numpy as np
import pytest

pytestmark = pytest.mark.unit

RANDOM_STATE = 42  # 08_project_and_similar.py と同じ値


def blobs(n: int = 90, d: int = 16, seed: int = 0) -> np.ndarray:
    """L2 正規化した合成データ。出荷物と同じ形(単位球上)にそろえる。"""
    rng = np.random.default_rng(seed)
    centers = rng.normal(size=(3, d))
    X = np.repeat(centers, n // 3, axis=0) + 0.35 * rng.normal(size=(n // 3 * 3, d))
    return X / np.linalg.norm(X, axis=1, keepdims=True)


def run_umap(X: np.ndarray, seed: int) -> np.ndarray:
    import umap

    return umap.UMAP(
        n_neighbors=10, min_dist=0.1, metric="cosine",
        random_state=seed, n_components=2,
    ).fit_transform(X)


@pytest.mark.slow
def test_umap_is_exactly_reproducible_for_a_seed():
    """G-06 の本命。同じ種で二度走らせて**完全一致**すること。"""
    X = blobs()
    a = run_umap(X, RANDOM_STATE)
    b = run_umap(X, RANDOM_STATE)
    assert a.shape == b.shape
    assert np.array_equal(a, b), (
        f"同じ種で配置が変わった(最大差 {np.abs(a - b).max()})。"
        "random_state が効いていないか、並列化が残っている"
    )


@pytest.mark.slow
def test_different_seeds_give_different_layouts():
    """対照: 種が実際に効いていること。

    これが無いと「完全一致」は「そもそも乱数を使っていない」でも通ってしまう。
    """
    X = blobs()
    a = run_umap(X, RANDOM_STATE)
    c = run_umap(X, RANDOM_STATE + 1)
    assert not np.array_equal(a, c), "種を変えても配置が同じ(種が効いていない)"


@pytest.mark.validation
def test_shipped_projection_records_enough_to_rerun():
    """出荷物だけを見て、再計算に必要な情報がそろっていること。

    **書き出していない再現性は、確かめようがない**(仕様書 §51)。
    """
    import json
    from pathlib import Path

    root = Path(__file__).resolve().parents[2]
    data = root / "public" / "data"
    models = data / "models.json"
    if not models.exists():
        pytest.skip("models.json がまだ無い")

    checked = 0
    for m in json.loads(models.read_text(encoding="utf-8"))["models"]:
        p = data / f"umap_{m['model_id']}.json"
        if not p.exists():
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        assert isinstance(d.get("random_state"), int), f"{p.name} に乱数種が無い"
        for key in ("n_neighbors", "min_dist", "metric"):
            assert key in d["params"], f"{p.name} に {key} が無い"
        checked += 1
    assert checked > 0, "UMAP の出荷物が 1 つも無く、この検査は何も見ていない"
