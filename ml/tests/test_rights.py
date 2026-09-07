"""test_rights.py — 権利ゲートの検査(T-001 / T-002 / G-01)。

期待値の出所(HC-016):
  許可・不許可の別は **SPEC §5.2 の条項**から来る。外部データの実測値ではない。
  ここでの「正当な例」は Commons の extmetadata が実際に返す表記から採っている
  (実測 2026-09-07: Category:CC-Zero に属するファイルの LicenseShortName は "CC0")。

HC-041 の規律により、**禁止・検出系の検査には陽性対照を対で置く**。
許可側だけを並べると、判定器を壊しても緩めても緑のままになる。
"""

from __future__ import annotations

import pytest

from folksound.rights import classify_license

# --- 陰性対照: 通ってよいもの(誤検出 0 を確かめる) -------------------------
ALLOWED_CASES = [
    ("Public domain", None, "public_domain"),
    ("PD-old-100", None, "public_domain"),
    ("CC0", None, "public_domain"),
    ("CC-Zero", None, "public_domain"),
    ("CC0 1.0", "cc0", "public_domain"),
    ("CC BY 4.0", "cc-by-4.0", "cc_by"),
    ("CC BY-SA 4.0", "cc-by-sa-4.0", "cc_by_sa"),
    ("CC BY-SA 3.0", "cc-by-sa-3.0", "cc_by_sa"),
    ("CC BY-SA 4.0 International", "cc-by-sa-4.0", "cc_by_sa"),
    (None, "cc-by-sa-2.0", "cc_by_sa"),
    # --- 法域移植版(ported licenses)------------------------------------
    # 実測 2026-09-07: Commons の実データに現れた表記。全 5,492 件を判定したところ、
    # 'CC BY 3.0 us'(3 件)/ 'CC BY-SA 2.0 de'(1 件)/ 'CC BY-SA 3.0 cl'(1 件)が
    # 「許可リストに無い」で落ちていた。これらは CC BY / CC BY-SA の法域移植版であり、
    # NC でも ND でもないので通してよい。**落ちているのを見てから足した。**
    ("CC BY 3.0 us", "cc-by-3.0-us", "cc_by"),
    ("CC BY-SA 2.0 de", "cc-by-sa-2.0-de", "cc_by_sa"),
    ("CC BY-SA 3.0 cl", "cc-by-sa-3.0-cl", "cc_by_sa"),
    ("CC BY-SA 2.5 in", "cc-by-sa-2.5-in", "cc_by_sa"),
]

# --- 陽性対照: 必ず捕まえるべきもの ----------------------------------------
# 第 3 要素は **どの経路で落ちるべきか**。結論(不許可)だけを見る対照は、
# 判定器を壊しても緑のままになる —— 実測 2026-09-07: 拒否リストを空にする変異体を
# 当てたところ、NC/ND 系は「許可リストに無い」で unknown となり、
# `allowed` だけを見る 10 件は全部通ってしまった(落ちたのは family を見る 1 件のみ)。
# したがって対照は **family まで固定する**(HC-065: 結論でなく経路を比べる)。
DENIED_CASES = [
    ("CC BY-NC 4.0", "cc-by-nc-4.0", "rejected"),        # 非営利限定
    ("CC BY-NC-SA 3.0", "cc-by-nc-sa-3.0", "rejected"),  # by も sa も含むが NC
    ("CC BY-ND 4.0", "cc-by-nd-4.0", "rejected"),        # 改変禁止
    ("Fair use", None, "rejected"),
    ("All rights reserved", None, "rejected"),
    ("Copyrighted free use", None, "rejected"),
    ("GFDL", "gfdl", "rejected"),
    ("Some Unknown Custom Tag", None, "unknown"),        # 未知は許可リスト側で落ちる
    # 法域移植を通すようにしても、NC/ND の移植版まで通してしまわないこと
    ("CC BY-NC 3.0 us", "cc-by-nc-3.0-us", "rejected"),
    ("CC BY-NC-SA 2.0 de", "cc-by-nc-sa-2.0-de", "rejected"),
    ("CC BY-ND 3.0 us", "cc-by-nd-3.0-us", "rejected"),
    # 実測で見つかった未知の表記。人が確かめるまで通さない(2026-09-07)
    ("EEF OAL-1", None, "unknown"),
    (None, None, "unknown"),                             # 表記が無い
    ("", "", "unknown"),                                 # 空文字も表記が無いのと同じ
]


@pytest.mark.unit
@pytest.mark.parametrize("short,machine,family", ALLOWED_CASES)
def test_allowed_licenses_pass(short, machine, family):
    """T-001 / G-01: 許可すべき表記が通ること(誤検出 0)。"""
    d = classify_license(short, machine)
    assert d.allowed, f"{short!r}/{machine!r} を落とした: {d.reason}"
    assert d.family == family, f"{short!r} の族が {d.family}(期待 {family})"


@pytest.mark.unit
@pytest.mark.parametrize("short,machine,family", DENIED_CASES)
def test_denied_licenses_are_caught(short, machine, family):
    """T-002 / G-01 陽性対照: 禁止・未知の表記を、**期待した経路で**落とすこと。

    `allowed` だけでなく `family` まで確かめる。そうしないと、
    拒否リストが空になっても許可リスト側が拾って緑のままになる。
    """
    d = classify_license(short, machine)
    assert not d.allowed, f"{short!r}/{machine!r} を通してしまった(family={d.family})"
    assert d.family == family, (
        f"{short!r} は {family} で落ちるべきだが {d.family} で落ちた。"
        "判定経路が変わっている(拒否リストが効いていない可能性)"
    )


@pytest.mark.unit
def test_nc_is_rejected_even_when_by_sa_present():
    """NC の検出が BY/SA の許可より先に効くこと。

    これは順序に依存する性質なので、順序を入れ替えると落ちる形で固定しておく。
    """
    d = classify_license("CC BY-NC-SA 4.0", "cc-by-nc-sa-4.0")
    assert not d.allowed
    assert d.family == "rejected"


@pytest.mark.unit
def test_unknown_is_not_silently_allowed():
    """未知の表記は unknown として **不許可** になること。

    「判定できないものを通す」方向に壊れていないことを名指しで確かめる。
    """
    d = classify_license("Totally New License 9.9", None)
    assert not d.allowed
    assert d.family == "unknown"
    assert "許可リスト" in d.reason


@pytest.mark.unit
def test_controls_are_disjoint():
    """対照が対照として成り立つ前提を固定する(HC-079)。

    許可側と不許可側に同じ表記が現れていたら、この検査は何も言っていない。
    """
    allowed = {(s, m) for s, m, _ in ALLOWED_CASES}
    denied = {(s, m) for s, m, _ in DENIED_CASES}
    assert not (allowed & denied), "許可側と不許可側に同じ入力がある"
    assert len(allowed) >= 5 and len(denied) >= 5, "対照の数が少なすぎる"
