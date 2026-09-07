"""test_mantel.py — Mantel 検定と偏 Mantel(G-08 / G-09 / F-12)。

期待値の出所(HC-016):
  **構成による**。答えの分かっている行列を組み立てて当てる。
    - 自分自身との Mantel r は 1
    - 符号を反転した行列との r は −1
    - 独立に作った乱数行列との r は 0 近傍で、p は有意にならない
  これらは外部実装にも自分の実装にも依存しない非循環のオラクルである。

**陽性対照**(HC-041): 相関があるときに検出できることを確かめる。
検出できない検定は、H-01 が落ちても「検定が働いていない」のか
「本当に相関が無い」のか区別できない。
"""

from __future__ import annotations

import numpy as np
import pytest

from folksound.mantel import mantel_test, partial_mantel_test, upper_triangle


def random_distance_matrix(n: int, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    pts = rng.normal(size=(n, 3))
    D = np.linalg.norm(pts[:, None, :] - pts[None, :, :], axis=-1)
    np.fill_diagonal(D, 0.0)
    return D


@pytest.mark.unit
def test_upper_triangle_excludes_diagonal_and_is_symmetric_safe():
    D = np.array([[0.0, 1.0, 2.0], [1.0, 0.0, 3.0], [2.0, 3.0, 0.0]])
    v = upper_triangle(D)
    assert sorted(v.tolist()) == [1.0, 2.0, 3.0]


@pytest.mark.unit
def test_mantel_with_itself_is_one():
    D = random_distance_matrix(30, 0)
    r, p, _ = mantel_test(D, D, permutations=199, seed=1)
    assert r == pytest.approx(1.0, abs=1e-12)
    assert p <= 0.01, "完全相関が有意にならないのは検定が働いていない"


@pytest.mark.unit
def test_mantel_with_negated_is_minus_one():
    D = random_distance_matrix(30, 1)
    r, _, _ = mantel_test(D, -D, permutations=99, seed=1)
    assert r == pytest.approx(-1.0, abs=1e-12)


@pytest.mark.unit
def test_mantel_of_independent_matrices_is_near_zero_and_not_significant():
    """陰性対照: 無関係な二つで有意になってはいけない(誤検出 0)。"""
    A = random_distance_matrix(40, 2)
    B = random_distance_matrix(40, 999)
    r, p, _ = mantel_test(A, B, permutations=499, seed=7)
    assert abs(r) < 0.25, r
    assert p > 0.05, f"無関係な行列で有意になった(r={r}, p={p})"


@pytest.mark.unit
def test_mantel_detects_a_planted_correlation():
    """陽性対照: 相関を仕込んだら検出できること。"""
    A = random_distance_matrix(40, 3)
    rng = np.random.default_rng(4)
    noise = random_distance_matrix(40, 5)
    B = A + 0.35 * noise
    r, p, _ = mantel_test(A, B, permutations=499, seed=8)
    assert r > 0.5, r
    assert p < 0.05, f"仕込んだ相関を検出できていない(r={r}, p={p})"


@pytest.mark.unit
def test_p_value_is_bounded_and_never_zero():
    """置換検定の p は (r_ge + 1) / (N + 1) なので 0 にはならない。

    p=0 と書いてしまうと「絶対に偶然でない」と読まれる。
    """
    D = random_distance_matrix(20, 6)
    _, p, _ = mantel_test(D, D, permutations=99, seed=2)
    assert 0.0 < p <= 1.0
    assert p == pytest.approx(1.0 / 100.0)


@pytest.mark.unit
def test_mantel_is_deterministic_for_a_seed():
    A = random_distance_matrix(25, 7)
    B = random_distance_matrix(25, 8)
    a = mantel_test(A, B, permutations=199, seed=11)
    b = mantel_test(A, B, permutations=199, seed=11)
    assert a[0] == b[0] and a[1] == b[1]


@pytest.mark.unit
def test_partial_mantel_removes_a_shared_driver():
    """G-09 の要。

    A と B が「共通の C」からしか関係していないとき、
    C を統制した偏相関はほぼ 0 になるべきである。
    これは H-02(地理と音響の相関が、録音の出自で説明されないか)を
    測るための道具そのものなので、道具が働くことを先に確かめる。
    """
    C = random_distance_matrix(45, 10)
    n1 = random_distance_matrix(45, 11)
    n2 = random_distance_matrix(45, 12)
    A = C + 0.25 * n1
    B = C + 0.25 * n2

    r_raw, p_raw, _ = mantel_test(A, B, permutations=499, seed=3)
    r_par, p_par, _ = partial_mantel_test(A, B, C, permutations=499, seed=3)

    assert r_raw > 0.5, f"素の相関が出ていない({r_raw})"
    assert abs(r_par) < abs(r_raw) * 0.5, (
        f"共通要因を統制しても相関が落ちない(raw={r_raw}, partial={r_par})"
    )


@pytest.mark.unit
def test_partial_mantel_keeps_a_genuine_link():
    """対照の対照: 本物の関係は統制しても残ること。

    これが無いと「偏相関はいつも 0 になる」だけの道具かもしれない。
    """
    A = random_distance_matrix(45, 20)
    C = random_distance_matrix(45, 21)     # A/B と無関係な第三の行列
    B = A + 0.2 * random_distance_matrix(45, 22)
    r_par, _, _ = partial_mantel_test(A, B, C, permutations=299, seed=5)
    assert r_par > 0.5, f"無関係な C を統制しただけで関係が消えた({r_par})"
