"""cluster.py — 音響クラスタと、人が付けた区分との一致度(仕様書 §90–§91 / Q5)。

仕様書 §91 は「地理的分類と音響的分類はどの程度一致するか」を問う。
これは §2.3 の H-01(距離の相関)とは**別の統計量**で同じことを見る道具である。
距離で見ても、群れの切り方で見ても同じ答えになるなら、その答えは物差しに依らない。

**ARI(調整ランド指数)を使う。** 偶然の一致を補正済みなので、
無関係な 2 分割なら期待値 0、同一分割なら 1 になる —— つまり
**帰無分布を別に作らなくても「偶然より一致しているか」が読める**。
NMI(正規化相互情報量)も併記するが、こちらは偶然補正されていないので、
群れの数が増えると勝手に上がる。**判断は ARI で行う。**
"""

from __future__ import annotations

import numpy as np


def kmeans_labels(X: np.ndarray, k: int, seed: int = 42) -> np.ndarray:
    """L2 正規化済み Embedding を k 個へ切る。

    球面上のベクトルなので、ユークリッド k-means は球面 k-means と
    単調に対応する(正規化済みなら距離の大小関係が保たれる)。
    """
    from sklearn.cluster import KMeans

    k = max(2, min(int(k), len(X) - 1))
    km = KMeans(n_clusters=k, random_state=seed, n_init=10)
    return km.fit_predict(np.asarray(X, dtype=np.float64))


def cluster_agreement(pred: np.ndarray, labels: np.ndarray) -> dict:
    """クラスタと人手の区分の一致度。

    `pred` はクラスタ番号、`labels` は国や投稿者などの区分。
    どちらも「番号の付き方」には意味が無いので、番号に依らない指標を使う。
    """
    from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score

    pred = np.asarray(pred)
    labels = np.asarray(labels)
    if pred.shape != labels.shape:
        raise ValueError(f"長さが違う: {pred.shape} vs {labels.shape}")

    return {
        "ari": float(adjusted_rand_score(labels, pred)),
        "nmi": float(normalized_mutual_info_score(labels, pred)),
        "n_clusters": int(len(np.unique(pred))),
        "n_label_groups": int(len(np.unique(labels))),
        "n": int(len(pred)),
    }


def silhouette(X: np.ndarray, labels: np.ndarray) -> float | None:
    """区分そのものが音響空間でどれだけまとまっているか(仕様書 §86)。

    群れが 1 つしか無い / 全部単独、のときは定義できないので None を返す
    (**0 を返さない** —— 0 は「まとまっていない」という意味を持ってしまう)。
    """
    from sklearn.metrics import silhouette_score

    labels = np.asarray(labels)
    n_groups = len(np.unique(labels))
    if n_groups < 2 or n_groups >= len(labels):
        return None
    try:
        return float(silhouette_score(np.asarray(X, dtype=np.float64),
                                      labels, metric="cosine"))
    except Exception:  # noqa: BLE001
        return None
