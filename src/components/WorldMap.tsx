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

/** 等長方形図法。国の代表点を置くだけなので、これで十分かつ誤解が少ない。
 *
 * 緯度は [-58, 84] に切る。南極には録音が無く、全緯度を描くと画面の 3 割が
 * 空白になって、肝心の密集地帯が小さくなるため(実測 2026-09-08 の目視)。
 */
const LAT_MAX = 84;
const LAT_MIN = -58;

function project(lon: number, lat: number, w: number, h: number) {
  const x = ((lon + 180) / 360) * w;
  const y = ((LAT_MAX - lat) / (LAT_MAX - LAT_MIN)) * h;
  return [x, y] as const;
}

const W = 1000;
const H = 420;

export default function WorldMap({ songs, selectedId, onSelect, highlightIds }: Props) {
  const [world, setWorld] = useState<WorldFeature[] | null>(null);
  const [hover, setHover] = useState<string | null>(null);
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let alive = true;
    // 絶対パスで引く。`trailingSlash: true` なのでこの頁は `/map/` にあり、
    // 相対パス `./data/...` は `/map/data/...` になって 404 する
    // (実測 2026-09-08: 実ブラウザ検品で陸地が出ないことから見つけた)。
    fetch("/data/world.geojson")
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
    const out: { d: string; name: string | null }[] = [];
    for (const f of world) {
      let d = "";
      for (const poly of f.geometry.coordinates) {
        for (const ring of poly) {
          // 緯度を切った以上、**描くほうも切る**。切らないと南極が viewBox の
          // 下へはみ出し、図の外に線が残る(実測 2026-09-08: 実ブラウザ検品で
          // <path> が (0,428) から高さ 87 はみ出しているのを検出した)。
          if (ring.every(([, lat]) => lat < LAT_MIN)) continue;
          ring.forEach(([lon, lat], i) => {
            const [x, y0] = project(lon, lat, W, H);
            const y = Math.max(0, Math.min(H, y0));
            d += `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
          });
          d += "Z";
        }
      }
      if (d) out.push({ d, name: f.properties.name });
    }
    return out;
  }, [world]);

  const maxCount = Math.max(1, ...groups.map((g) => g.songs.length));
  const radius = (n: number) => 4 + 11 * Math.sqrt(n / maxCount);

  // ラベルの衝突回避。件数の多い順に置き、既に置いたものと当たったら捨てる。
  const labels = useMemo(() => {
    const placed: { x0: number; y0: number; x1: number; y1: number }[] = [];
    const out: { country: string; x: number; y: number }[] = [];
    const charW = 5.4; // 10px の欧文ラベルのおおよその字幅
    const lineH = 11;
    for (const g of groups.slice(0, 18)) {
      const [x, y] = project(g.lon, g.lat, W, H);
      const ty = y - radius(g.songs.length) - 4;
      const halfW = (g.country.length * charW) / 2;
      const box = { x0: x - halfW, y0: ty - lineH, x1: x + halfW, y1: ty };
      const hits = placed.some(
        (p) => !(box.x1 < p.x0 || box.x0 > p.x1 || box.y1 < p.y0 || box.y0 > p.y1),
      );
      if (hits) continue;
      placed.push(box);
      out.push({ country: g.country, x, y: ty });
    }
    return out;
  }, [groups, maxCount]);

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

          {/* ラベルは重なった時点で読めなくなるので、置けるものだけ置く。
              件数の多い順に見て、すでに置いたラベルと矩形が当たるものは捨てる。
              **全部出すより、読める数だけ出すほうがよい**(密集地帯は丸の title で読める)。 */}
          {labels.map((l) => (
            <text
              key={`t-${l.country}`}
              x={l.x}
              y={l.y}
              className="worldmap__label"
              textAnchor="middle"
            >
              {l.country}
            </text>
          ))}
        </svg>
      </div>

      <p className="worldmap__caption">
        丸の大きさは、その国から採れた録音の本数です。位置は
        <strong>国の代表点</strong>であって、録音された場所ではありません。
      </p>
    </div>
  );
}
