"""05_preprocess_features.py — 正規化・セグメント化・特徴量抽出(F-03 / F-04)。

入力: data/raw/selected.json と data/raw/audio/
出力:
    data/normalized/mels/<id>.npz     セグメントごとのメルスペクトログラム(学習用)
    data/features/features.json       録音ごとの従来型音響特徴量
    data/features/waveforms.json      表示用の波形エンベロープ(仕様書 §115)
    data/features/segments.json       セグメント数と、失敗したものの名指し

速さについて(実測 2026-09-08):
    律速は**音声の復号**である。OGG Vorbis を 1 本読むのに 8 秒前後かかり、
    再標本化(soxr MQ)は 0.6 秒で済む。つまり工夫すべきは変換ではなく、
    **復号を並列に流すこと**だった。この機は 8 コアなので、プロセスプールで
    複数本を同時に処理する(1 プロセス 1 録音。録音どうしは独立なので分けられる)。
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from folksound.features import HOP_LENGTH, N_FFT, N_MELS, extract_features  # noqa: E402
from folksound.preprocess import (  # noqa: E402
    TARGET_SR,
    peak_normalize,
    sample_segments,
    segment_signal,
)

WAVEFORM_BUCKETS = 400  # 表示用の包絡線の解像度

# 1 本から取るセグメントの上限。学習側(06_train)の上限と揃える。
MAX_SEGMENTS = 12


def waveform_envelope(x: np.ndarray, buckets: int = WAVEFORM_BUCKETS) -> list[float]:
    """表示用の包絡線。各バケツの最大絶対値を取る。

    **これは表示用の加工値なので、検査の根拠には使わない**(HC-068)。
    """
    if x.size == 0:
        return [0.0] * buckets
    idx = np.array_split(np.arange(x.size), buckets)
    return [round(float(np.abs(x[i]).max()), 4) if len(i) else 0.0 for i in idx]


def load_fast(path: Path) -> tuple[np.ndarray, int]:
    """soundfile で読み、soxr で 22050Hz mono へ落とす。

    librosa.load を経由しない。復号が律速なので、余計な層を挟まない。
    """
    import soundfile as sf
    import soxr

    data, sr = sf.read(str(path), dtype="float32", always_2d=True)
    mono = data.mean(axis=1) if data.shape[1] > 1 else data[:, 0]
    if sr != TARGET_SR:
        mono = soxr.resample(mono, sr, TARGET_SR, quality="MQ")
    return peak_normalize(np.asarray(mono, dtype=np.float32)), sr


def process_one(job: tuple[str, str, str]) -> dict:
    """1 録音ぶん。**プロセスプールから呼ばれるので、例外を外へ投げない。**"""
    rid, rel_path, root_str = job
    root = Path(root_str)
    try:
        import librosa

        y, orig_sr = load_fast(root / rel_path)
        duration = float(y.size) / TARGET_SR
        all_segs = segment_signal(y, TARGET_SR)
        if not all_segs:
            return {"id": rid, "ok": False, "error": "no segments"}
        segs = sample_segments(all_segs, MAX_SEGMENTS)

        mels = np.stack([
            librosa.power_to_db(
                librosa.feature.melspectrogram(
                    y=s["samples"], sr=TARGET_SR, n_fft=N_FFT,
                    hop_length=HOP_LENGTH, n_mels=N_MELS, fmin=20, fmax=8000,
                ),
                ref=np.max,
            ).astype(np.float32)
            for s in segs
        ])

        meldir = root / "data" / "normalized" / "mels"
        meldir.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            meldir / f"{rid}.npz",
            mels=mels,
            padded=np.array([s["padded"] for s in segs]),
        )

        # 特徴量は **CNN が見るのと同じ材料**(抜き出した 12 セグメントの連結)から取る。
        # 全長から取ると、CNN の見ているものと食い違う量を並べることになる。
        excerpt = np.concatenate([s["samples"] for s in segs])
        feats = extract_features(excerpt, TARGET_SR)

        return {
            "id": rid,
            "ok": True,
            "features": feats,
            "envelope": waveform_envelope(y),
            "duration_s": round(duration, 3),
            "sample_rate_original": orig_sr,
            "segments": len(segs),
            "segments_available": len(all_segs),
            "padded_segments": int(sum(bool(s["padded"]) for s in segs)),
            "excerpt_seconds": round(float(excerpt.size) / TARGET_SR, 2),
        }
    except Exception as e:  # noqa: BLE001
        # **黙って捨てない。** 落ちたものは名指しで残す(HC-075)
        return {"id": rid, "ok": False, "error": repr(e)}


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    ap = argparse.ArgumentParser()
    ap.add_argument("--inp", type=Path, default=root / "data" / "raw" / "selected.json")
    ap.add_argument("--outdir", type=Path, default=root / "data" / "features")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 2))
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()

    sel = json.loads(args.inp.read_text(encoding="utf-8"))
    recs = sel["records"]
    if args.limit:
        recs = recs[: args.limit]

    args.outdir.mkdir(parents=True, exist_ok=True)
    jobs = [(r["id"], r["path"], str(root)) for r in recs]
    print(f"{len(jobs)} 録音 / ワーカ {args.workers}", flush=True)

    results: list[dict] = []
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(process_one, j): j[0] for j in jobs}
        done = 0
        for fut in as_completed(futs):
            results.append(fut.result())
            done += 1
            if done % 20 == 0 or done == len(jobs):
                el = time.time() - t0
                print(f"  {done}/{len(jobs)}  {el:.0f}s "
                      f"(残り約 {el / done * (len(jobs) - done):.0f}s)", flush=True)

    ok = [r for r in results if r["ok"]]
    bad = [r for r in results if not r["ok"]]
    ok.sort(key=lambda r: r["id"])

    (args.outdir / "features.json").write_text(json.dumps({
        "feature_version": "1.0",
        "excerpt_policy": f"抜き出した最大 {MAX_SEGMENTS} セグメント(各 5 秒)の連結から算出",
        "items": [{"id": r["id"], **r["features"]} for r in ok],
    }, ensure_ascii=False), encoding="utf-8")

    (args.outdir / "waveforms.json").write_text(json.dumps({
        "buckets": WAVEFORM_BUCKETS,
        "items": [{"id": r["id"], "envelope": r["envelope"],
                   "duration_s": r["duration_s"]} for r in ok],
    }, ensure_ascii=False), encoding="utf-8")

    (args.outdir / "segments.json").write_text(json.dumps({
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "target_sr": TARGET_SR,
        "max_segments": MAX_SEGMENTS,
        "processed": len(ok),
        "failed": len(bad),
        "failures": [{"id": r["id"], "error": r["error"]} for r in bad],
        "items": [{k: r[k] for k in
                   ("id", "segments", "segments_available", "duration_s",
                    "sample_rate_original", "padded_segments", "excerpt_seconds")}
                  for r in ok],
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    total_segs = sum(r["segments"] for r in ok)
    print(f"\n処理 {len(ok)} 録音 / 失敗 {len(bad)} / セグメント {total_segs} "
          f"/ {time.time() - t0:.0f}s")
    for b in bad[:10]:
        print(f"  FAIL {b['id']}: {b['error'][:110]}")
    print(f"wrote {args.outdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
