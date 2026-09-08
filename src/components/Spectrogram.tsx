import type { SpectrogramRow } from "@/lib/types";

/**
 * スペクトログラム(仕様書 §64 / §107)。
 * 画像は Python 側で事前生成してある(仕様書 §114)。ブラウザでは解析しない。
 *
 * **どの区間の絵かを必ず添える。** 録音全体ではなく連続した一続きなので、
 * それを書かないと「この曲はこう」と読まれてしまう。
 */
export default function Spectrogram({
  id,
  meta,
  fmin,
  fmax,
}: {
  id: string;
  meta: SpectrogramRow | null;
  fmin: number;
  fmax: number;
}) {
  if (!meta) return <p className="note">スペクトログラムがありません。</p>;

  const end = meta.start_s + meta.duration_s;
  const fmt = (s: number) =>
    s >= 60
      ? `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")}`
      : `${s.toFixed(0)}秒`;

  return (
    <figure className="spec">
      <div className="spec__frame">
        <div className="spec__yaxis" aria-hidden="true">
          <span>{(fmax / 1000).toFixed(0)}k</span>
          <span>{(fmax / 2000).toFixed(0)}k</span>
          <span>{fmin}Hz</span>
        </div>
        <img
          className="spec__img"
          src={`/spectrogram/${id}.webp`}
          width={meta.width}
          height={meta.height}
          loading="lazy"
          decoding="async"
          alt={`この録音の ${fmt(meta.start_s)} から ${fmt(end)} までの周波数の濃淡`}
        />
      </div>
      <div className="spec__xaxis" aria-hidden="true">
        <span>{fmt(meta.start_s)}</span>
        <span>{fmt(end)}</span>
      </div>
      <figcaption className="note">
        縦は周波数({fmin}Hz〜{(fmax / 1000).toFixed(0)}kHz・メル尺度)、
        横は時間、色の濃さは強さです。描いているのは
        <strong>
          {fmt(meta.start_s)} から {fmt(end)} までの連続した {meta.duration_s.toFixed(0)} 秒
        </strong>
        で、録音全体ではありません。
        <strong>
          深層学習と特徴量が見ているのは、全体から等間隔に抜いた 12 個の 5 秒断片
        </strong>
        なので、この絵とは一致しません。音の様子を掴むための図です。
      </figcaption>
    </figure>
  );
}
