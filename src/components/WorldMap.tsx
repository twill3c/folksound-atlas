"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import type { Song } from "@/lib/types";

interface Props {
  songs: Song[];
  selectedId: string | null;
  onSelect: (id: string | null) => void;
  highlightIds?: Set<string>;
}

interface WorldFeature {
  properties: { name: string | null; iso_a3: string | null };
  geometry: { type: "MultiPolygon"; coordinates: number[][][][] };
}

/** 等長方形図法。国の代表点を置くだけなので、これで十分かつ誤解が少ない。 */
function project(lon: number, lat: number, w: number, h: number) {
  return [((lon + 180) / 360) * w, ((90 - lat) / 180) * h] as const;
}

const W = 1000;
const H = 500;

export default function WorldMap({ songs, selectedId, onSelect, highlightIds }: Props) {
  const [world, setWorld] = useState<WorldFeature[] | null>(null);
  const [hover, setHover] = useState<string | null>(null);
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let alive = true;
    fetch("./data/world.geojson")
      .then((r) => (r.ok ? r.json() : null))
      .then((d) => {
        if (alive && d) setWorld(d.features as WorldFeature[]);
      })
      .catch(() => {
        /* 下地が無くても点は出す */
      });
    return () => {
      alive = false;
    };
  }, []);

  // 国ごとにまとめる。1 国に何本あるかを丸の大きさで示す。
  const groups = useMemo(() => {
    const m = new Map<
      string,
      { country: string; lat: number; lon: number; songs: Song[] }
    >();
    for (const s of songs) {
      if (s.latitude == null || s.longitude == null) continue;
      const g = m.get(s.country);
      if (g) g.songs.push(s);
      else
        m.set(s.country, {
          country: s.country,
          lat: s.latitude,
          lon: s.longitude,
          songs: [s],
        });
    }
    return [...m.values()].sort((a, b) => b.songs.length - a.songs.length);
  }, [songs]);

  const paths = useMemo(() => {
    if (!world) return [];
    return world.map((f) => {
      let d = "";
      for (const poly of f.geometry.coordinates) {
        for (const ring of poly) {
          ring.forEach(([lon, lat], i) => {
            const [x, y] = project(lon, lat, W, H);
            d += `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
          });
          d += "Z";
        }
      }
      return { d, name: f.properties.name };
    });
  }, [world]);

  const maxCount = Math.max(1, ...groups.map((g) => g.songs.length));
  const radius = (n: number) => 4 + 11 * Math.sqrt(n / maxCount);

  const selectedCountry = selectedId
    ? songs.find((s) => s.id === selectedId)?.country ?? null
    : null;

  return (
    <div ref={wrapRef} className="worldmap">
      <div className="scrollx">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="worldmap__svg"
          role="img"
          aria-label="録音の採られた国の分布"
        >
          <rect x={0} y={0} width={W} height={H} className="worldmap__sea" />
          {paths.map((p, i) => (
            <path key={i} d={p.d} className="worldmap__land" />
          ))}

          {groups.map((g) => {
            const [x, y] = project(g.lon, g.lat, W, H);
            const on = selectedCountry === g.country || hover === g.country;
            const dim =
              highlightIds && highlightIds.size > 0
                ? !g.songs.some((s) => highlightIds.has(s.id))
                : false;
            return (
              <g
                key={g.country}
                className={`worldmap__pin${on ? " is-on" : ""}${dim ? " is-dim" : ""}`}
                onMouseEnter={() => setHover(g.country)}
                onMouseLeave={() => setHover(null)}
                onClick={() => onSelect(g.songs[0].id)}
              >
                <circle cx={x} cy={y} r={radius(g.songs.length)} />
                <title>{`${g.country} — ${g.songs.length} 件`}</title>
              </g>
            );
          })}

          {groups.slice(0, 12).map((g) => {
            const [x, y] = project(g.lon, g.lat, W, H);
            return (
              <text
                key={`t-${g.country}`}
                x={x}
                y={y - radius(g.songs.length) - 4}
                className="worldmap__label"
                textAnchor="middle"
              >
                {g.country}
              </text>
            );
          })}
        </svg>
      </div>

      <p className="worldmap__caption">
        丸の大きさは、その国から採れた録音の本数です。位置は
        <strong>国の代表点</strong>であって、録音された場所ではありません。
      </p>
    </div>
  );
}
