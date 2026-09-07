"""07_embeddings.py — 各モデルの Embedding を出す(F-05 / F-13 / SPEC §8)。

録音 1 本の Embedding は、そのセグメントの Embedding の**平均を L2 正規化**したもの。
(平均してから正規化する。正規化してから平均すると長さが 1 でなくなる。)

作る系統:
    feat-baseline-v1  librosa の特徴量を標準化して並べたベクトル。ラベル非依存
    self-ae-v1        オートエンコーダの encode。ラベル非依存
    self-clf-v1       国分類器の encode。**ラベル依存(対照)**

出力: data/embeddings/embedding_<model_id>.json と models.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from folksound.models import EMBEDDING_DIM, FolkCNNAutoencoder, FolkCNNClassifier  # noqa: E402

FEATURE_KEYS = [
    "rms", "zcr", "spectral_centroid", "spectral_bandwidth", "spectral_rolloff", "tempo",
]


def feature_vector(f: dict) -> np.ndarray:
    """従来型特徴量を 1 本のベクトルにする(スカラー 6 + contrast 7 + mfcc 40 + chroma 12)。"""
    parts: list[float] = [float(f[k]) for k in FEATURE_KEYS]
    parts += [float(v) for v in f["spectral_contrast"]]
    parts += [float(v) for v in f["mfcc"]]
    parts += [float(v) for v in f["chroma"]]
    return np.asarray(parts, dtype=np.float64)


def l2(v: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(v)
    return v / n if n > 1e-12 else v


def embed_with_cnn(model, ids: list[str], meldir: Path, max_segments: int) -> dict[str, list[float]]:
    out: dict[str, list[float]] = {}
    model.eval()
    with torch.no_grad():
        for rid in ids:
            f = meldir / f"{rid}.npz"
            if not f.exists():
                continue
            mels = np.load(f)["mels"][:max_segments]
            x = torch.from_numpy(((mels + 80.0) / 80.0).astype(np.float32)).unsqueeze(1)
            z = model.encode(x).numpy()
            out[rid] = l2(z.mean(axis=0)).astype(float).tolist()
    return out


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    ap = argparse.ArgumentParser()
    ap.add_argument("--selected", type=Path, default=root / "data" / "raw" / "selected.json")
    ap.add_argument("--features", type=Path, default=root / "data" / "features" / "features.json")
    ap.add_argument("--meldir", type=Path, default=root / "data" / "normalized" / "mels")
    ap.add_argument("--models", type=Path, default=root / "ml" / "models")
    ap.add_argument("--outdir", type=Path, default=root / "data" / "embeddings")
    ap.add_argument("--max-segments", type=int, default=12)
    args = ap.parse_args()

    torch.set_num_threads(4)
    args.outdir.mkdir(parents=True, exist_ok=True)

    feats = json.loads(args.features.read_text(encoding="utf-8"))["items"]
    ids = [f["id"] for f in feats]
    training = json.loads((args.models / "training.json").read_text(encoding="utf-8"))

    written: list[dict] = []

    # --- feat-baseline-v1(ラベル非依存)-------------------------------------
    M = np.stack([feature_vector(f) for f in feats])
    mu, sd = M.mean(axis=0), M.std(axis=0)
    sd[sd < 1e-9] = 1.0                       # 定数の列で 0 除算を作らない
    Z = (M - mu) / sd
    base = {fid: l2(Z[i]).astype(float).tolist() for i, fid in enumerate(ids)}
    written.append({
        "model_id": "feat-baseline-v1",
        "name": "従来型音響特徴量",
        "type": "features",
        "embedding_dimension": Z.shape[1],
        "training_objective": "学習しない(librosa の特徴量を標準化して並べただけ)",
        "training_dataset": None,
        "saw_country_labels": False,
        "may_support_geographic_claim": True,
        "label_note": "国名を一度も見ていない。地理の話に使える",
        "version": "1.0",
        "_emb": base,
    })

    # --- self-ae-v1(ラベル非依存)-------------------------------------------
    ae_path = args.models / "self-ae-v1.pt"
    if ae_path.exists():
        ae = FolkCNNAutoencoder()
        ae.load_state_dict(torch.load(ae_path, map_location="cpu"))
        written.append({
            "model_id": "self-ae-v1",
            "name": "自作 CNN(自己教師あり)",
            "type": "cnn-autoencoder",
            "embedding_dimension": EMBEDDING_DIM,
            "training_objective": "メルスペクトログラムの再構成のみ",
            "training_dataset": "folk-v1.1 (train split)",
            "saw_country_labels": False,
            "may_support_geographic_claim": True,
            "label_note": "国名を一度も見ていない。地理の話に使える",
            "version": "1.0",
            "_emb": embed_with_cnn(ae, ids, args.meldir, args.max_segments),
        })

    # --- self-clf-v1(ラベル依存・対照)--------------------------------------
    clf_path = args.models / "self-clf-v1.pt"
    if clf_path.exists():
        n_classes = len(training["classifier_countries"])
        clf = FolkCNNClassifier(n_classes=n_classes)
        clf.load_state_dict(torch.load(clf_path, map_location="cpu"))
        written.append({
            "model_id": "self-clf-v1",
            "name": "自作 CNN(国分類器)",
            "type": "cnn-classifier",
            "embedding_dimension": EMBEDDING_DIM,
            "training_objective": f"国の分類({n_classes} 国)",
            "training_dataset": "folk-v1.1 (train split)",
            "saw_country_labels": True,
            "may_support_geographic_claim": False,
            "label_note": "国名を教わって学習した。国ごとに固まるのは仕掛けであって発見ではない",
            "version": "1.0",
            "_emb": embed_with_cnn(clf, ids, args.meldir, args.max_segments),
        })

    models_meta = []
    for m in written:
        emb = m.pop("_emb")
        (args.outdir / f"embedding_{m['model_id']}.json").write_text(
            json.dumps({
                "model": m["model_id"],
                "dimension": m["embedding_dimension"],
                "l2_normalized": True,
                "items": [{"id": k, "embedding": v} for k, v in sorted(emb.items())],
            }, ensure_ascii=False), encoding="utf-8")
        models_meta.append(m)
        print(f"  {m['model_id']}: {len(emb)} 件 / {m['embedding_dimension']} 次元 "
              f"/ ラベル {'見た' if m['saw_country_labels'] else '見ていない'}")

    (args.outdir / "models.json").write_text(
        json.dumps({"generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    "models": models_meta}, ensure_ascii=False, indent=1),
        encoding="utf-8")
    print(f"\nwrote {args.outdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
