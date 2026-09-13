"""test_home_derived.py — ホームの「測ってみた答え」が測定結果から導かれているか(T-019 / F-15 / G-08)。

**実装ではなく振る舞いを見る**(HC-080)。`page.tsx` のソースを grep するのでなく、
**ビルド後に配られる `out/index.html` に実際に出ている数**を読み、
Python で**別に**数え直した値と突き合わせる。

これは「数え上げの規則」の二実装照合である(TS で数えて描いたもの と Python で数え直したもの)。
科学的な結論そのものを検査するものではない。

HTML の読み方について(2026-09-14 に一度書き誤ったので、正しい前提を残す):
    React の静的描画は、隣り合う文字列節点のあいだに `<!-- -->` を挟む。
    `<strong>{a} / {b}</strong>` は `3<!-- --> / <!-- -->3` として出る。
    **生の HTML に正規表現を当てると "3 / 3" は拾えない。** 印を剥がしてから当てる。
    なお、タグを剥がす `<[^>]+>` は `<!-- -->` も一緒に剥がす(`<` で始まり `>` で終わり、
    中に `>` を含まないため)。最初「コメントを別に除かないと一致しない」と書いたが、
    それは**誤り**で、前提を確かめる検査が落ちて分かった。

期待値の出所(HC-016): `public/data/analysis.json` と `public/data/network_*.json`(出荷物)。
"""

from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "out" / "index.html"
DATA = ROOT / "public" / "data"

FRACTION = re.compile(r"(\d+)\s*/\s*(\d+)")

pytestmark = pytest.mark.validation


def rendered_fractions(html: str) -> list[tuple[int, int]]:
    """`<ul class="home-evidence">` の中に出ている "N / M" を上から順に返す。"""
    m = re.search(r'<ul class="home-evidence">(.*?)</ul>', html, flags=re.S)
    assert m, "ホームに home-evidence の一覧が無い(描画されていない)"
    text = re.sub(r"<[^>]+>", " ", m.group(1))  # タグと React の `<!-- -->` を剥がす
    return [(int(a), int(b)) for a, b in FRACTION.findall(text)]


def expected_fractions(analysis: dict, nets: dict[str, dict]) -> list[tuple[int, int]]:
    """page.tsx と**同じ規則を Python で別に書いた**数え上げ。"""
    blind = [
        r for r in analysis["results"]
        if not r.get("saw_country_labels") and r.get("geo_vs_acoustic")
    ]
    alpha = blind[0].get("alpha", 0.05) if blind else 0.05
    n_blind = len(blind)
    n_prov = sum(1 for r in blind if r["provenance_vs_acoustic"]["p"] < alpha)
    n_ari = sum(1 for r in blind if (r.get("clustering") or {}).get("uploader_beats_country"))
    found = [nets[r["model_id"]] for r in blind if r["model_id"] in nets]
    n_net = sum(1 for n in found if n["edge_composition"]["uploader_lift_exceeds_country"])
    return [(n_prov, n_blind), (n_ari, n_blind), (n_net, len(found))]


def load_inputs():
    if not OUT.exists():
        pytest.skip("out/index.html が無い(npm run build をまだ回していない)")
    analysis = json.loads((DATA / "analysis.json").read_text(encoding="utf-8"))
    nets = {}
    for p in DATA.glob("network_*.json"):
        if p.name == "network_manifest.json":
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        nets[d["model"]] = d
    return OUT.read_text(encoding="utf-8"), analysis, nets


def test_home_evidence_matches_an_independent_recount():
    """T-019: 画面の数が、JSON から別に数え直した数と一致すること。"""
    html, analysis, nets = load_inputs()
    got = rendered_fractions(html)
    want = expected_fractions(analysis, nets)
    assert len(got) == 3, f"数の組が 3 つ出ていない: {got}"
    assert got == want, f"画面の数 {got} と JSON から数え直した数 {want} が違う"


def test_recount_is_sensitive_to_the_data():
    """陽性対照: 入力を一つ変えたら期待値が変わり、画面と食い違うこと。

    これが無いと、上の検査は「数え方がたまたま定数を返す」場合でも緑になる。
    判定を一つ反転させた写しで数え直し、**画面と一致しなくなる**ことを確かめる。
    """
    html, analysis, nets = load_inputs()
    got = rendered_fractions(html)

    flipped = copy.deepcopy(analysis)
    target = next(
        r for r in flipped["results"]
        if not r.get("saw_country_labels") and r.get("clustering")
    )
    target["clustering"]["uploader_beats_country"] = not target["clustering"]["uploader_beats_country"]
    assert expected_fractions(flipped, nets) != got, (
        "判定を反転させても期待値が画面と一致したまま(この検査は入力を見ていない)"
    )


def test_markup_must_be_stripped_before_matching():
    """HTML の読み方の前提を固定する(HC-079)。

    **生の HTML に当てると拾えず、印を剥がすと拾える**ことを実物の一片で確かめる。
    前提が崩れた(React が区切りを入れなくなった等)ら、ここで分かる。
    """
    sample = '<ul class="home-evidence"><li><strong>3<!-- --> / <!-- -->3</strong></li></ul>'
    assert FRACTION.findall(sample) == [], (
        "生の HTML のままで拾えてしまった —— 前提(React が節点の間に印を挟む)が変わった"
    )
    assert rendered_fractions(sample) == [(3, 3)]
