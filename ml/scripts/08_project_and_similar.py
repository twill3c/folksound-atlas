"""08_project_and_similar.py — UMAP / PCA 射影と音響的近傍(F-06 / F-07 / G-06)。

再現性(仕様書 §51 / G-06):
    UMAP は `random_state` を固定する。固定した値と使ったパラメータは
    出力 JSON に必ず書き出す。**書き出さない再現性は、確かめようがない。**

出力: data/embeddings/umap_<model>.json / pca_<model>.json / similarity_<model>.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

RANDOM_STATE = 42
UMAP_PARAMS = {"n_neighbors": 15, "min_dist": 0.1, "metric": "cosine"}  # 仕様書 §12


def load_embeddings(path: Path) -> tuple[list[str], np.ndarray]:
    d = json.loads(path.read_text(encoding="utf-8"))
    ids = [it["id"] for it in d["items"]]
    X = np.asarray([it["embedding"] for it in d["items"]], dtype=np.float64)
    return ids, X


def top_similar(ids: list[str], X: np.ndarray, top_n: int) -> list[dict]:
    """コサイン類似度の上位。Embedding は L2 正規化済みなので内積でよい。"""
    S = X @ X.T
    np.fill_diagonal(S, -np.inf)          # 自分自身は近傍に含めない
    k = min(top_n, len(ids) - 1) if len(ids) > 1 else 0
    out = []
    for i, rid in enumerate(ids):
        if k <= 0:
            out.append({"id": rid, "similar": []})
            continue
        idx = np.argpartition(-S[i], k - 1)[:k]
        idx = idx[np.argsort(-S[i][idx])]
        out.append({
            "id": rid,
            "similar": [{"id": ids[j], "score": round(float(S[i][j]), 6)} for j in idx],
        })
    return out


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    ap = argparse.ArgumentParser()
    ap.add_argument("--embdir", type=Path, default=root / "data" / "embeddings")
    ap.add_argument("--top-n", type=int, default=20)
    args = ap.parse_args()

    import umap
    from sklearn.decomposition import PCA

    models = json.loads((args.embdir / "models.json").read_text(encoding="utf-8"))["models"]

    for m in models:
        mid = m["model_id"]
        p = args.embdir / f"embedding_{mid}.json"
        if not p.exists():
            continue
        ids, X = load_embeddings(p)
        n = len(ids)
        print(f"{mid}: {n} 件 {X.shape[1]} 次元", flush=True)

        # --- UMAP -----------------------------------------------------------
        nn = max(2, min(UMAP_PARAMS["n_neighbors"], n - 1))
        reducer = umap.UMAP(
            n_neighbors=nn,
            min_dist=UMAP_PARAMS["min_dist"],
            metric=UMAP_PARAMS["metric"],
            random_state=RANDOM_STATE,
            n_components=2,
        )
        XY = reducer.fit_transform(X)
        (args.embdir / f"umap_{mid}.json").write_text(json.dumps({
            "model": mid,
            "method": "umap",
            "params": {**UMAP_PARAMS, "n_neighbors": nn},
            "random_state": RANDOM_STATE,
            "items": [{"id": i, "x": round(float(a), 5), "y": round(float(b), 5)}
                      for i, (a, b) in zip(ids, XY)],
        }, ensure_ascii=False), encoding="utf-8")

        # --- PCA(仕様書 §89: 同じデータを別の方法でも見る)-------------------
        pca = PCA(n_components=2, random_state=RANDOM_STATE)
        XY2 = pca.fit_transform(X)
        (args.embdir / f"pca_{mid}.json").write_text(json.dumps({
            "model": mid,
            "method": "pca",
            "params": {"explained_variance_ratio":
                       [round(float(v), 5) for v in pca.explained_variance_ratio_]},
            "random_state": RANDOM_STATE,
            "items": [{"id": i, "x": round(float(a), 5), "y": round(float(b), 5)}
                      for i, (a, b) in zip(ids, XY2)],
        }, ensure_ascii=False), encoding="utf-8")

        # --- 類似 -------------------------------------------------------------
        (args.embdir / f"similarity_{mid}.json").write_text(json.dumps({
            "model": mid,
            "top_n": args.top_n,
            "items": top_similar(ids, X, args.top_n),
        }, ensure_ascii=False), encoding="utf-8")

        print(f"  UMAP / PCA(寄与率 {pca.explained_variance_ratio_[:2].sum():.3f})/ 類似 を書いた",
              flush=True)

    (args.embdir / "projection_manifest.json").write_text(json.dumps({
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "random_state": RANDOM_STATE,
        "umap_params": UMAP_PARAMS,
        "top_n": args.top_n,
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
