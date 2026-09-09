"use client";

import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import type { ModelInfo, NetworkFile } from "@/lib/types";

/**
 * 音響的近さのネットワーク(仕様書 §69)。
 *
 * 配置は手元で計算済み(種固定)。ここでは描くだけで、力学計算はしない。
 *
 * 色は dataviz の検証済みスロットを**固定順**で 6 つまで。
 * 7 番目以降は色を作らず「その他」へ畳む(色を増やして回さない)。
 * 3 色は紙面に対するコントラストが 3:1 を割る warn だったので、
 * **凡例・ホバーの名前・件数表**という文字の裏づけを必ず添える。
 */
const SLOTS = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#4a3aa7"];
const OTHER = "#9a938a";

const W = 760;
const H = 560;
const PAD = 18;

export default function NetworkView({ models }: { models: ModelInfo[] }) {
  const router = useRouter();
  const [modelId, setModelId] = useState(models[0]?.model_id ?? "");
  const [colorBy, setColorBy] = useState<"country" | "uploader">("country");
  const [hover, setHover] = useState<string | null>(null);
  const [net, setNet] = useState<NetworkFile | null>(null);
  const [err, setErr] = useState<string | null>(null);

  // **必要になったものだけ取りに行く**(N-03)。
  // 4 モデルぶんを頁に埋めると 281KB になるが、読むのは一度に 1 つだけ。
  useEffect(() => {
    if (!modelId) return;
    let alive = true;
    setNet(null);
    setErr(null);
    fetch(`/data/network_${modelId}.json`)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(String(r.status)))))
      .then((d) => alive && setNet(d as NetworkFile))
      .catch((e) => alive && setErr(String(e)));
    return () => {
      alive = false;
    };
  }, [modelId]);

  const { pos, keys, colorOf, counts } = useMemo(() => {
    if (!net) {
      return {
        pos: new Map<string, { x: number; y: number }>(),
        keys: [] as string[],
        colorOf: () => OTHER,
        counts: [] as [string, number][],
      };
    }
    const pos = new Map(
      net.nodes.map((n) => [
        n.id,
        {
          x: PAD + n.x * (W - 2 * PAD),
          y: PAD + n.y * (H - 2 * PAD),
        },
      ]),
    );
    const c = new Map<string, number>();
    for (const n of net.nodes) {
      const k = colorBy === "country" ? n.country : n.uploader;
      c.set(k, (c.get(k) ?? 0) + 1);
    }
    const ranked = [...c.entries()].sort((a, b) => b[1] - a[1]);
    const keys = ranked.slice(0, SLOTS.length).map(([k]) => k);
    const colorOf = (k: string) => {
      const i = keys.indexOf(k);
      return i < 0 ? OTHER : SLOTS[i];
    };
    return { pos, keys, colorOf, counts: ranked };
  }, [net, colorBy]);

  const byId = useMemo(
    () => new Map((net?.nodes ?? []).map((n) => [n.id, n])),
    [net],
  );
  const hoveredNode = hover ? byId.get(hover) : null;

  return (
    <>
      <div className="controls">
        <div className="controls__group">
          <span className="controls__label">モデル</span>
          {models.map((m) => (
            <button
              key={m.model_id}
              type="button"
              className={m.model_id === modelId ? "is-on" : ""}
              onClick={() => setModelId(m.model_id)}
            >
              {m.name}
              <span
                className={`tag ${m.saw_country_labels ? "tag--saw" : "tag--blind"}`}
                style={{ marginLeft: 6 }}
              >
                {m.saw_country_labels ? "ラベルを見た" : "見ていない"}
              </span>
            </button>
          ))}
        </div>

        <div className="controls__group">
          <span className="controls__label">色分け</span>
          <button
            type="button"
            className={colorBy === "country" ? "is-on" : ""}
            onClick={() => setColorBy("country")}
          >
            国
          </button>
          <button
            type="button"
            className={colorBy === "uploader" ? "is-on" : ""}
            onClick={() => setColorBy("uploader")}
          >
            投稿者(どのアーカイブか)
          </button>
        </div>
      </div>

      {err && <p className="note">ネットワークを読み込めませんでした({err})。</p>}
      {!net && !err && <p className="note">読み込み中…</p>}

      {net && (
        <>
      <div className="scrollx">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          className="netview__svg"
          role="img"
          aria-label={`${net.model_name} の音響的近さのネットワーク`}
        >
          <rect x={0} y={0} width={W} height={H} className="netview__bg" />

          {net.edges.map((e, i) => {
            const a = pos.get(e.a);
            const b = pos.get(e.b);
            if (!a || !b) return null;
            const on = hover === e.a || hover === e.b;
            return (
              <line
                key={i}
                x1={a.x}
                y1={a.y}
                x2={b.x}
                y2={b.y}
                className={`netview__edge${on ? " is-on" : ""}`}
              />
            );
          })}

          {net.nodes.map((n) => {
            const p = pos.get(n.id)!;
            const k = colorBy === "country" ? n.country : n.uploader;
            const on = hover === n.id;
            return (
              <circle
                key={n.id}
                cx={p.x}
                cy={p.y}
                r={n.deg === 0 ? 3 : on ? 7 : 4.6}
                fill={colorOf(k)}
                className={`netview__node${n.deg === 0 ? " is-isolated" : ""}${on ? " is-on" : ""}`}
                onMouseEnter={() => setHover(n.id)}
                onMouseLeave={() => setHover(null)}
                onClick={() => router.push(`/song/${n.id}/`)}
              >
                <title>{`${n.title}(${n.country} / ${n.uploader})— 辺 ${n.deg} 本`}</title>
              </circle>
            );
          })}
        </svg>
      </div>

      <p className="netview__readout">
        {hoveredNode
          ? `${hoveredNode.title} — ${hoveredNode.country} / ${hoveredNode.uploader}(辺 ${hoveredNode.deg} 本)`
          : "点にふれると曲名が出ます。クリックで詳細へ。小さい点は誰とも結ばれなかった録音です。"}
      </p>

      <div className="soundspace__legend">
        {keys.map((k) => (
          <span key={k} className="soundspace__key">
            <i style={{ background: colorOf(k) }} />
            {k}
          </span>
        ))}
        <span className="soundspace__key">
          <i style={{ background: OTHER }} />
          その他({Math.max(counts.length - keys.length, 0)} 群)
        </span>
      </div>

      {/* コントラスト warn の裏づけ(文字で読める表を必ず添える) */}
      <details className="netview__table">
        <summary>色分けの内訳を表で見る</summary>
        <div className="scrollx">
          <table className="ftable">
            <thead>
              <tr>
                <th>{colorBy === "country" ? "国" : "投稿者"}</th>
                <th className="num">録音</th>
                <th>色</th>
              </tr>
            </thead>
            <tbody>
              {counts.slice(0, 14).map(([k, v]) => (
                <tr key={k}>
                  <td>{k}</td>
                  <td className="num">{v}</td>
                  <td>{keys.includes(k) ? "色つき" : "その他(灰)"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>

      <NetworkStats net={net} />
        </>
      )}
    </>
  );
}

/** 図だけでは読めない数を、文字で添える。 */
function NetworkStats({ net }: { net: NetworkFile }) {
  const c = net.edge_composition;
  return (
    <div style={{ marginTop: 18 }}>
      <p className="note" style={{ fontSize: 13 }}>
        節点 {net.n_nodes} / 辺 {net.n_edges} / 誰とも結ばれなかった録音{" "}
        {net.n_isolated} / かたまり {net.n_components}(最大 {net.largest_component})。
        辺は<strong>相互 {net.k} 近傍</strong>(互いに相手の上位 {net.k} に入る組だけ)。
        配置は乱数種 {net.seed} で手元で計算しています。
      </p>
      <div className="scrollx">
        <table className="ftable">
          <thead>
            <tr>
              <th>辺が繋いでいるもの</th>
              <th className="num">割合</th>
              <th className="num">偶然なら</th>
              <th className="num">偶然比</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>同じ国どうし</td>
              <td className="num">{(c.same_country_ratio * 100).toFixed(1)}%</td>
              <td className="num">{(c.same_country_chance * 100).toFixed(1)}%</td>
              <td className="num">{c.same_country_lift?.toFixed(1)}×</td>
            </tr>
            <tr>
              <td>同じ投稿者どうし</td>
              <td className="num">{(c.same_uploader_ratio * 100).toFixed(1)}%</td>
              <td className="num">{(c.same_uploader_chance * 100).toFixed(1)}%</td>
              <td className="num">{c.same_uploader_lift?.toFixed(1)}×</td>
            </tr>
          </tbody>
        </table>
      </div>
      <p className="note" style={{ fontSize: 13 }}>
        <strong>割合をそのまま比べてはいけません。</strong>
        国は 37 種、投稿者は 122 種なので、でたらめに辺を張っても
        <strong>国のほうが揃いやすい</strong>からです。
        偶然に同じ札になる確率で割った「偶然比」で見ると、
        {c.uploader_lift_exceeds_country ? (
          <>
            {" "}
            <strong>投稿者のほうが強く効いています</strong>
            (国 {c.same_country_lift?.toFixed(1)}× 対 投稿者{" "}
            {c.same_uploader_lift?.toFixed(1)}×)。
            生の割合だけを見ると逆に読めてしまいます。
          </>
        ) : (
          <>
            {" "}
            国のほうが強く効いています(国 {c.same_country_lift?.toFixed(1)}× 対
            投稿者 {c.same_uploader_lift?.toFixed(1)}×)。
          </>
        )}
      </p>
    </div>
  );
}
