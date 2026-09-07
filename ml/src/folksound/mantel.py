"""mantel.py — 距離行列どうしの相関と、その置換検定(G-08 / G-09)。

なぜ普通の相関ではいけないか:
    距離行列の要素は独立ではない。n 個の対象から n(n−1)/2 個の対ができるが、
    同じ対象が何度も現れるので、素朴な検定は**自由度を大きく数えすぎて**、
    偶然の相関をいくらでも有意にしてしまう。
    Mantel 検定は「対象のラベルを入れ替える」置換で帰無分布を作ることで、
    この非独立性を扱う。**入れ替えるのは要素ではなく対象である。**

偏 Mantel(`partial_mantel_test`)は、第三の距離行列 C の影響を取り除いた
A と B の関係を測る。本プロジェクトでは
    A = 地理距離 / B = 音響距離 / C = 録音の出自(同じ投稿者・同じアーカイブか)
に当て、**H-01 の相関が録音条件で説明されないか**(H-02)を見るために使う。
"""

from __future__ import annotations

import numpy as np


def upper_triangle(D: np.ndarray) -> np.ndarray:
    """対角を除いた上三角を 1 次元で返す。"""
    n = D.shape[0]
    iu = np.triu_indices(n, k=1)
    return np.asarray(D, dtype=np.float64)[iu]


def _pearson(a: np.ndarray, b: np.ndarray) -> float:
    a = a - a.mean()
    b = b - b.mean()
    denom = np.sqrt((a * a).sum() * (b * b).sum())
    if denom < 1e-300:
        return 0.0
    return float((a * b).sum() / denom)


def _permute(D: np.ndarray, order: np.ndarray) -> np.ndarray:
    """**対象**を入れ替える(行と列を同じ順で並べ替える)。"""
    return D[np.ix_(order, order)]


def mantel_test(
    A: np.ndarray,
    B: np.ndarray,
    permutations: int = 999,
    seed: int = 42,
) -> tuple[float, float, np.ndarray]:
    """Mantel 検定。

    戻り値は `(r, p, 帰無分布)`。

    p は両側で、`(|r_perm| >= |r_obs| の数 + 1) / (permutations + 1)` とする。
    **+1 があるので p は決して 0 にならない。** 0 と書くと
    「絶対に偶然でない」と読まれてしまうが、置換検定が言えるのは
    「この回数の入れ替えでは、これより極端なものは出なかった」までである。
    """
    A = np.asarray(A, dtype=np.float64)
    B = np.asarray(B, dtype=np.float64)
    if A.shape != B.shape or A.ndim != 2 or A.shape[0] != A.shape[1]:
        raise ValueError(f"同じ大きさの正方行列が要る: {A.shape} vs {B.shape}")

    a = upper_triangle(A)
    r_obs = _pearson(a, upper_triangle(B))

    rng = np.random.default_rng(seed)
    n = A.shape[0]
    null = np.empty(permutations, dtype=np.float64)
    for i in range(permutations):
        order = rng.permutation(n)
        null[i] = _pearson(a, upper_triangle(_permute(B, order)))

    p = (int(np.sum(np.abs(null) >= abs(r_obs))) + 1) / (permutations + 1)
    return r_obs, p, null


def _residualize(x: np.ndarray, z: np.ndarray) -> np.ndarray:
    """x を z へ回帰した残差(切片つき)。"""
    Z = np.column_stack([np.ones_like(z), z])
    beta, *_ = np.linalg.lstsq(Z, x, rcond=None)
    return x - Z @ beta


def partial_mantel_test(
    A: np.ndarray,
    B: np.ndarray,
    C: np.ndarray,
    permutations: int = 999,
    seed: int = 42,
) -> tuple[float, float, np.ndarray]:
    """偏 Mantel 検定。C を統制した A と B の関係を測る。

    A と B をそれぞれ C へ回帰した**残差どうし**の相関を取り、
    置換で帰無分布を作る。
    """
    A = np.asarray(A, dtype=np.float64)
    B = np.asarray(B, dtype=np.float64)
    C = np.asarray(C, dtype=np.float64)
    if not (A.shape == B.shape == C.shape):
        raise ValueError("三つとも同じ大きさの正方行列が要る")

    c = upper_triangle(C)
    ra = _residualize(upper_triangle(A), c)
    rb = _residualize(upper_triangle(B), c)
    r_obs = _pearson(ra, rb)

    rng = np.random.default_rng(seed)
    n = A.shape[0]
    null = np.empty(permutations, dtype=np.float64)
    for i in range(permutations):
        order = rng.permutation(n)
        Bp = _permute(B, order)
        Cp = _permute(C, order)
        # B と C は同じ入れ替えで動かす(出自は録音に付いた属性なので、
        # 録音を入れ替えれば一緒に動く)
        rb_p = _residualize(upper_triangle(Bp), upper_triangle(Cp))
        ra_p = _residualize(upper_triangle(A), upper_triangle(Cp))
        null[i] = _pearson(ra_p, rb_p)

    p = (int(np.sum(np.abs(null) >= abs(r_obs))) + 1) / (permutations + 1)
    return r_obs, p, null
