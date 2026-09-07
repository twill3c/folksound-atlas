"""11_prepare_map.py — 世界地図の下地を用意する(F-08)。

出所: Natural Earth Admin 0 Countries(パブリックドメイン)。
フリート内の world-flow-globe が `naciscdn.org` から取得したものを写して使う
(同プロジェクトの SPEC SRC-001。naturalearthdata.com の原典 URL は HTTP 500 を返す)。

本アプリの座標は**国の代表点**なので、詳細な地図は要らない。
むしろ細かすぎる地図は「録音地点がそこまで正確に分かっている」という誤解を招く。
そこで座標を丸め、小さすぎる島を落として軽くする。

出力: public/data/world.geojson
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

SOURCE = Path(r"C:/_ClaudeCode/world-flow-globe/public/data/base/countries.geojson")


def ring_area(ring: list) -> float:
    """符号なしの多角形面積(度^2)。小さな島を落とす判定にだけ使う。"""
    a = 0.0
    for i in range(len(ring) - 1):
        x1, y1 = ring[i][0], ring[i][1]
        x2, y2 = ring[i + 1][0], ring[i + 1][1]
        a += x1 * y2 - x2 * y1
    return abs(a) / 2.0


def simplify_coords(coords, nd: int):
    if isinstance(coords[0], (int, float)):
        return [round(float(coords[0]), nd), round(float(coords[1]), nd)]
    return [simplify_coords(c, nd) for c in coords]


def dedupe(ring: list) -> list:
    """丸めで潰れて重複した点を落とす。輪は閉じたまま保つ。"""
    out = [ring[0]]
    for p in ring[1:]:
        if p != out[-1]:
            out.append(p)
    if len(out) >= 3 and out[0] != out[-1]:
        out.append(out[0])
    return out


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", type=Path, default=SOURCE)
    ap.add_argument("--out", type=Path, default=root / "public" / "data" / "world.geojson")
    ap.add_argument("--decimals", type=int, default=2)
    ap.add_argument("--min-area", type=float, default=0.05, help="度^2。これ未満の環を落とす")
    args = ap.parse_args()

    if not args.src.exists():
        print(f"下地が見つからない: {args.src}")
        return 1

    src = json.loads(args.src.read_text(encoding="utf-8"))
    feats = []
    dropped_rings = 0
    for f in src["features"]:
        g = f["geometry"]
        if g is None:
            continue
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        kept = []
        for poly in polys:
            outer = simplify_coords(poly[0], args.decimals)
            outer = dedupe(outer)
            if len(outer) < 4 or ring_area(outer) < args.min_area:
                dropped_rings += 1
                continue
            kept.append([outer])          # 穴(内側の環)は落とす。世界図には効かない
        if not kept:
            continue
        feats.append({
            "type": "Feature",
            "properties": {
                "name": f["properties"].get("name"),
                "iso_a3": f["properties"].get("iso_a3"),
            },
            "geometry": {"type": "MultiPolygon", "coordinates": kept},
        })

    out = {
        "type": "FeatureCollection",
        "attribution": "Natural Earth (public domain) — Admin 0 Countries",
        "note": "座標を丸め、小さな環を落として軽くしてある。国の代表点を置くための下地であり、"
                "境界の正確さを主張するものではない",
        "features": feats,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")),
                        encoding="utf-8")
    print(f"国 {len(feats)} / 落とした環 {dropped_rings} / "
          f"{args.out.stat().st_size / 1e6:.2f} MB → {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
