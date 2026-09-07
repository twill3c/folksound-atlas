"use client";

const W = 900;
const H = 110;

export default function Waveform({
  envelope,
  durationS,
}: {
  envelope: number[];
  durationS: number;
}) {
  if (!envelope || envelope.length === 0) {
    return <p className="note">波形のデータがありません。</p>;
  }
  const n = envelope.length;
  const step = W / n;
  const mid = H / 2;
  const peak = Math.max(...envelope, 1e-6);

  // 上下対称の帯として描く。振幅は最大値で正規化してあるので、
  // **高さの絶対値に意味は無い**(音量の比較には使えない)。
  let d = "";
  for (let i = 0; i < n; i++) {
    const h = (envelope[i] / peak) * (mid - 4);
    d += `M${(i * step).toFixed(2)},${(mid - h).toFixed(2)}L${(i * step).toFixed(2)},${(mid + h).toFixed(2)}`;
  }

  const ticks = 6;
  return (
    <div className="scrollx">
      <svg
        viewBox={`0 0 ${W} ${H + 18}`}
        className="wave"
        role="img"
        aria-label="波形の包絡線"
      >
        <rect x={0} y={0} width={W} height={H} className="wave__bg" />
        <path d={d} className="wave__line" />
        <line x1={0} y1={mid} x2={W} y2={mid} className="wave__axis" />
        {Array.from({ length: ticks + 1 }, (_, i) => {
          const x = (i / ticks) * W;
          const t = (i / ticks) * durationS;
          return (
            <g key={i}>
              <line x1={x} y1={H} x2={x} y2={H + 4} className="wave__axis" />
              <text
                x={Math.min(Math.max(x, 14), W - 14)}
                y={H + 15}
                textAnchor="middle"
                className="wave__tick"
              >
                {t >= 60
                  ? `${Math.floor(t / 60)}:${String(Math.round(t % 60)).padStart(2, "0")}`
                  : `${t.toFixed(0)}秒`}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
