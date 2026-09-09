"""test_dataset.py — 出荷する成果物そのものの検査(T-003 / T-004 / T-014 / T-015 / T-012b)。

対象は `public/data/*.json`。**まだ作っていない段階では skip する**が、
作ったあとは必ず走る。ここが「データが在るか」ではなく
「配ってよい形か」を見る唯一の場所である。

期待値の出所(HC-016): **SPEC の条項**(§5.2 の権利ゲート、§8 のラベル分離、
schemas/*.schema.json の構造)。実測値ではない。
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "public" / "data"
# 生の Embedding は配らない(N-03)ので、検査は作られた場所に当てる
EMB = ROOT / "data" / "embeddings"

pytestmark = pytest.mark.validation


def load(name: str):
    p = DATA / name
    if not p.exists():
        pytest.skip(f"{name} がまだ無い(ETL 未実行)")
    return json.loads(p.read_text(encoding="utf-8"))


# ---- 許可ライセンス(SPEC §5.2)-------------------------------------------
def _allowed(label: str) -> bool:
    import sys

    sys.path.insert(0, str(ROOT / "ml" / "src"))
    from folksound.rights import classify_license

    return classify_license(label, None).allowed


def test_every_song_has_provenance():
    """T-003 / G-02: 出自の欄が全件埋まっていること。"""
    songs = load("songs.json")["songs"]
    assert songs, "songs.json が空"
    required = ("source", "source_url", "retrieval_date", "sha256",
                "license", "country", "country_source_category")
    missing = [
        (s["id"], k) for s in songs for k in required if not s.get(k)
    ]
    assert not missing, f"出自の欄が欠けている: {missing[:8]}"


def test_source_urls_are_https_commons():
    songs = load("songs.json")["songs"]
    bad = [s["id"] for s in songs if not s["source_url"].startswith("https://")]
    assert not bad, f"https でない source_url: {bad[:5]}"


def test_provenance_detector_catches_a_missing_field():
    """T-004 / G-02 陽性対照: 欄を欠いた行を混ぜたら落ちること。"""
    songs = load("songs.json")["songs"]
    broken = [dict(songs[0])]
    broken[0]["source_url"] = ""
    required = ("source", "source_url", "retrieval_date", "sha256")
    missing = [(s["id"], k) for s in broken for k in required if not s.get(k)]
    assert missing, "欠けた行を検出できていない(この検査は働いていない)"


def test_every_song_passes_the_rights_gate():
    """T-001 / G-01: 出荷物の全件が許可ライセンスであること。"""
    songs = load("songs.json")["songs"]
    bad = [(s["id"], s["license"]) for s in songs if not _allowed(s["license"])]
    assert not bad, f"許可されないライセンスが出荷物に混じっている: {bad[:8]}"


def test_every_song_is_rights_verified():
    songs = load("songs.json")["songs"]
    bad = [s["id"] for s in songs if s.get("rights_verified") is not True]
    assert not bad, f"rights_verified が true でない: {bad[:8]}"


def test_coordinates_are_labelled_as_country_centroids():
    """SPEC §5.5: 国の代表点を `exact` と呼ばないこと。"""
    songs = load("songs.json")["songs"]
    bad = [
        s["id"] for s in songs
        if s.get("latitude") is not None and s.get("coordinate_precision") == "exact"
    ]
    assert not bad, f"国の代表点を exact と称している: {bad[:5]}"


def test_models_declare_label_exposure_consistently():
    """T-012b / G-04: `may_support_geographic_claim` は
    `saw_country_labels` の否定でなければならない。"""
    models = load("models.json")["models"]
    assert models, "models.json が空"
    bad = [
        m["model_id"] for m in models
        if m["may_support_geographic_claim"] == m["saw_country_labels"]
    ]
    assert not bad, f"ラベル露出と地理主張の可否が矛盾している: {bad}"


def test_at_least_one_label_blind_model_exists():
    """地理の話に使えるモデルが一つも無ければ、目玉は測りようがない。"""
    models = load("models.json")["models"]
    blind = [m for m in models if not m["saw_country_labels"]]
    assert blind, "ラベル非依存のモデルが一つも無い"


def test_analysis_excludes_label_seeing_models():
    """G-04: 分類器が地理の解析に入っていないこと。"""
    analysis = load("analysis.json")
    for r in analysis["results"]:
        if r.get("saw_country_labels"):
            assert r.get("excluded_from_geographic_claim") is True, (
                f"{r['model_id']} はラベルを見たのに解析から外れていない"
            )
            assert "geo_vs_acoustic" not in r, (
                f"{r['model_id']} に地理相関の数値が入っている(循環)"
            )


def test_embeddings_are_l2_normalized():
    """T-015 / F-07。"""
    models = load("models.json")["models"]
    checked = 0
    for m in models:
        p = EMB / f"embedding_{m['model_id']}.json"
        if not p.exists():
            continue
        checked += 1
        d = json.loads(p.read_text(encoding="utf-8"))
        assert d["l2_normalized"] is True
        for it in d["items"][:40]:
            n = math.sqrt(sum(v * v for v in it["embedding"]))
            assert abs(n - 1.0) < 1e-4, f"{m['model_id']}/{it['id']} のノルムが {n}"
    # 走査対象が空でないことを別に確かめる(HC-041)。
    # 0 件でも「違反 0」になってしまう検査を残さない。
    assert checked > 0, "Embedding ファイルが 1 つも見つからず、この検査は何も見ていない"


def test_similarity_is_sorted_and_excludes_self():
    """T-015: 降順で、自分自身を含まないこと。"""
    models = load("models.json")["models"]
    for m in models:
        p = DATA / f"similarity_{m['model_id']}.json"
        if not p.exists():
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        for row in d["items"][:60]:
            ids = [x["id"] for x in row["similar"]]
            scores = [x["score"] for x in row["similar"]]
            assert row["id"] not in ids, f"{row['id']} が自分自身を近傍に含む"
            assert scores == sorted(scores, reverse=True), f"{row['id']} が降順でない"
            assert len(ids) == len(set(ids)), f"{row['id']} の近傍に重複"


def test_projection_records_its_seed():
    """G-06: 再現の種を書き出していること。書いていない再現性は確かめようがない。"""
    models = load("models.json")["models"]
    for m in models:
        p = DATA / f"umap_{m['model_id']}.json"
        if not p.exists():
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        assert isinstance(d.get("random_state"), int)
        assert d.get("params")


def test_every_projected_id_exists_in_songs():
    """集合の一致で書く(件数の定数では書かない)。"""
    songs = {s["id"] for s in load("songs.json")["songs"]}
    models = load("models.json")["models"]
    for m in models:
        for kind in ("umap", "pca", "similarity"):
            p = DATA / f"{kind}_{m['model_id']}.json"
            if not p.exists():
                continue
            d = json.loads(p.read_text(encoding="utf-8"))
            ids = {it["id"] for it in d["items"]}
            assert ids <= songs, (
                f"{p.name} に songs.json に無い id がある: "
                f"{sorted(ids - songs)[:5]}"
            )


def test_features_cover_every_song():
    songs = {s["id"] for s in load("songs.json")["songs"]}
    feats = {f["id"] for f in load("features.json")["items"]}
    assert songs == feats, (
        f"songs と features が食い違う: 欠 {sorted(songs - feats)[:5]} / "
        f"余 {sorted(feats - songs)[:5]}"
    )


def test_every_song_has_a_spectrogram_image():
    """仕様書 §126 が MVP 必須に挙げる Spectrogram。

    台帳に載っているだけでなく、**画像が実在すること**まで見る。
    台帳だけを見る検査は、画像を配り忘れても緑になる。
    """
    songs = {s["id"] for s in load("songs.json")["songs"]}
    spec = load("spectrograms.json")
    listed = {s["id"] for s in spec["items"]}
    assert songs == listed, (
        f"songs と spectrograms が食い違う: 欠 {sorted(songs - listed)[:5]} / "
        f"余 {sorted(listed - songs)[:5]}"
    )
    imgdir = ROOT / "public" / "spectrogram"
    missing = [i for i in sorted(listed) if not (imgdir / f"{i}.webp").exists()]
    assert not missing, f"画像が無い: {missing[:5]}"


def test_spectrogram_window_is_recorded():
    """どの区間を描いた絵かが台帳に残っていること。

    区間を書かずに絵だけ配ると、読み手は「録音全体」と受け取る。
    """
    spec = load("spectrograms.json")
    for key in ("window_seconds", "start_fraction", "fmin", "fmax", "n_mels"):
        assert key in spec, f"{key} が spectrograms.json に無い"
    for row in spec["items"][:50]:
        assert row["duration_s"] > 0
        assert row["start_s"] >= 0
        assert row["width"] > 0 and row["height"] > 0


def test_distance_profile_only_covers_label_blind_models():
    """F-12 / G-04: 地理の図にラベルを見たモデルを載せない。"""
    prof = load("distance_profile.json")
    blind = {
        m["model_id"] for m in load("models.json")["models"]
        if not m["saw_country_labels"]
    }
    listed = {m["model_id"] for m in prof["models"]}
    assert listed, "distance_profile.json にモデルが 1 つも無い"
    assert listed <= blind, f"ラベルを見たモデルが混じっている: {sorted(listed - blind)}"


def test_distance_profile_suppresses_thin_bands():
    """対の数が足りない束は値を出さないこと。

    少数の対が線を暴れさせるのを防ぐ仕掛けなので、
    **効いていること**を確かめる(閾値を書いただけでは効かない)。
    """
    prof = load("distance_profile.json")
    floor = prof["min_pairs_per_band"]
    for m in prof["models"]:
        for b in m["bands"]:
            for key in ("same", "diff"):
                s = b[key]
                if s["n"] < floor:
                    assert s["mean"] is None, (
                        f"{m['model_id']} / {b['label']} / {key}: "
                        f"{s['n']} 対しかないのに値が出ている"
                    )
                else:
                    assert s["mean"] is not None


def test_distance_profile_bands_cover_every_pair():
    """束の合計が対の総数と一致すること(取りこぼし・二重計上の検出)。"""
    prof = load("distance_profile.json")
    for m in prof["models"]:
        total = sum(b["n"] for b in m["bands"])
        assert total == m["n_pairs"], (
            f"{m['model_id']}: 束の合計 {total} が対の総数 {m['n_pairs']} と違う"
        )
        for b in m["bands"]:
            assert b["same"]["n"] + b["diff"]["n"] == b["n"], (
                f"{m['model_id']} / {b['label']}: 同/異の合計が束の数と違う"
            )


def test_network_edges_are_mutual_and_consistent():
    """仕様書 §69: 辺は相互 k 近傍。節点集合が songs と一致すること。"""
    songs = {s["id"] for s in load("songs.json")["songs"]}
    checked = 0
    for m in load("models.json")["models"]:
        p = DATA / f"network_{m['model_id']}.json"
        if not p.exists():
            continue
        checked += 1
        net = json.loads(p.read_text(encoding="utf-8"))
        ids = {n["id"] for n in net["nodes"]}
        assert ids <= songs, f"{p.name}: songs に無い節点がある"
        # 辺の端点は必ず節点集合の中
        for e in net["edges"]:
            assert e["a"] in ids and e["b"] in ids, f"{p.name}: 辺の端点が節点に無い"
        # 無向グラフなので同じ組を二度出さない
        pairs = [(e["a"], e["b"]) for e in net["edges"]]
        assert all(a < b for a, b in pairs), f"{p.name}: 辺の向きが正規化されていない"
        assert len(set(pairs)) == len(pairs), f"{p.name}: 辺が重複している"
        # 次数は辺から数え直したものと一致すること
        from collections import Counter

        deg = Counter()
        for a, b in pairs:
            deg[a] += 1
            deg[b] += 1
        for n in net["nodes"]:
            assert n["deg"] == deg.get(n["id"], 0), (
                f"{p.name}: {n['id']} の次数が辺と食い違う"
            )
    assert checked > 0, "ネットワークが 1 つも無く、この検査は何も見ていない"


def test_network_edge_composition_reports_chance_baseline():
    """**生の割合だけを出さない**こと。

    国は 37 種・投稿者は 122 種なので、でたらめに辺を張っても国のほうが揃いやすい。
    偶然比を出さずに割合だけ並べると、逆の結論に読めてしまう
    (実測 2026-09-10: 生では国 43.3% > 投稿者 39.0% だが、
     偶然比では国 9.3x < 投稿者 13.9x)。
    """
    for m in load("models.json")["models"]:
        p = DATA / f"network_{m['model_id']}.json"
        if not p.exists():
            continue
        c = json.loads(p.read_text(encoding="utf-8"))["edge_composition"]
        for key in ("same_country_chance", "same_uploader_chance",
                    "same_country_lift", "same_uploader_lift"):
            assert c.get(key) is not None, f"{p.name}: {key} が無い"
        # 偶然の確率は 0 より大きく 1 未満
        assert 0 < c["same_country_chance"] < 1
        assert 0 < c["same_uploader_chance"] < 1
        # lift = ratio / chance が成り立っていること(数の整合)
        assert c["same_country_lift"] == pytest.approx(
            c["same_country_ratio"] / c["same_country_chance"], rel=0.02
        )


def test_no_non_finite_numbers_in_features():
    for f in load("features.json")["items"]:
        for k, v in f.items():
            if k == "id":
                continue
            vals = v if isinstance(v, list) else [v]
            assert all(math.isfinite(x) for x in vals), f"{f['id']}.{k} が非有限"
