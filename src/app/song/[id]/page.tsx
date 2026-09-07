import Link from "next/link";
import { notFound } from "next/navigation";

import FeatureTable from "@/components/FeatureTable";
import Nav from "@/components/Nav";
import Waveform from "@/components/Waveform";
import {
  getFeatures,
  getLabelBlindModels,
  getModels,
  getSimilarity,
  getSongs,
  getWaveforms,
} from "@/lib/server-data";

export function generateStaticParams() {
  return getSongs().map((s) => ({ id: s.id }));
}

export default async function SongPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const songs = getSongs();
  const song = songs.find((s) => s.id === id);
  if (!song) notFound();

  const byId = new Map(songs.map((s) => [s.id, s]));
  const feature = getFeatures().get(id) ?? null;
  const wave = getWaveforms().get(id) ?? null;
  const models = getModels();
  const blind = getLabelBlindModels();

  // 近傍は **ラベルを見ていないモデル** を既定で見せる(SPEC §2.2)
  const neighbourModels = blind.length > 0 ? blind : models;
  const neighbours = neighbourModels.map((m) => ({
    model: m,
    rows: (getSimilarity(m.model_id).get(id)?.similar ?? []).slice(0, 8),
  }));

  return (
    <>
      <header className="masthead">
        <div className="masthead__inner">
          <h1 className="masthead__title" style={{ fontSize: "clamp(20px,3vw,30px)" }}>
            {song.title}
          </h1>
          <p className="masthead__sub">
            {song.country}
            {song.duration_s != null && ` ・ ${Math.round(song.duration_s)} 秒`}
            {song.license && ` ・ ${song.license}`}
          </p>
        </div>
      </header>
      <Nav current="" />

      <main>
        <div className="wrap" style={{ maxWidth: 940 }}>
          <p style={{ marginTop: 0 }}>
            <Link href="/map/">← 世界地図へ戻る</Link>
          </p>

          <section className="panel">
            <h2>聴く</h2>
            {song.audio_url ? (
              <>
                {/* 音源は再配布せず、Commons の原本を直接指す(仕様書 §71) */}
                <audio controls preload="none" src={song.audio_url} className="player">
                  お使いのブラウザは音声再生に対応していません。
                </audio>
                <p className="note" style={{ marginTop: 8 }}>
                  再生しているのは Wikimedia Commons にある原本です。
                  この地図帳は音源を持たず、複製もしていません。
                </p>
              </>
            ) : (
              <p className="note">再生できる URL がありません。</p>
            )}
          </section>

          {wave && (
            <section className="panel">
              <h2>波形</h2>
              <Waveform envelope={wave.envelope} durationS={wave.duration_s} />
              <p className="note">
                縦は最大値で正規化した包絡線です。<strong>高さの絶対値に意味はありません</strong>
                (録音どうしの音量比較には使えません)。
              </p>
            </section>
          )}

          {feature && (
            <section className="panel">
              <h2>音響特徴量</h2>
              <FeatureTable f={feature} />
              <p className="note">
                値は、この録音から等間隔に抜き出した最大 12 個の 5 秒断片
                (計 60 秒)から算出しています。深層学習側が見ているのと同じ材料です。
              </p>
            </section>
          )}

          <section className="panel">
            <h2>音響的に近い録音</h2>
            {neighbours.map(({ model, rows }) => (
              <div key={model.model_id} style={{ marginBottom: 18 }}>
                <h3 className="panel__sub">
                  {model.name}{" "}
                  <span
                    className={`tag ${model.saw_country_labels ? "tag--saw" : "tag--blind"}`}
                  >
                    {model.saw_country_labels ? "ラベルを見た" : "ラベルを見ていない"}
                  </span>
                </h3>
                {rows.length === 0 ? (
                  <p className="note">近傍がまだ計算されていません。</p>
                ) : (
                  <ol className="neighbours">
                    {rows.map((r) => {
                      const s = byId.get(r.id);
                      return (
                        <li key={r.id}>
                          <Link href={`/song/${r.id}/`}>{s?.title ?? r.id}</Link>
                          <span className="neighbours__country">
                            {s?.country ?? "—"}
                          </span>
                          <span className="num">{r.score.toFixed(3)}</span>
                        </li>
                      );
                    })}
                  </ol>
                )}
              </div>
            ))}
            <p className="note">
              数はコサイン類似度です。<strong>似ているのは音の性質であって、
              歴史的・系統的なつながりではありません。</strong>
              録音された年代や機材が近いだけのこともあります。
            </p>
          </section>

          <section className="panel">
            <h2>出自と権利</h2>
            <dl className="prov">
              <div>
                <dt>出典</dt>
                <dd>
                  <a href={song.source_url}>{song.source}</a>
                </dd>
              </div>
              <div>
                <dt>ライセンス</dt>
                <dd>
                  {song.license_url ? (
                    <a href={song.license_url}>{song.license}</a>
                  ) : (
                    song.license
                  )}
                </dd>
              </div>
              {song.attribution && (
                <div>
                  <dt>クレジット</dt>
                  <dd>{song.attribution}</dd>
                </div>
              )}
              <div>
                <dt>国の札の根拠</dt>
                <dd>
                  <code>{song.country_source_category}</code>
                </dd>
              </div>
              <div>
                <dt>位置の粒度</dt>
                <dd>
                  {song.coordinate_precision === "country_centroid"
                    ? "国の代表点(録音地点ではない)"
                    : song.coordinate_precision}
                </dd>
              </div>
              <div>
                <dt>取得日</dt>
                <dd>{song.retrieval_date}</dd>
              </div>
              <div>
                <dt>SHA-256</dt>
                <dd className="mono-sm">{song.sha256}</dd>
              </div>
            </dl>
          </section>
        </div>
      </main>
    </>
  );
}
