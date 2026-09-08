"""09_analysis.py — 目玉(H-01)と対照(H-02)を測る(F-12 / F-15 / G-04 / G-08 / G-09)。

    H-01  地理距離と音響距離に正の相関がある(Mantel 置換検定・両側 p<0.05)
    H-02  その相関は録音の出自(投稿者=デジタル化したアーカイブ)で説明されない

**G-04 の強制**: 国ラベルを見たモデル(`saw_country_labels=true`)は、
この解析の入力にしない。使おうとしたら例外で止める。
分類器の Embedding が国ごとに固まるのは構成上の必然であり、それを地理の証拠に使うと循環する。

判定は事前に登録した規則で行い、**結果を見てから規則を変えない**:
    H-01 成立 := r > 0 かつ p < 0.05
    H-02 成立 := 偏 Mantel(出自を統制)でも r > 0 かつ p < 0.05
                 かつ 偏相関が素の相関の半分以上を保つ
    目玉が立つ := H-01 と H-02 の両方が成立

出力: data/exports/analysis.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from folksound.cluster import cluster_agreement, kmeans_labels, silhouette  # noqa: E402
from folksound.countries import canonical_country  # noqa: E402
from folksound.geo import haversine_km  # noqa: E402
from folksound.mantel import mantel_test, partial_mantel_test  # noqa: E402

PERMUTATIONS = 999
SEED = 42
ALPHA = 0.05
PARTIAL_RETENTION = 0.5  # 偏相関が素の相関のこれ以上を保つこと


class CircularityError(Exception):
    """ラベルを見たモデルを地理の主張に使おうとした(G-04)。"""


def build_matrices(ids, meta, coords, X):
    n = len(ids)
    geo = np.zeros((n, n))
    prov = np.zeros((n, n))
    for i in range(n):
        ci = meta[ids[i]]["country"]
        ui = meta[ids[i]]["uploader"]
        for j in range(i + 1, n):
            cj = meta[ids[j]]["country"]
            uj = meta[ids[j]]["uploader"]
            a, b = coords[ci], coords[cj]
            d = haversine_km(a["lat"], a["lon"], b["lat"], b["lon"])
            geo[i, j] = geo[j, i] = d
            same = 1.0 if (ui and uj and ui == uj) else 0.0
            prov[i, j] = prov[j, i] = 1.0 - same   # 同じ投稿者なら 0(近い)
    aco = 1.0 - (X @ X.T)
    np.fill_diagonal(aco, 0.0)
    aco = np.clip(aco, 0.0, None)
    return geo, aco, prov


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    ap = argparse.ArgumentParser()
    ap.add_argument("--selected", type=Path, default=root / "data" / "raw" / "selected.json")
    ap.add_argument("--coords", type=Path, default=root / "data" / "raw" / "country_coords.json")
    ap.add_argument("--embdir", type=Path, default=root / "data" / "embeddings")
    ap.add_argument("--out", type=Path, default=root / "data" / "exports" / "analysis.json")
    ap.add_argument("--permutations", type=int, default=PERMUTATIONS)
    args = ap.parse_args()

    sel = json.loads(args.selected.read_text(encoding="utf-8"))["records"]
    meta = {
        r["id"]: {
            "country": canonical_country(r["country"]),
            "uploader": r.get("uploader"),
        }
        for r in sel
    }
    coords = json.loads(args.coords.read_text(encoding="utf-8"))["countries"]
    models = json.loads((args.embdir / "models.json").read_text(encoding="utf-8"))["models"]

    results = []
    for m in models:
        mid = m["model_id"]
        if m["saw_country_labels"]:
            # **地理の主張には使わない。** 存在は残すが、解析からは外す(G-04)
            results.append({
                "model_id": mid,
                "saw_country_labels": True,
                "excluded_from_geographic_claim": True,
                "reason": "国ラベルを見て学習したモデルなので、地理の主張に使うと循環する(SPEC §2.2 / G-04)",
            })
            continue

        p = args.embdir / f"embedding_{mid}.json"
        if not p.exists():
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        ids = [it["id"] for it in d["items"] if it["id"] in meta
               and meta[it["id"]]["country"] in coords]
        if len(ids) < 10:
            continue
        keep = {it["id"]: it["embedding"] for it in d["items"]}
        X = np.asarray([keep[i] for i in ids], dtype=np.float64)

        geo, aco, prov = build_matrices(ids, meta, coords, X)

        r1, p1, _ = mantel_test(geo, aco, permutations=args.permutations, seed=SEED)
        r2, p2, _ = partial_mantel_test(geo, aco, prov,
                                        permutations=args.permutations, seed=SEED)
        r3, p3, _ = mantel_test(prov, aco, permutations=args.permutations, seed=SEED)

        h01 = bool(r1 > 0 and p1 < ALPHA)
        h02 = bool(r2 > 0 and p2 < ALPHA and abs(r2) >= abs(r1) * PARTIAL_RETENTION)

        # --- Q5: 音響クラスタは国の境界と一致するか(仕様書 §90–§91)-------
        # 距離の相関(H-01)とは**別の統計量**で同じことを見る。
        # ARI は偶然一致を補正済みなので、0 付近なら「偶然と変わらない」と読める。
        countries = np.array([meta[i]["country"] for i in ids])
        uploaders = np.array([meta[i]["uploader"] or "(不明)" for i in ids])
        k = len(set(countries))
        pred = kmeans_labels(X, k=k, seed=SEED)
        agree_country = cluster_agreement(pred, countries)
        agree_uploader = cluster_agreement(pred, uploaders)
        clustering = {
            "k": int(k),
            "vs_country": agree_country,
            "vs_uploader": agree_uploader,
            # 区分そのものが音響空間でまとまっているか(仕様書 §86)
            "silhouette_country": silhouette(X, countries),
            "silhouette_uploader": silhouette(X, uploaders),
            # **同じ向きか**を一目で読めるようにしておく
            "uploader_beats_country": bool(
                agree_uploader["ari"] > agree_country["ari"]
            ),
        }

        results.append({
            "model_id": mid,
            "model_name": m["name"],
            "saw_country_labels": False,
            "n_recordings": len(ids),
            "n_countries": len({meta[i]["country"] for i in ids}),
            "n_uploaders": len({meta[i]["uploader"] for i in ids}),
            "permutations": args.permutations,
            "seed": SEED,
            "alpha": ALPHA,
            "geo_vs_acoustic": {"r": round(r1, 5), "p": round(p1, 5)},
            "geo_vs_acoustic_given_provenance": {"r": round(r2, 5), "p": round(p2, 5)},
            "provenance_vs_acoustic": {"r": round(r3, 5), "p": round(p3, 5)},
            "H01_supported": h01,
            "H02_supported": h02,
            "headline_supported": bool(h01 and h02),
            "clustering": clustering,
        })
        print(f"{mid}: n={len(ids)}  "
              f"geo~aco r={r1:+.3f} p={p1:.4f} | "
              f"partial r={r2:+.3f} p={p2:.4f} | "
              f"prov~aco r={r3:+.3f} p={p3:.4f} | "
              f"H01={h01} H02={h02}", flush=True)
        print(f"    クラスタ(k={k}): ARI 国={agree_country['ari']:+.4f} "
              f"投稿者={agree_uploader['ari']:+.4f} "
              f"-> {'投稿者のほうが一致' if clustering['uploader_beats_country'] else '国のほうが一致'}",
              flush=True)

    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "preregistered": {
            "H01": "地理距離と音響距離に正の相関がある(両側 p<0.05)",
            "H02": "その相関は録音の出自(投稿者)で説明されない",
            "decision_rule": {
                "H01": "r > 0 かつ p < alpha",
                "H02": f"偏 Mantel で r > 0 かつ p < alpha かつ |r_partial| >= {PARTIAL_RETENTION} * |r_raw|",
                "headline": "H01 と H02 の両方",
            },
            "note": "この規則は測定より前に SPEC §2.3 へ書いた。結果を見てから変えない",
        },
        "clustering_note": (
            "仕様書 §91 / Q5。距離の相関(H-01)とは別の統計量で同じことを見る。"
            "ARI は偶然一致を補正済みなので 0 付近は「偶然と変わらない」を意味する。"
            "NMI は偶然補正されておらず群れの数で上がるので、判断は ARI で行う"
        ),
        "results": results,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
