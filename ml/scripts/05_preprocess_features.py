"""05_preprocess_features.py — 正規化・セグメント化・特徴量抽出(F-03 / F-04)。

入力: data/raw/selected.json と data/raw/audio/
出力:
    data/normalized/mels/<id>.npz     セグメントごとのメルスペクトログラム(学習用)
    data/features/features.json       録音ごとの従来型音響特徴量
    data/features/waveforms.json      表示用の波形エンベロープ(仕様書 §115)

波形はブラウザで毎回 WAV を解析させず、ここで包絡線に落として JSON にする。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from folksound.features import HOP_LENGTH, N_FFT, N_MELS, extract_features  # noqa: E402
from folksound.preprocess import (  # noqa: E402
    TARGET_SR,
    load_and_standardize,
    segment_signal,
)

WAVEFORM_BUCKETS = 400  # 表示用の包絡線の解像度


def waveform_envelope(x: np.ndarray, buckets: int = WAVEFORM_BUCKETS) -> list[float]:
    """表示用の包絡線。各バケツの最大絶対値を取る。

    **これは表示用の加工値なので、検査の根拠には使わない**(HC-068)。
    """
    if x.size == 0:
        return [0.0] * buckets
    idx = np.array_split(np.arange(x.size), buckets)
    return [float(np.abs(x[i]).max()) if len(i) else 0.0 for i in idx]


def mel_of(seg: np.ndarray, sr: int) -> np.ndarray:
    import librosa

    m = librosa.feature.melspectrogram(
        y=seg, sr=sr, n_fft=N_FFT, hop_length=HOP_LENGTH, n_mels=N_MELS,
        fmin=20, fmax=8000,
    )
    return librosa.power_to_db(m, ref=np.max).astype(np.float32)


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    ap = argparse.ArgumentParser()
    ap.add_argument("--inp", type=Path, default=root / "data" / "raw" / "selected.json")
    ap.add_argument("--meldir", type=Path, default=root / "data" / "normalized" / "mels")
    ap.add_argument("--outdir", type=Path, default=root / "data" / "features")
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    sel = json.loads(args.inp.read_text(encoding="utf-8"))
    recs = sel["records"]
    if args.limit:
        recs = recs[: args.limit]

    args.meldir.mkdir(parents=True, exist_ok=True)
    args.outdir.mkdir(parents=True, exist_ok=True)

    features: list[dict] = []
    waveforms: list[dict] = []
    seg_index: list[dict] = []
    failures: list[dict] = []

    for i, r in enumerate(recs, 1):
        path = root / r["path"]
        try:
            y, orig_sr = load_and_standardize(path)
        except Exception as e:  # noqa: BLE001
            # **黙って捨てない。** 落ちたものは名指しで残す(HC-075)
            failures.append({"id": r["id"], "path": r["path"], "error": repr(e)})
            print(f"  FAIL {r['id']}: {e}", flush=True)
            continue

        duration = float(y.size) / TARGET_SR
        segs = segment_signal(y, TARGET_SR)
        if not segs:
            failures.append({"id": r["id"], "path": r["path"], "error": "no segments"})
            continue

        mels = np.stack([mel_of(s["samples"], TARGET_SR) for s in segs])
        np.savez_compressed(
            args.meldir / f"{r['id']}.npz",
            mels=mels,
            padded=np.array([s["padded"] for s in segs]),
        )

        feats = extract_features(y, TARGET_SR)
        features.append({"id": r["id"], **feats})
        waveforms.append({"id": r["id"], "envelope": waveform_envelope(y),
                          "duration_s": round(duration, 3)})
        seg_index.append({
            "id": r["id"], "segments": len(segs),
            "duration_s": round(duration, 3),
            "sample_rate_original": orig_sr,
            "padded_segments": int(sum(bool(s["padded"]) for s in segs)),
        })

        if i % 20 == 0:
            print(f"  {i}/{len(recs)}", flush=True)

    (args.outdir / "features.json").write_text(
        json.dumps({"feature_version": "1.0", "items": features},
                   ensure_ascii=False), encoding="utf-8")
    (args.outdir / "waveforms.json").write_text(
        json.dumps({"buckets": WAVEFORM_BUCKETS, "items": waveforms},
                   ensure_ascii=False), encoding="utf-8")
    (args.outdir / "segments.json").write_text(
        json.dumps({
            "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "target_sr": TARGET_SR,
            "processed": len(seg_index),
            "failed": len(failures),
            "failures": failures,
            "items": seg_index,
        }, ensure_ascii=False, indent=1), encoding="utf-8")

    total_segs = sum(s["segments"] for s in seg_index)
    print(f"\n処理 {len(seg_index)} 録音 / 失敗 {len(failures)} / セグメント {total_segs}")
    print(f"wrote {args.outdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
