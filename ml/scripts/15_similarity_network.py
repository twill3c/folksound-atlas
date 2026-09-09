"""15_similarity_network.py — 音響的近さのネットワーク(仕様書 §69 / §127)。

ノード = 録音、エッジ = 音響的に近いこと。

**辺の張り方**: 上位 20 件をそのまま繋ぐと 6,280 本の毛玉になって何も読めない。
ここでは **相互 k 近傍**(互いに相手の上位 k に入っている場合だけ結ぶ)を使う。
片側だけの「近い」を落とすので、
「たまたま誰にとっても近い一点」に辺が集中するのを防げる。

**配置は手元で計算して座標を配る**(N-02)。ブラウザで毎回力学計算をしない。
`seed` を固定するので、同じ入力なら同じ図になる。

**孤立した点も出す。** 相互 k 近傍では、誰とも結ばれない録音が必ず出る。
隠すと「全部が繋がっている」という嘘になるので、繋がらなかったことを見せる。

あわせて **辺が何を繋いでいるか**を数える。
同じ国どうしを繋いだ辺と、同じ投稿者どうしを繋いだ辺の割合を出す ——
これは §2.4 / §14 の所見を、四つ目の角度から測ったことになる。

出力: public/data/network_<model_id>.json
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

SEED = 42
DEFAULT_K = 4


def chance_same(labels: list[str]) -> float:
    """無作為に選んだ 2 点が同じ札を持つ確率。

    **これが要る理由。** 「辺の何割が同じ国を繋いだか」を国と投稿者で
    そのまま比べてはいけない。国は 37 種、投稿者は 122 種なので、
    でたらめに辺を張っても**国のほうが揃いやすい**。
    実測(2026-09-10): 偶然に同じ国 4.67% / 同じ投稿者 2.81%。
    生の割合では国 43.3% > 投稿者 39.0% で「国が勝つ」ように見えるが、
    偶然比に直すと国 9.3 倍 < 投稿者 13.9 倍で**逆になる**。
    """
    from collections import Counter

    c = Counter(labels)
    n = len(labels)
    if n < 2:
        return 0.0
    same = sum(v * (v - 1) // 2 for v in c.values())
    return same / (n * (n - 1) // 2)


def mutual_knn_edges(sim_items: list[dict], k: int) -> list[tuple[str, str, float]]:
    """互いに相手の上位 k に入っている組だけを辺にする。"""
    topk = {
        row["id"]: {s["id"]: s["score"] for s in row["similar"][:k]}
        for row in sim_items
    }
    edges: list[tuple[str, str, float]] = []
    for a, nbrs in topk.items():
        for b, score in nbrs.items():
            if a < b and b in topk and a in topk[b]:
                edges.append((a, b, float(score)))
    return sorted(edges, key=lambda e: (e[0], e[1]))


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    ap = argparse.ArgumentParser()
    ap.add_argument("--selected", type=Path, default=root / "data" / "raw" / "selected.json")
    ap.add_argument("--embdir", type=Path, default=root / "data" / "embeddings")
    ap.add_argument("--outdir", type=Path, default=root / "public" / "data")
    ap.add_argument("--k", type=int, default=DEFAULT_K)
    args = ap.parse_args()

    import networkx as nx

    sel = json.loads(args.selected.read_text(encoding="utf-8"))["records"]
    meta = {
        r["id"]: {
            "country": canonical_country(r["country"]),
            "uploader": r.get("uploader") or "(不明)",
            "title": r["file"].replace("File:", "").rsplit(".", 1)[0],
        }
        for r in sel
    }
    models = json.loads((args.embdir / "models.json").read_text(encoding="utf-8"))["models"]

    for m in models:
        sim_path = args.embdir / f"similarity_{m['model_id']}.json"
        if not sim_path.exists():
            continue
        sim = json.loads(sim_path.read_text(encoding="utf-8"))
        items = [r for r in sim["items"] if r["id"] in meta]
        edges = mutual_knn_edges(items, args.k)
        ids = [r["id"] for r in items]

        g = nx.Graph()
        g.add_nodes_from(ids)
        g.add_weighted_edges_from(edges)

        # 配置は種を固定して手元で決める(再現できる図にする)
        pos = nx.spring_layout(g, seed=SEED, k=1.6 / np.sqrt(max(len(ids), 1)),
                               iterations=220, weight="weight")

        xs = np.array([pos[i][0] for i in ids])
        ys = np.array([pos[i][1] for i in ids])

        def norm(v: np.ndarray) -> np.ndarray:
            lo, hi = float(v.min()), float(v.max())
            return (v - lo) / (hi - lo) if hi > lo else np.full_like(v, 0.5)

        xs, ys = norm(xs), norm(ys)

        deg = dict(g.degree())
        isolated = [i for i in ids if deg[i] == 0]
        comps = sorted((len(c) for c in nx.connected_components(g)), reverse=True)

        # **辺が何を繋いでいるか**を数える(四つ目の角度)
        same_country = sum(1 for a, b, _ in edges
                           if meta[a]["country"] == meta[b]["country"])
        same_uploader = sum(1 for a, b, _ in edges
                            if meta[a]["uploader"] == meta[b]["uploader"])
        n_e = max(len(edges), 1)
        # 偶然の当たりやすさ(群の数と大きさで決まる)で割って比べる
        base_c = chance_same([meta[i]["country"] for i in ids])
        base_u = chance_same([meta[i]["uploader"] for i in ids])
        ratio_c = same_country / n_e
        ratio_u = same_uploader / n_e
        lift_c = ratio_c / base_c if base_c > 0 else None
        lift_u = ratio_u / base_u if base_u > 0 else None

        payload = {
            "model": m["model_id"],
            "model_name": m["name"],
            "saw_country_labels": m["saw_country_labels"],
            "k": args.k,
            "seed": SEED,
            "edge_rule": "相互 k 近傍(互いに相手の上位 k に入る組だけ)",
            "n_nodes": len(ids),
            "n_edges": len(edges),
            "n_isolated": len(isolated),
            "components": comps[:12],
            "n_components": len(comps),
            "largest_component": comps[0] if comps else 0,
            "edge_composition": {
                "same_country": same_country,
                "same_country_ratio": round(ratio_c, 4),
                "same_country_chance": round(base_c, 4),
                "same_country_lift": round(lift_c, 2) if lift_c else None,
                "same_uploader": same_uploader,
                "same_uploader_ratio": round(ratio_u, 4),
                "same_uploader_chance": round(base_u, 4),
                "same_uploader_lift": round(lift_u, 2) if lift_u else None,
                # **生の割合で比べない。** 群の数が違うので偶然の当たりやすさが違う
                "uploader_lift_exceeds_country": (
                    bool(lift_u > lift_c) if (lift_u and lift_c) else None
                ),
                "note": (
                    "生の割合は群の大きさに左右される(国 37 種 / 投稿者 122 種)。"
                    "偶然に同じ札になる確率で割った lift で比べること"
                ),
            },
            "nodes": [
                {
                    "id": i,
                    "x": round(float(xs[t]), 4),
                    "y": round(float(ys[t]), 4),
                    "deg": int(deg[i]),
                    "country": meta[i]["country"],
                    "uploader": meta[i]["uploader"],
                    "title": meta[i]["title"],
                }
                for t, i in enumerate(ids)
            ],
            "edges": [{"a": a, "b": b, "w": round(w, 4)} for a, b, w in edges],
        }
        out = args.outdir / f"network_{m['model_id']}.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

        print(f"{m['model_id']}: 節点 {len(ids)} / 辺 {len(edges)} / "
              f"孤立 {len(isolated)} / 連結成分 {len(comps)}(最大 {comps[0] if comps else 0})",
              flush=True)
        print(f"    辺の内訳(生): 同じ国 {ratio_c:.1%} / 同じ投稿者 {ratio_u:.1%}",
              flush=True)
        print(f"    偶然比:        国 {lift_c:.1f}x(偶然 {base_c:.1%}) / "
              f"投稿者 {lift_u:.1f}x(偶然 {base_u:.1%}) "
              f"-> {'投稿者' if lift_u > lift_c else '国'}のほうが強い", flush=True)

    (args.outdir / "network_manifest.json").write_text(json.dumps({
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "k": args.k,
        "seed": SEED,
        "layout": "networkx spring_layout(種固定・手元で計算)",
    }, ensure_ascii=False), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
