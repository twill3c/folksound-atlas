"""12_pretrained_embeddings.py — 外部の事前学習モデルで Embedding を作る(F-13 / 仕様書 §15–22)。

仕様書が V1.1 の目玉に据える「複数モデルによる音響空間比較」の一角。
仕様書は PANNs / AST / HTS-AT / CLAP を候補に挙げるが、ここでは
**torchaudio に同梱された wav2vec 2.0(BASE)** を採る。理由:

  - 追加の依存を入れない(torchaudio だけで完結する)
  - **本コーパスを一度も見ていない。** LibriSpeech 960 時間の音声で
    自己教師あり学習されており、国ラベルはおろか民謡そのものを知らない
  - 自作 CNN とは系統が違う(波形入力の Transformer 対 メル入力の CNN)

**限界を先に書く。これは音声(話し声)のモデルであって音楽のモデルではない。**
音楽向けに作られた表現(PANNs 等)なら別の結果になりうる。
ここで確かめたいのは精度ではなく、
**「本コーパスを一切見ていない表現でも、録音の出自による交絡が出るのか」**である。
出るなら、その交絡は学習のしかたではなく**録音そのもの**に宿っていることになる。

実測(2026-09-08 / この機 / CPU 6 スレッド):
    モデル取得 360MB / 245 秒、5 秒断片 1 つあたり 1.48 秒。
    録音あたり 4 断片に絞って 314 録音で約 31 分。
    自作 CNN が 12 断片なのに対しここが 4 断片なのは**速さの都合**であり、
    断片の取り方(全体から等間隔)は同じ規則を使う。

出力: data/embeddings/embedding_pretrained-w2v2-v1.json と models.json への追記
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
from folksound.preprocess import (  # noqa: E402
    SEGMENT_SECONDS,
    peak_normalize,
    sample_segments,
    segment_signal,
)

MODEL_ID = "pretrained-w2v2-v1"
TARGET_SR = 16000  # wav2vec 2.0 は 16kHz を前提とする


def l2(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-12 else v


def load_16k(path: Path) -> np.ndarray:
    import soundfile as sf
    import soxr

    data, sr = sf.read(str(path), dtype="float32", always_2d=True)
    mono = data.mean(axis=1) if data.shape[1] > 1 else data[:, 0]
    if sr != TARGET_SR:
        mono = soxr.resample(mono, sr, TARGET_SR, quality="MQ")
    return peak_normalize(np.asarray(mono, dtype=np.float32))


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    ap = argparse.ArgumentParser()
    ap.add_argument("--selected", type=Path, default=root / "data" / "raw" / "selected.json")
    ap.add_argument("--features", type=Path, default=root / "data" / "features" / "features.json")
    ap.add_argument("--outdir", type=Path, default=root / "data" / "embeddings")
    ap.add_argument("--segments", type=int, default=4)
    ap.add_argument("--threads", type=int, default=6)
    args = ap.parse_args()

    torch.set_num_threads(args.threads)

    import torchaudio

    bundle = torchaudio.pipelines.WAV2VEC2_BASE
    model = bundle.get_model()
    model.eval()
    assert bundle.sample_rate == TARGET_SR, bundle.sample_rate

    # 特徴量まで通った録音だけを対象にする(出荷物と集合を揃える)
    ok_ids = {f["id"] for f in json.loads(args.features.read_text(encoding="utf-8"))["items"]}
    recs = [
        r for r in json.loads(args.selected.read_text(encoding="utf-8"))["records"]
        if r["id"] in ok_ids
    ]
    print(f"{len(recs)} 録音 x 最大 {args.segments} 断片", flush=True)

    emb: dict[str, list[float]] = {}
    failures: list[dict] = []
    t0 = time.time()
    want = int(round(SEGMENT_SECONDS * TARGET_SR))

    with torch.no_grad():
        for i, r in enumerate(recs, 1):
            try:
                y = load_16k(root / r["path"])
                segs = sample_segments(segment_signal(y, TARGET_SR), args.segments)
                if not segs:
                    failures.append({"id": r["id"], "error": "no segments"})
                    continue
                vecs = []
                for s in segs:
                    x = torch.from_numpy(s["samples"][:want]).unsqueeze(0)
                    feats, _ = model.extract_features(x)
                    # 最終層を時間方向に平均する
                    vecs.append(feats[-1].squeeze(0).mean(dim=0).numpy())
                emb[r["id"]] = l2(np.mean(vecs, axis=0)).astype(float).tolist()
            except Exception as e:  # noqa: BLE001
                # **黙って捨てない**(HC-075)
                failures.append({"id": r["id"], "error": repr(e)})
                print(f"  FAIL {r['id']}: {e}", flush=True)

            if i % 25 == 0:
                el = time.time() - t0
                print(f"  {i}/{len(recs)}  {el:.0f}s "
                      f"(残り約 {el / i * (len(recs) - i):.0f}s)", flush=True)

    dim = len(next(iter(emb.values()))) if emb else 0
    args.outdir.mkdir(parents=True, exist_ok=True)
    (args.outdir / f"embedding_{MODEL_ID}.json").write_text(json.dumps({
        "model": MODEL_ID,
        "dimension": dim,
        "l2_normalized": True,
        "items": [{"id": k, "embedding": v} for k, v in sorted(emb.items())],
    }, ensure_ascii=False), encoding="utf-8")

    # models.json へ追記(既にあれば差し替え)
    mpath = args.outdir / "models.json"
    doc = json.loads(mpath.read_text(encoding="utf-8"))
    card = {
        "model_id": MODEL_ID,
        "name": "wav2vec 2.0(外部・事前学習)",
        "type": "pretrained",
        "embedding_dimension": dim,
        "training_objective": "音声 960 時間の自己教師あり学習(LibriSpeech)。本コーパスは一度も見ていない",
        "training_dataset": "LibriSpeech 960h(外部)",
        "saw_country_labels": False,
        "may_support_geographic_claim": True,
        "label_note": "国名どころか本コーパスの音源自体を見ていない。ただし**話し声のモデル**であって音楽のモデルではない",
        "inference_time_ms": None,
        "model_size_bytes": None,
        "version": "1.0",
    }
    doc["models"] = [m for m in doc["models"] if m["model_id"] != MODEL_ID] + [card]
    doc["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    mpath.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\n{len(emb)} 件 / {dim} 次元 / 失敗 {len(failures)} / {time.time() - t0:.0f}s")
    for f in failures[:5]:
        print(f"  FAIL {f['id']}: {f['error'][:100]}")
    print(f"wrote {args.outdir / f'embedding_{MODEL_ID}.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
