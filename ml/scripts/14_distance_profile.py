"""14_distance_profile.py — 地理距離 vs 音響距離の図のもとを作る(F-12 / 仕様書 §25)。

§2.4 は相関係数という**一つの数**で答えを出した。数だけだと
「なぜそうなるのか」が読めないので、**関係そのものを見せる**。

49,141 対を素の散布図にすると潰れて何も読めないので、
**地理距離で束ねて、束ごとの音響距離の平均**を出す(帯として散らばりも出す)。
さらに **同じ投稿者の対 / 違う投稿者の対** に分けて出す。
この二本が離れていれば、「音響的な近さ」が語っているのは
地理ではなく出自だということが**図として見える**。

出力: public/data/distance_profile.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from folksound.countries import canonical_country  # noqa: E402
from folksound.geo import haversine_km  # noqa: E402

# 地理距離の束。0km(=同じ国)は意味が違うので独立した束にする。
BAND_EDGES = [0, 1, 1000, 2000, 3000, 4000, 5000, 6000,
              8000, 10000, 12000, 15000, 20100]
MIN_PAIRS = 30  # これ未満の束は「数が足りない」として値を出さない


def band_label(lo: float, hi: float) -> str:
    if lo == 0:
        return "同じ国"
    if hi >= 20000:
        return f"{int(lo / 1000)},000km 以上"
    return f"{int(lo / 1000)},000–{int(hi / 1000)},000km"


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    ap = argparse.ArgumentParser()
    ap.add_argument("--selected", type=Path, default=root / "data" / "raw" / "selected.json")
    ap.add_argument("--coords", type=Path, default=root / "data" / "raw" / "country_coords.json")
    ap.add_argument("--embdir", type=Path, default=root / "data" / "embeddings")
    ap.add_argument("--out", type=Path,
                    default=root / "public" / "data" / "distance_profile.json")
    ap.add_argument("--top-pairs", type=int, default=12)
    args = ap.parse_args()

    sel = json.loads(args.selected.read_text(encoding="utf-8"))["records"]
    meta = {r["id"]: {"country": canonical_country(r["country"]),
                      "uploader": r.get("uploader"),
                      "title": r["file"].replace("File:", "").rsplit(".", 1)[0]}
            for r in sel}
    coords = json.loads(args.coords.read_text(encoding="utf-8"))["countries"]
    models = json.loads((args.embdir / "models.json").read_text(encoding="utf-8"))["models"]

    out_models = []
    for m in models:
        if m["saw_country_labels"]:
            continue  # 地理の話に使わない(G-04)
        p = args.embdir / f"embedding_{m['model_id']}.json"
        if not p.exists():
            continue
        d = json.loads(p.read_text(encoding="utf-8"))
        ids = [it["id"] for it in d["items"]
               if it["id"] in meta and meta[it["id"]]["country"] in coords]
        X = np.asarray([it["embedding"] for it in d["items"] if it["id"] in ids],
                       dtype=np.float64)
        n = len(ids)

        # 対ごとの (地理距離, 音響距離, 同じ投稿者か)
        geo, aco, same = [], [], []
        for i in range(n):
            ci, ui = meta[ids[i]]["country"], meta[ids[i]]["uploader"]
            a = coords[ci]
            for j in range(i + 1, n):
                cj, uj = meta[ids[j]]["country"], meta[ids[j]]["uploader"]
                b = coords[cj]
                geo.append(haversine_km(a["lat"], a["lon"], b["lat"], b["lon"]))
                aco.append(1.0 - float(X[i] @ X[j]))
                same.append(bool(ui and uj and ui == uj))
        geo = np.asarray(geo)
        aco = np.asarray(aco)
        same = np.asarray(same)

        bands = []
        for k in range(len(BAND_EDGES) - 1):
            lo, hi = BAND_EDGES[k], BAND_EDGES[k + 1]
            in_band = (geo >= lo) & (geo < hi) if lo > 0 else (geo < 1)
            row = {"label": band_label(lo, hi), "lo_km": lo, "hi_km": hi,
                   "n": int(in_band.sum())}
            for key, mask in (("same", in_band & same), ("diff", in_band & ~same)):
                cnt = int(mask.sum())
                # **数が足りない束は値を出さない。** 出すと少数の対が線を暴れさせる
                if cnt >= MIN_PAIRS:
                    v = aco[mask]
                    row[key] = {
                        "n": cnt,
                        "mean": round(float(v.mean()), 5),
                        "p25": round(float(np.percentile(v, 25)), 5),
                        "p75": round(float(np.percentile(v, 75)), 5),
                    }
                else:
                    row[key] = {"n": cnt, "mean": None, "p25": None, "p75": None}
            bands.append(row)

        # Q2(仕様書 §92): 地理的に遠いのに音響的に近い対
        far = geo >= 8000
        order = np.argsort(aco + np.where(far, 0.0, 10.0))[: args.top_pairs]
        pair_idx = []
        c = 0
        lut = {}
        for i in range(n):
            for j in range(i + 1, n):
                lut[c] = (i, j)
                c += 1
        for t in order:
            i, j = lut[int(t)]
            pair_idx.append({
                "a": {"id": ids[i], "title": meta[ids[i]]["title"],
                      "country": meta[ids[i]]["country"]},
                "b": {"id": ids[j], "title": meta[ids[j]]["title"],
                      "country": meta[ids[j]]["country"]},
                "geo_km": round(float(geo[t]), 1),
                "acoustic_distance": round(float(aco[t]), 5),
                "same_uploader": bool(same[t]),
            })

        out_models.append({
            "model_id": m["model_id"],
            "model_name": m["name"],
            "n_recordings": n,
            "n_pairs": int(len(geo)),
            "n_same_uploader_pairs": int(same.sum()),
            "bands": bands,
            "far_but_close": pair_idx,
        })
        print(f"{m['model_id']}: {n} 録音 / {len(geo)} 対 "
              f"(同じ投稿者 {int(same.sum())})", flush=True)
        for b in bands:
            s = b["same"]["mean"]
            df = b["diff"]["mean"]
            print(f"    {b['label']:>18s} n={b['n']:6d}  "
                  f"同={'—' if s is None else f'{s:.4f}'}({b['same']['n']:5d})  "
                  f"異={'—' if df is None else f'{df:.4f}'}({b['diff']['n']:6d})",
                  flush=True)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps({
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "min_pairs_per_band": MIN_PAIRS,
        "note": "音響距離 = 1 - コサイン類似度。地理距離は国の代表点どうしの大円距離",
        "models": out_models,
    }, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
