"use client";

import Link from "next/link";
import { useMemo, useState } from "react";

import WorldMap from "@/components/WorldMap";
import type { Song } from "@/lib/types";

export default function MapExplorer({ songs }: { songs: Song[] }) {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [country, setCountry] = useState<string | null>(null);

  const byCountry = useMemo(() => {
    const m = new Map<string, Song[]>();
    for (const s of songs) {
      const a = m.get(s.country);
      if (a) a.push(s);
      else m.set(s.country, [s]);
    }
    return [...m.entries()].sort(
      (a, b) => b[1].length - a[1].length || a[0].localeCompare(b[0]),
    );
  }, [songs]);

  const selected = selectedId ? songs.find((s) => s.id === selectedId) ?? null : null;
  const shown = country ? byCountry.find(([c]) => c === country)?.[1] ?? [] : [];

  const highlight = useMemo(
    () => (country ? new Set(shown.map((s) => s.id)) : undefined),
    [country, shown],
  );

  return (
    <>
      <WorldMap
        songs={songs}
        selectedId={selectedId}
        onSelect={(id) => {
          setSelectedId(id);
          const s = songs.find((x) => x.id === id);
          if (s) setCountry(s.country);
        }}
        highlightIds={highlight}
      />

      <div className="mapx">
        <div className="mapx__col">
          <h2 className="mapx__h">国({byCountry.length})</h2>
          <ul className="mapx__countries">
            {byCountry.map(([c, list]) => (
              <li key={c}>
                <button
                  type="button"
                  className={c === country ? "is-on" : ""}
                  onClick={() => {
                    setCountry(c === country ? null : c);
                    setSelectedId(null);
                  }}
                >
                  <span>{c}</span>
                  <span className="num">{list.length}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>

        <div className="mapx__col mapx__col--wide">
          <h2 className="mapx__h">
            {country ? `${country} の録音(${shown.length})` : "国を選ぶと一覧が出ます"}
          </h2>
          {country && (
            <ul className="mapx__songs">
              {shown.map((s) => (
                <li key={s.id}>
                  <Link
                    href={`/song/${s.id}/`}
                    className={s.id === selectedId ? "is-on" : ""}
                    onMouseEnter={() => setSelectedId(s.id)}
                  >
                    {s.title}
                  </Link>
                  <span className="mapx__meta">
                    {s.duration_s != null ? `${Math.round(s.duration_s)} 秒` : ""}
                    {s.license ? ` ・ ${s.license}` : ""}
                  </span>
                </li>
              ))}
            </ul>
          )}
          {selected && (
            <p className="note" style={{ marginTop: 16 }}>
              「{selected.country}」という札は{" "}
              <code>{selected.country_source_category}</code> から来ています。
              曲の出自を表すもので、演奏者や録音地を表すものではありません。
            </p>
          )}
        </div>
      </div>
    </>
  );
}
