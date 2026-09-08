"""13_spectrograms.py — 曲ごとのスペクトログラム画像を作る(F-10 / 仕様書 §64 / §107 / §114)。

仕様書 §114 の方針どおり **事前生成して画像で配る**。ブラウザで毎回 WAV を解析させない。

**どの区間を描いているかを決めて、画面にもそう書く。**
録音全体を 1 枚に潰すと縦線の壁になって何も読めないので、
**連続した 30 秒**を切り出して描く。開始位置は録音の 10% 地点とする
(頭出しの無音やアナウンスを避けるため)。30 秒に満たない録音は全体を使う。

解析(CNN・特徴量)が見ているのは全体から等間隔に抜いた 12 断片であって、
この 30 秒とは**一致しない**。絵は「この録音がどんな音か」を掴むためのもので、
解析の入力そのものではない —— この区別も画面に書く(HC-068: 表示用の加工値を
検査の根拠にしない、の裏返しで、表示は表示だと明示する)。

出力: public/spectrogram/<id>.webp と public/data/spectrograms.json
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
from folksound.features import HOP_LENGTH, N_FFT, N_MELS  # noqa: E402
from folksound.preprocess import TARGET_SR, peak_normalize  # noqa: E402

WINDOW_SECONDS = 30.0
START_FRACTION = 0.10
MAX_COLUMNS = 480          # 時間方向の解像度(これ以上は人の目に効かない)
FMIN, FMAX = 20, 8000

# 濃淡に割り当てる dB の範囲。
# **実測して決めた**(2026-09-08、本コーパスから 6 録音を走査):
#   dB のパーセンタイル(1,5,25,50,75,95,99) = -74.1 -69.7 -58.0 -49.0 -39.1 -25.0 -15.6
# 最初は [-80, 0] に割り当てていたが、上 16dB と下 6dB が空で、
# 中身が 0.13〜0.80 に圧縮されて**眠い絵**になった(目視で気づいた)。
# 実測の p1〜p99 に合わせて張り直す。
DB_FLOOR, DB_CEIL = -72.0, -14.0

# 紙面の色に寄せた配色。暗い=静か、濃い橙=強い。
# **色は強さの順序だけを表す。** 周波数や国とは無関係である。
PALETTE_STOPS = [
    (0.00, (245, 241, 232)),
    (0.35, (216, 207, 190)),
    (0.65, (196, 138, 108)),
    (0.85, (156, 74, 47)),
    (1.00, (74, 30, 18)),
]


def build_lut() -> np.ndarray:
    lut = np.zeros((256, 3), dtype=np.uint8)
    xs = np.linspace(0.0, 1.0, 256)
    stops = PALETTE_STOPS
    for i, x in enumerate(xs):
        for j in range(len(stops) - 1):
            x0, c0 = stops[j]
            x1, c1 = stops[j + 1]
            if x0 <= x <= x1:
                t = 0.0 if x1 == x0 else (x - x0) / (x1 - x0)
                lut[i] = [int(round(c0[k] + t * (c1[k] - c0[k]))) for k in range(3)]
                break
    return lut


def load_window(path: Path) -> tuple[np.ndarray, float, float]:
    """連続した窓を切り出す。戻り値は (信号, 開始秒, 長さ秒)。"""
    import soundfile as sf
    import soxr

    data, sr = sf.read(str(path), dtype="float32", always_2d=True)
    mono = data.mean(axis=1) if data.shape[1] > 1 else data[:, 0]
    if sr != TARGET_SR:
        mono = soxr.resample(mono, sr, TARGET_SR, quality="MQ")
    y = peak_normalize(np.asarray(mono, dtype=np.float32))

    total = y.size / TARGET_SR
    if total <= WINDOW_SECONDS:
        return y, 0.0, total
    start = min(total * START_FRACTION, max(total - WINDOW_SECONDS, 0.0))
    a = int(start * TARGET_SR)
    b = a + int(WINDOW_SECONDS * TARGET_SR)
    return y[a:b], start, WINDOW_SECONDS


def render(rid: str, rel: str, root_str: str, outdir_str: str) -> dict:
    """**プロセスプールから呼ばれるので例外を外へ投げない。**"""
    try:
        import librosa
        from PIL import Image

        root = Path(root_str)
        y, start, dur = load_window(root / rel)
        if y.size < N_FFT:
            return {"id": rid, "ok": False, "error": "too short"}

        mel = librosa.feature.melspectrogram(
            y=y, sr=TARGET_SR, n_fft=N_FFT, hop_length=HOP_LENGTH,
            n_mels=N_MELS, fmin=FMIN, fmax=FMAX,
        )
        db = librosa.power_to_db(mel, ref=np.max)
        db = np.clip(db, DB_FLOOR, DB_CEIL)

        # 時間方向を間引く(最大値を取る。平均だと立ち上がりが消える)
        t = db.shape[1]
        if t > MAX_COLUMNS:
            edges = np.linspace(0, t, MAX_COLUMNS + 1).astype(int)
            db = np.stack([db[:, edges[i]:edges[i + 1]].max(axis=1)
                           for i in range(MAX_COLUMNS)], axis=1)

        norm = (db - DB_FLOOR) / (DB_CEIL - DB_FLOOR)       # 0..1
        idx = np.clip((norm * 255.0).round(), 0, 255).astype(np.uint8)
        idx = np.flipud(idx)                                # 低音を下に
        rgb = build_lut()[idx]

        outdir = Path(outdir_str)
        outdir.mkdir(parents=True, exist_ok=True)
        Image.fromarray(rgb, mode="RGB").save(
            outdir / f"{rid}.webp", format="WEBP", quality=72, method=4)

        return {
            "id": rid, "ok": True,
            "start_s": round(float(start), 2),
            "duration_s": round(float(dur), 2),
            "width": int(rgb.shape[1]), "height": int(rgb.shape[0]),
        }
    except Exception as e:  # noqa: BLE001
        return {"id": rid, "ok": False, "error": repr(e)}


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    ap = argparse.ArgumentParser()
    ap.add_argument("--selected", type=Path, default=root / "data" / "raw" / "selected.json")
    ap.add_argument("--features", type=Path, default=root / "data" / "features" / "features.json")
    ap.add_argument("--outdir", type=Path, default=root / "public" / "spectrogram")
    ap.add_argument("--manifest", type=Path,
                    default=root / "public" / "data" / "spectrograms.json")
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 4) - 2))
    args = ap.parse_args()

    ok_ids = {f["id"] for f in json.loads(args.features.read_text(encoding="utf-8"))["items"]}
    recs = [r for r in json.loads(args.selected.read_text(encoding="utf-8"))["records"]
            if r["id"] in ok_ids]
    print(f"{len(recs)} 録音 / ワーカ {args.workers}", flush=True)

    results: list[dict] = []
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(render, r["id"], r["path"], str(root), str(args.outdir))
                for r in recs]
        for i, fut in enumerate(as_completed(futs), 1):
            results.append(fut.result())
            if i % 50 == 0 or i == len(futs):
                el = time.time() - t0
                print(f"  {i}/{len(futs)}  {el:.0f}s", flush=True)

    ok = sorted((r for r in results if r["ok"]), key=lambda r: r["id"])
    bad = [r for r in results if not r["ok"]]

    args.manifest.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.write_text(json.dumps({
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "window_seconds": WINDOW_SECONDS,
        "start_fraction": START_FRACTION,
        "n_mels": N_MELS,
        "fmin": FMIN,
        "fmax": FMAX,
        "note": "連続した 30 秒(録音の 10% 地点から)。解析が見ている 12 断片とは一致しない",
        "failed": [{"id": r["id"], "error": r["error"]} for r in bad],
        "items": [{k: r[k] for k in ("id", "start_s", "duration_s", "width", "height")}
                  for r in ok],
    }, ensure_ascii=False), encoding="utf-8")

    total = sum((args.outdir / f"{r['id']}.webp").stat().st_size for r in ok)
    print(f"\n{len(ok)} 枚 / 失敗 {len(bad)} / 合計 {total / 1e6:.2f} MB "
          f"(平均 {total / max(len(ok), 1) / 1e3:.1f} KB) / {time.time() - t0:.0f}s")
    for b in bad[:5]:
        print(f"  FAIL {b['id']}: {b['error'][:100]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
