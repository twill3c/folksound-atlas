"""test_cluster.py — 音響クラスタと地理クラスタの一致度(仕様書 §90–§91 / Q5)。

期待値の出所(HC-016): **構成による**。答えの分かっている配置を作って当てる。
ARI(調整ランド指数)は偶然一致を補正済みで、無関係な 2 分割なら期待値 0、
同一分割なら 1 になる。これは外部実装にも自分の実装にも依存しない性質である。

ただし**理論上 0 になることと、この標本で 0 になることは別**なので、
実際のラベル分布(国・投稿者はどちらも極端に偏っている)に近い形でも
ラベルを混ぜたら 0 付近へ落ちることを対照で確かめる(HC-074)。
"""

from __future__ import annotations

import numpy as np
import pytest

from folksound.cluster import cluster_agreement, kmeans_labels

pytestmark = pytest.mark.unit


def separated_blobs(groups: int = 5, per: int = 20, d: int = 8, seed: int = 0):
    """明確に分かれた群れ。真の所属が分かっている。"""
    rng = np.random.default_rng(seed)
    centers = rng.normal(size=(groups, d)) * 6.0
    X = np.repeat(centers, per, axis=0) + rng.normal(size=(groups * per, d)) * 0.2
    X = X / np.linalg.norm(X, axis=1, keepdims=True)
    truth = np.repeat(np.arange(groups), per)
    return X, truth


def test_kmeans_recovers_well_separated_groups():
    X, truth = separated_blobs()
    got = kmeans_labels(X, k=5, seed=42)
    assert cluster_agreement(got, truth)["ari"] > 0.9


def test_kmeans_is_deterministic_for_a_seed():
    X, _ = separated_blobs()
    a = kmeans_labels(X, k=5, seed=42)
    b = kmeans_labels(X, k=5, seed=42)
    assert np.array_equal(a, b)


def test_agreement_is_one_for_identical_partitions():
    truth = np.repeat(np.arange(4), 10)
    m = cluster_agreement(truth, truth)
    assert m["ari"] == pytest.approx(1.0)
    assert m["nmi"] == pytest.approx(1.0)


def test_agreement_is_near_zero_for_shuffled_labels():
    """陰性対照: ラベルを混ぜたら一致が消えること。"""
    X, truth = separated_blobs()
    got = kmeans_labels(X, k=5, seed=42)
    rng = np.random.default_rng(1)
    shuffled = rng.permutation(truth)
    assert abs(cluster_agreement(got, shuffled)["ari"]) < 0.15


def test_agreement_survives_a_skewed_label_distribution():
    """この標本の形でも対照が効くこと(HC-074)。

    国も投稿者も極端に偏る(上位 2 者で 9 割)。
    偏った分割でも「混ぜたら 0 付近」が成り立つことを確かめておかないと、
    実データで出た小さな ARI を「偏りのせい」と切り分けられない。
    """
    rng = np.random.default_rng(2)
    n = 300
    # 2 つの巨大な群 + 多数の小さな群、という実データに近い形
    skewed = np.concatenate([
        np.zeros(150, dtype=int), np.ones(100, dtype=int),
        rng.integers(2, 20, n - 250),
    ])
    same = skewed.copy()
    assert cluster_agreement(same, skewed)["ari"] == pytest.approx(1.0)
    assert abs(cluster_agreement(rng.permutation(skewed), skewed)["ari"]) < 0.15


def test_agreement_reports_cluster_counts():
    """何個の群に切ったかを結果に残すこと(後から読めるように)。"""
    X, truth = separated_blobs()
    m = cluster_agreement(kmeans_labels(X, k=5, seed=42), truth)
    assert m["n_clusters"] == 5
    assert m["n_label_groups"] == 5
