"use client";

import { useState } from "react";

import type { DistanceModel } from "@/lib/types";

/**
 * 地理距離 × 音響距離(F-12 / 仕様書 §25)。
 *
 * 49,141 対を素の散布図にすると潰れて読めないので、地理距離で束ねて
 * **束ごとの平均**を線にする(四分位範囲を帯で添える)。
 *
 * 二本に分けるのが要点で、**同じ投稿者の対**と**違う投稿者の対**を並べる。
 * 「違う投稿者」の線が距離によらず平らなら、音響的な近さは地理を語っていない。
 *
 * 色は dataviz の検証済みスロット 1・2(青 / 橙)。
 * 手元のサイト色(緑 #2f6b5f)は彩度が floor を割って灰色に見え、
 * 色覚多様性での分離も 7.3 しか無かったので使わない(検証器の実測)。
 */
const SERIES = {
  same: { color: "#2a78d6", label: "同じ投稿者の対" },
  diff: { color: "#eb6834", label: "違う投稿者の対" },
} as const;

const W = 720;
const H = 240;
const PAD = { top: 14, right: 16, bottom: 44, left: 52 };

/** 軸に並べる短い表記。回さずに済ませるための省略形。 */
function shortLabel(lo: number, hi: number): string {
  if (lo === 0) return "同国";
  if (hi >= 20000) return `${Math.round(lo / 1000)}k+`;
  // 最初の帯は lo=1km(「同じ国」を切り出した残り)なので 0 と書く
  const a = lo < 1000 ? 0 : Math.round(lo / 1000);
  return `${a}–${Math.round(hi / 1000)}k`;
}

type Key = "same" | "diff";

export default function DistanceProfile({ model }: { model: DistanceModel }) {
  const [hover, setHover] = useState<{ band: number; key: Key } | null>(null);

  const bands = model.bands;
  const values: number[] = [];
  for (const b of bands) {
    for (const k of ["same", "diff"] as Key[]) {
      const s = b[k];
      if (s.mean != null) values.push(s.p25 ?? s.mean, s.p75 ?? s.mean, s.mean);
    }
  }
  if (values.length === 0) return null;

  const yMin = Math.min(...values);
  const yMax = Math.max(...values);
  const pad = (yMax - yMin) * 0.12 || 0.05;
  const lo = Math.max(0, yMin - pad);
  const hi = yMax + pad;

  const iw = W - PAD.left - PAD.right;
  const ih = H - PAD.top - PAD.bottom;
  const x = (i: number) => PAD.left + (iw * (i + 0.5)) / bands.length;
  const y = (v: number) => PAD.top + ih - ((v - lo) / (hi - lo)) * ih;

  /** null で切れる線分の集まりを返す(欠測をまたいで繋がない)。 */
  function segments(key: Key) {
    const out: { i: number; v: number }[][] = [];
    let cur: { i: number; v: number }[] = [];
    bands.forEach((b, i) => {
      const m = b[key].mean;
      if (m == null) {
        if (cur.length) out.push(cur);
        cur = [];
      } else cur.push({ i, v: m });
    });
    if (cur.length) out.push(cur);
    return out;
  }

  function areaPath(key: Key) {
    const segs = segments(key);
    return segs
      .map((seg) => {
        const up = seg.map((p) => `${x(p.i)},${y(bands[p.i][key].p75 ?? p.v)}`);
        const dn = [...seg]
          .reverse()
          .map((p) => `${x(p.i)},${y(bands[p.i][key].p25 ?? p.v)}`);
        return `M${up.join("L")}L${dn.join("L")}Z`;
      })
      .join(" ");
  }

  const ticks = 4;
  const hovered = hover ? bands[hover.band][hover.key] : null;

  return (
    <div className="dprof">
      <div className="scrollx">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="dprof__svg"
          role="img"
          aria-label={`${model.model_name}: 地理距離ごとの音響距離の平均`}
        >
          {/* 目盛(控えめに) */}
          {Array.from({ length: ticks + 1 }, (_, k) => {
            const v = lo + ((hi - lo) * k) / ticks;
            return (
              <g key={k}>
                <line
                  x1={PAD.left}
                  y1={y(v)}
                  x2={W - PAD.right}
                  y2={y(v)}
                  className="dprof__grid"
                />
                <text x={PAD.left - 7} y={y(v) + 3.5} className="dprof__ytick">
                  {v.toFixed(2)}
                </text>
              </g>
            );
          })}

          {(["diff", "same"] as Key[]).map((key) => (
            <path
              key={`a-${key}`}
              d={areaPath(key)}
              fill={SERIES[key].color}
              opacity={0.13}
            />
          ))}

          {(["diff", "same"] as Key[]).map((key) =>
            segments(key).map((seg, si) => (
              <polyline
                key={`l-${key}-${si}`}
                points={seg.map((p) => `${x(p.i)},${y(p.v)}`).join(" ")}
                fill="none"
                stroke={SERIES[key].color}
                strokeWidth={2}
                strokeLinejoin="round"
              />
            )),
          )}

          {(["diff", "same"] as Key[]).map((key) =>
            bands.map((b, i) =>
              b[key].mean == null ? null : (
                <circle
                  key={`p-${key}-${i}`}
                  cx={x(i)}
                  cy={y(b[key].mean as number)}
                  r={hover?.band === i && hover.key === key ? 6.5 : 4.5}
                  fill={SERIES[key].color}
                  stroke="#fffdf8"
                  strokeWidth={2}
                  onMouseEnter={() => setHover({ band: i, key })}
                  onMouseLeave={() => setHover(null)}
                  style={{ cursor: "pointer" }}
                >
                  <title>{`${b.label} / ${SERIES[key].label}: 平均 ${(b[key].mean as number).toFixed(3)}(${b[key].n} 対)`}</title>
                </circle>
              ),
            ),
          )}

          {/* x 軸のラベルは**回さない**。
              回すと (a) 端が図の外へ出て切れる (b) getBBox は変換前の箱を返すので
              検査が緑のまま通る —— 実際にこの図で切れを出した(2026-09-10)。
              短い表記にして水平のまま全部並べる。 */}
          {bands.map((b, i) => (
            <text
              key={`x-${i}`}
              x={x(i)}
              y={H - PAD.bottom + 15}
              className="dprof__xtick"
              textAnchor="middle"
            >
              {shortLabel(b.lo_km, b.hi_km)}
            </text>
          ))}
          <text
            x={PAD.left + iw / 2}
            y={H - 6}
            className="dprof__axislabel"
            textAnchor="middle"
          >
            二本の録音が地理的にどれだけ離れているか
          </text>
        </svg>
      </div>

      <p className="dprof__readout">
        {hovered && hover
          ? `${bands[hover.band].label} ・ ${SERIES[hover.key].label} — 音響距離の平均 ${(hovered.mean as number).toFixed(3)}(${hovered.n} 対)`
          : "点にふれると、その束の平均と対の数が出ます。"}
      </p>
    </div>
  );
}

export function DistanceLegend() {
  return (
    <div className="dprof__legend">
      {(Object.keys(SERIES) as Key[]).map((k) => (
        <span key={k} className="dprof__key">
          <i style={{ background: SERIES[k].color }} />
          {SERIES[k].label}
        </span>
      ))}
      <span className="dprof__key dprof__key--note">
        帯は四分位範囲(真ん中の半分がどこに散らばるか)
      </span>
    </div>
  );
}
