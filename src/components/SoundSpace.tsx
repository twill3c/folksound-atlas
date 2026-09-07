"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import type { ProjectionRow, Song } from "@/lib/types";

interface Props {
  points: ProjectionRow[];
  songs: Map<string, Song>;
  colorBy: "country" | "uploader";
  selectedId: string | null;
  onSelect: (id: string) => void;
  highlightIds?: Set<string>;
}

const W = 760;
const H = 520;
const PAD = 26;

/** 色は「どの国か」を当てるためではなく、**固まりが見えるか**を見るためのもの。 */
const PALETTE = [
  "#2f6b5f", "#9c4a2f", "#4a5e8c", "#8a6d1f", "#6b3f66",
  "#3f7a86", "#8c4a5e", "#5d7a3f", "#7a5c3a", "#44607a",
  "#a15a3a", "#3f6b4a", "#7c4f7a", "#6a6a2f", "#4e4a80",
];

function keyColor(key: string, keys: string[]) {
  const i = keys.indexOf(key);
  return i < 0 ? "#9a938a" : PALETTE[i % PALETTE.length];
}

export default function SoundSpace({
  points,
  songs,
  colorBy,
  selectedId,
  onSelect,
  highlightIds,
}: Props) {
  const [hover, setHover] = useState<string | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);

  const { scaled, keys } = useMemo(() => {
    if (points.length === 0) return { scaled: [], keys: [] as string[] };
    const xs = points.map((p) => p.x);
    const ys = points.map((p) => p.y);
    const x0 = Math.min(...xs);
    const x1 = Math.max(...xs);
    const y0 = Math.min(...ys);
    const y1 = Math.max(...ys);
    const sx = (v: number) =>
      PAD + ((v - x0) / Math.max(x1 - x0, 1e-9)) * (W - 2 * PAD);
    const sy = (v: number) =>
      H - PAD - ((v - y0) / Math.max(y1 - y0, 1e-9)) * (H - 2 * PAD);

    const counts = new Map<string, number>();
    for (const p of points) {
      const s = songs.get(p.id);
      if (!s) continue;
      const k = colorBy === "country" ? s.country : s.uploader ?? "(不明)";
      counts.set(k, (counts.get(k) ?? 0) + 1);
    }
    const topKeys = [...counts.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, PALETTE.length)
      .map(([k]) => k);

    return {
      scaled: points.map((p) => {
        const s = songs.get(p.id);
        const k = s
          ? colorBy === "country"
            ? s.country
            : s.uploader ?? "(不明)"
          : "(不明)";
        return { id: p.id, cx: sx(p.x), cy: sy(p.y), key: k, song: s };
      }),
      keys: topKeys,
    };
  }, [points, songs, colorBy]);

  useEffect(() => setHover(null), [colorBy]);

  const hoveredSong = hover ? songs.get(hover) : null;

  return (
    <div className="soundspace">
      <div className="scrollx">
        <svg
          ref={svgRef}
          viewBox={`0 0 ${W} ${H}`}
          className="soundspace__svg"
          role="img"
          aria-label="音響空間の散布図"
        >
          <rect x={0} y={0} width={W} height={H} className="soundspace__bg" />
          {scaled.map((p) => {
            const on = p.id === selectedId || p.id === hover;
            const dim =
              highlightIds && highlightIds.size > 0 && !highlightIds.has(p.id);
            return (
              <circle
                key={p.id}
                cx={p.cx}
                cy={p.cy}
                r={on ? 7 : 4.2}
                fill={keyColor(p.key, keys)}
                className={`soundspace__pt${on ? " is-on" : ""}${dim ? " is-dim" : ""}`}
                onMouseEnter={() => setHover(p.id)}
                onMouseLeave={() => setHover(null)}
                onClick={() => onSelect(p.id)}
              >
                <title>{`${p.song?.title ?? p.id}(${p.key})`}</title>
              </circle>
            );
          })}
        </svg>
      </div>

      <div className="soundspace__legend">
        {keys.map((k) => (
          <span key={k} className="soundspace__key">
            <i style={{ background: keyColor(k, keys) }} />
            {k}
          </span>
        ))}
        {keys.length > 0 && <span className="soundspace__key">
          <i style={{ background: "#9a938a" }} />その他
        </span>}
      </div>

      <p className="soundspace__hint">
        {hoveredSong
          ? `${hoveredSong.title} — ${hoveredSong.country}`
          : "点にふれると曲名が出ます。クリックで詳細へ。"}
      </p>
    </div>
  );
}
