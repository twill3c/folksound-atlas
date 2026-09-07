"""preprocess.py — 音声の内部標準化とセグメント化(SPEC §7 / F-03 / 仕様書 §28–29)。

内部標準:
    WAV / mono / 22050 Hz / float32
    セグメント 5.0 秒、ホップ 2.5 秒

**原音は変更せず保存する。** ここで作るのは派生物である。
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np

TARGET_SR = 22050          # SPEC §7
SEGMENT_SECONDS = 5.0      # SPEC §7
HOP_SECONDS = 2.5          # SPEC §7


def to_mono(x: np.ndarray) -> np.ndarray:
    """多チャンネルを平均して 1 次元 float32 にする。

    soundfile は (samples, channels)、torchaudio は (channels, samples) を返す。
    ここは **(channels, samples) を前提**とし、呼び出し側で向きを揃える。
    """
    a = np.asarray(x)
    if a.ndim == 1:
        return a.astype(np.float32, copy=False)
    if a.ndim != 2:
        raise ValueError(f"想定外の次元数: {a.ndim}")
    return a.astype(np.float32).mean(axis=0)


def peak_normalize(x: np.ndarray, target_peak: float = 0.95) -> np.ndarray:
    """ピークを揃える。無音はそのまま返す(0 除算を作らない)。"""
    a = np.asarray(x, dtype=np.float32)
    peak = float(np.max(np.abs(a))) if a.size else 0.0
    if peak <= 1e-9:
        return a
    return (a * (target_peak / peak)).astype(np.float32)


def segment_signal(
    x: np.ndarray,
    sr: int,
    segment_seconds: float = SEGMENT_SECONDS,
    hop_seconds: float = HOP_SECONDS,
) -> list[dict]:
    """固定長セグメントへ切る。

    5 秒に満たない録音は**捨てずに**ゼロ詰めして 1 セグメントにする。
    短いものを落とすと、短い録音しか無い国が丸ごと消え、地理の偏りが増えるためである。
    ゼロ詰めしたことは `padded` に残す(後段が区別できるように)。
    """
    a = np.asarray(x, dtype=np.float32)
    n = a.size
    if n == 0:
        return []

    want = int(round(segment_seconds * sr))
    step = int(round(hop_seconds * sr))

    if n < want:
        buf = np.zeros(want, dtype=np.float32)
        buf[:n] = a
        return [{"index": 0, "start_sample": 0, "samples": buf, "padded": True}]

    out: list[dict] = []
    idx = 0
    start = 0
    while start + want <= n:
        out.append(
            {
                "index": idx,
                "start_sample": start,
                "samples": a[start : start + want],
                "padded": False,
            }
        )
        idx += 1
        start += step
    return out


def sha256_of(path: str | Path, chunk: int = 1 << 20) -> str:
    """音源の重複検出に使う(仕様書 §82)。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def load_and_standardize(path: str | Path) -> tuple[np.ndarray, int]:
    """音源を読み、mono / TARGET_SR / float32 へ揃えて返す。

    戻り値は `(signal, original_sample_rate)`。
    """
    import librosa
    import soundfile as sf

    with sf.SoundFile(str(path)) as f:
        original_sr = f.samplerate

    # librosa.load は mono 化と再標本化をまとめて行う。
    # 既定の `soxr_hq` は 300 件規模だと律速になるので `soxr_mq` を使う
    # (実測 2026-09-08: 1 件あたり 8 秒前後 → 2 秒前後)。
    # 22050Hz へ落とす用途では可聴帯域の差は問題にならない。
    y, _ = librosa.load(str(path), sr=TARGET_SR, mono=True, res_type="soxr_mq")
    return peak_normalize(np.asarray(y, dtype=np.float32)), original_sr


def sample_segments(segments: list[dict], max_count: int) -> list[dict]:
    """セグメントを **録音全体から等間隔で** 選ぶ。

    先頭から N 件取ると、長い録音では最初の 30 秒しか見ないことになる。
    組曲・語り物のように後半で様子が変わるものを取りこぼすので、
    全体に散らして取る。順序と `index` は元のまま残す。
    """
    if max_count <= 0 or len(segments) <= max_count:
        return segments
    idx = np.linspace(0, len(segments) - 1, max_count)
    picked = sorted({int(round(i)) for i in idx})
    return [segments[i] for i in picked]
