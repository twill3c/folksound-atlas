"""features.py — 従来型音響特徴量(SPEC §7 / F-04 / 仕様書 §32)。

「人間が解釈できる」側の特徴量をここに集める。深層学習 Embedding とは別系統であり、
**国ラベルを一切見ない**ので、地理の主張に使ってよい(SPEC §8 の `feat-baseline-v1`)。

無音・定数・極端に短い断片は実データに必ず混じる。これらは異常ではなく正常系なので、
非有限値(NaN / inf)を出さないことを実装側の責務とする(HC-002 の型)。
"""

from __future__ import annotations

import numpy as np

# SPEC §7 の内部標準
N_FFT = 2048
HOP_LENGTH = 512
N_MELS = 128
FMIN = 20
FMAX = 8000
N_MFCC = 40

_EPS = 1e-10


def rms(x: np.ndarray) -> float:
    """実効値。正弦波(整数周期)なら A/√2 に一致する。"""
    if x.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(np.square(x.astype(np.float64)))))


def zero_crossing_rate(x: np.ndarray) -> float:
    """ゼロ交差率(1 サンプルあたり)。

    定数信号(全ゼロを含む)では交差が起きないので 0.0 を返す。
    `np.sign` は 0 に対して 0 を返すため、素朴に符号差を数えると
    ゼロを跨がずに触れただけの点を二重に数える。ここでは符号を
    「非負を +1」に丸めてから隣接差を見る。
    """
    if x.size < 2:
        return 0.0
    s = np.where(x.astype(np.float64) >= 0.0, 1.0, -1.0)
    crossings = np.count_nonzero(np.diff(s))
    return float(crossings) / float(x.size)


def spectral_centroid(x: np.ndarray, sr: int) -> float:
    """スペクトル重心(Hz)。

    全ゼロ入力では分母が 0 になるので、その場合は 0.0 を返す(非有限を出さない)。
    """
    if x.size == 0:
        return 0.0
    n = int(min(len(x), N_FFT * 8))
    seg = x[:n].astype(np.float64)
    win = np.hanning(len(seg)) if len(seg) > 1 else np.ones(1)
    spec = np.abs(np.fft.rfft(seg * win))
    freqs = np.fft.rfftfreq(len(seg), d=1.0 / sr)
    total = float(spec.sum())
    if total <= _EPS:
        return 0.0
    return float((freqs * spec).sum() / total)


def _safe(v: float) -> float:
    return float(v) if np.isfinite(v) else 0.0


def _tempo_fn():
    """librosa のテンポ推定関数を**明示的に**取りに行く。

    librosa は版によって置き場所が変わる:
        1.0 系   `librosa.feature.tempo`
        0.10 系  `librosa.feature.rhythm.tempo`

    ここを `try/except` で握りつぶすと、**関数が見つからないという実装の誤りが、
    「テンポ 0.0」という もっともらしいデータに化ける。**
    実際にこのプロジェクトで、0.10 系のパスを書いたまま librosa 1.0 で走らせ、
    314 件すべてが tempo=0.0 のまま出荷されかけた(2026-09-08)。
    どちらのパスも無いのは**版の問題(コードの誤り)**なので、その場で落とす。

    さらに `lazy_loader` のせいで、先に別の属性へ触れたあとだと
    `librosa.feature.rhythm` が解決できてしまうことがある。
    切り分けを誤らせるので、**触る順に依存しない形で**両方を試す。
    """
    import librosa

    for getter in (
        lambda: librosa.feature.tempo,          # librosa 1.0 系
        lambda: librosa.feature.rhythm.tempo,   # librosa 0.10 系
    ):
        try:
            fn = getter()
        except AttributeError:
            continue
        if callable(fn):
            return fn
    raise AttributeError(
        "librosa にテンポ推定関数が見つからない"
        "(librosa.feature.tempo / librosa.feature.rhythm.tempo のどちらも無い)。"
        "librosa の版を確かめること"
    )


def extract_features(x: np.ndarray, sr: int) -> dict:
    """SPEC §7 / schemas に対応する特徴量の辞書を返す。

    librosa をここでだけ使う。呼び出し側は librosa を知らなくてよい。
    """
    import librosa

    x = np.asarray(x, dtype=np.float32)
    if x.size == 0:
        x = np.zeros(sr, dtype=np.float32)

    S = np.abs(librosa.stft(x, n_fft=N_FFT, hop_length=HOP_LENGTH))
    silent = float(S.sum()) <= _EPS

    def mean_of(fn, *a, **kw) -> float:
        try:
            v = fn(*a, **kw)
            return _safe(np.nanmean(v))
        except Exception:
            return 0.0

    centroid = 0.0 if silent else mean_of(
        librosa.feature.spectral_centroid, S=S, sr=sr)
    bandwidth = 0.0 if silent else mean_of(
        librosa.feature.spectral_bandwidth, S=S, sr=sr)
    rolloff = 0.0 if silent else mean_of(
        librosa.feature.spectral_rolloff, S=S, sr=sr)

    if silent:
        contrast = [0.0] * 7
    else:
        try:
            c = librosa.feature.spectral_contrast(S=S, sr=sr)
            contrast = [_safe(v) for v in np.nanmean(c, axis=1)]
        except Exception:
            contrast = [0.0] * 7

    try:
        mel = librosa.feature.melspectrogram(
            S=S**2, sr=sr, n_mels=N_MELS, fmin=FMIN, fmax=FMAX)
        mfcc_m = librosa.feature.mfcc(
            S=librosa.power_to_db(mel), n_mfcc=N_MFCC)
        mfcc = [_safe(v) for v in np.nanmean(mfcc_m, axis=1)]
    except Exception:
        mfcc = [0.0] * N_MFCC
    if len(mfcc) != N_MFCC:
        mfcc = (mfcc + [0.0] * N_MFCC)[:N_MFCC]

    if silent:
        chroma = [0.0] * 12
    else:
        try:
            ch = librosa.feature.chroma_stft(S=S, sr=sr)
            chroma = [_safe(v) for v in np.nanmean(ch, axis=1)]
        except Exception:
            chroma = [0.0] * 12
    if len(chroma) != 12:
        chroma = (chroma + [0.0] * 12)[:12]

    if silent:
        # 無音にテンポは無い。これは異常ではなく正常系なので 0.0 でよい。
        tempo = 0.0
    else:
        # **関数が無い場合は落とす**(_tempo_fn が送出する)。
        # 音そのものが理由で推定できない場合だけ 0.0 に落とす。
        fn = _tempo_fn()
        try:
            t = fn(y=x, sr=sr)
            tempo = _safe(np.atleast_1d(t)[0])
        except Exception:
            tempo = 0.0

    return {
        "rms": _safe(rms(x)),
        "zcr": _safe(zero_crossing_rate(x)),
        "spectral_centroid": centroid,
        "spectral_bandwidth": bandwidth,
        "spectral_rolloff": rolloff,
        "spectral_contrast": contrast,
        "mfcc": mfcc,
        "chroma": chroma,
        "tempo": tempo,
    }
