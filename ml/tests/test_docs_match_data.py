"""test_docs_match_data.py — 文書に書いた数と、実際の出力を突き合わせる(HC-152)。

**テストは実装を守るが、SPEC・README に書いた数を守るものは何も無い。**
実際にこのプロジェクトで、SPEC §2.4 に「投稿者 63 人」と書いたまま
出力は 122 人という食い違いが起き、画面を目視して初めて気づいた。
数値は具体的なので、後から読むと実測値として振る舞ってしまう。

そこで「SPEC に書いた数」を機械で読み、出力と照合する。
照合できない形で数を書いたら、それはここで守れない数だということでもある。
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = ROOT / "SPEC.md"
ANALYSIS = ROOT / "data" / "exports" / "analysis.json"

pytestmark = pytest.mark.validation


def _analysis():
    if not ANALYSIS.exists():
        pytest.skip("analysis.json がまだ無い")
    d = json.loads(ANALYSIS.read_text(encoding="utf-8"))
    for r in d["results"]:
        if "n_recordings" in r:
            return d, r
    pytest.skip("解析結果が空")


def test_spec_headline_counts_match_analysis():
    """SPEC §2.4 の「録音 N 本 / M 国 / 投稿者 K 人」が出力と一致すること。"""
    _, r = _analysis()
    text = SPEC.read_text(encoding="utf-8")
    m = re.search(r"録音\s*([0-9,]+)\s*本\s*/\s*([0-9,]+)\s*国\s*/\s*投稿者\s*([0-9,]+)\s*人", text)
    assert m, "SPEC §2.4 の見出しの数が読み取れない(書式を変えたら、この検査も直す)"
    n_rec, n_cnt, n_up = (int(x.replace(",", "")) for x in m.groups())
    assert (n_rec, n_cnt, n_up) == (
        r["n_recordings"], r["n_countries"], r["n_uploaders"]
    ), (
        f"SPEC が {n_rec}本/{n_cnt}国/{n_up}人 と書いているが、"
        f"analysis.json は {r['n_recordings']}/{r['n_countries']}/{r['n_uploaders']}"
    )


def test_spec_permutation_settings_match_analysis():
    _, r = _analysis()
    text = SPEC.read_text(encoding="utf-8")
    m = re.search(r"置換\s*([0-9,]+)\s*回・乱数種\s*([0-9]+)", text)
    assert m, "SPEC の置換回数・乱数種が読み取れない"
    perms, seed = int(m.group(1).replace(",", "")), int(m.group(2))
    assert perms == r["permutations"], f"置換回数 SPEC={perms} 実際={r['permutations']}"
    assert seed == r["seed"], f"乱数種 SPEC={seed} 実際={r['seed']}"


def test_spec_correlation_table_matches_analysis():
    """SPEC §2.4 の相関表の r と p が、出力と一致すること。

    ここが本命である。相関の値は「もっともらしい」ので、
    ずれていても読んだ人には分からない。
    """
    d, _ = _analysis()
    by_id = {r["model_id"]: r for r in d["results"] if "geo_vs_acoustic" in r}
    text = SPEC.read_text(encoding="utf-8")

    checked = 0
    for mid, key, label in [
        ("feat-baseline-v1", "geo_vs_acoustic", "H-01"),
        ("feat-baseline-v1", "geo_vs_acoustic_given_provenance", "H-02"),
        ("feat-baseline-v1", "provenance_vs_acoustic", "対抗"),
        ("self-ae-v1", "geo_vs_acoustic", "H-01"),
        ("self-ae-v1", "geo_vs_acoustic_given_provenance", "H-02"),
        ("self-ae-v1", "provenance_vs_acoustic", "対抗"),
    ]:
        if mid not in by_id:
            continue
        got = by_id[mid][key]
        # SPEC には "r = +0.039(p = 0.0010)" のような形で書いてある
        r_str = f"{got['r']:+.3f}".replace("+0.", "+0.").replace("-0.", "−0.")
        alt = f"{got['r']:.3f}"
        p_str = f"{got['p']:.4f}"
        found = (
            (r_str in text or alt in text or f"{got['r']:+.3f}" in text)
            and p_str in text
        )
        assert found, (
            f"{mid}/{key} の値が SPEC に見当たらない: r={got['r']} p={got['p']}。"
            "SPEC を実測に合わせて直すこと"
        )
        checked += 1

    # 走査対象が空でないことを確かめる(HC-041)
    assert checked >= 4, f"照合できた項目が {checked} 件しかなく、この検査は何も見ていない"
