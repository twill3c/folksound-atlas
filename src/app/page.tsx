import Link from "next/link";

import Nav from "@/components/Nav";
import { getAnalysis, getManifest, getNetwork } from "@/lib/server-data";

export default function Home() {
  const manifest = getManifest();
  const analysis = getAnalysis();

  // 目玉の見出しは **測定結果の JSON から数え上げて導く**。手書きしない(F-15 / T-019)。
  // 一つのモデルの判定だけを拾うと、他の物差しと食い違ったときに黙って片方を捨てることになる。
  // そこで国ラベルを見ていない全モデルについて、物差しごとに「投稿者が国を上回ったか」を数える。
  const blind = (analysis?.results ?? []).filter(
    (r) => !r.saw_country_labels && r.geo_vs_acoustic,
  );
  const alpha = blind[0]?.alpha ?? 0.05;
  const nBlind = blind.length;
  const nHeadline = blind.filter((r) => r.headline_supported).length;
  const nProvSig = blind.filter(
    (r) => (r.provenance_vs_acoustic?.p ?? 1) < alpha,
  ).length;
  const nAriUploader = blind.filter(
    (r) => r.clustering?.uploader_beats_country,
  ).length;
  const nets = blind
    .map((r) => getNetwork(r.model_id))
    .filter((n): n is NonNullable<typeof n> => n != null);
  const nNetUploader = nets.filter(
    (n) => n.edge_composition.uploader_lift_exceeds_country,
  ).length;

  return (
    <>
      <header className="masthead">
        <div className="masthead__inner">
          <h1 className="masthead__title">FolkSound Atlas</h1>
          <p className="masthead__sub">
            Listen to the world. Explore the sound. — 世界の民謡を、音の構造から眺める
          </p>
        </div>
      </header>
      <Nav current="/" />

      <main>
        <div className="wrap">
          <p className="lede">
            世界のあちこちで歌われてきた民謡を、権利の確かめられたものだけ集めて、
            波形・周波数・音響特徴量・深層学習の Embedding という順に並べ直した地図帳です。
            中心にある問いはひとつだけあります。
          </p>

          <p
            className="lede"
            style={{ marginTop: 18, fontWeight: 700, color: "var(--aco)" }}
          >
            地理的に近い音楽は、音響的にも近いのか。
          </p>

          {manifest && (
            <p className="lede" style={{ marginTop: 18 }}>
              いま載っているのは <strong>{manifest.recording_count} 本</strong>の録音、
              <strong>{manifest.country_count} か国</strong>ぶんです。
            </p>
          )}

          {nBlind > 0 && (
            <div
              className="card"
              style={{ marginTop: 24, borderLeft: "4px solid var(--aco)" }}
            >
              <h2 style={{ marginTop: 0, fontSize: 17 }}>測ってみた答え</h2>
              <p style={{ fontSize: 15, marginBottom: 10 }}>
                {nHeadline === 0 ? (
                  <>
                    <strong>目玉は立ちませんでした。</strong>
                    国名を教わっていない {nBlind} つのモデルのどれでも、
                    地理的な近さが音響的な近さを説明するとは言えませんでした。
                  </>
                ) : (
                  <>
                    国名を教わっていない {nBlind} つのモデルのうち {nHeadline} つで、
                    地理的な近さが録音の出自を差し引いても音響的な近さを説明していました。
                  </>
                )}
              </p>
              <p style={{ fontSize: 14.5, marginBottom: 8 }}>
                かわりに見えたのは<strong>録音の出自</strong>
                (どのアーカイブが同じ機材でデジタル化したか)です。
                物差しを替えて測り直しても、向きは変わりませんでした。
              </p>
              <ul className="home-evidence">
                <li>
                  距離の相関 —— 出自との相関が有意だったモデル{" "}
                  <strong>
                    {nProvSig} / {nBlind}
                  </strong>
                </li>
                <li>
                  群れの切り方(ARI)—— 国より投稿者でよく揃ったモデル{" "}
                  <strong>
                    {nAriUploader} / {nBlind}
                  </strong>
                </li>
                <li>
                  類似ネットワーク(偶然比)—— 国より投稿者を強く繋いだモデル{" "}
                  <strong>
                    {nNetUploader} / {nets.length}
                  </strong>
                </li>
              </ul>
              <p className="note" style={{ fontSize: 13 }}>
                この文と数は、測定結果の JSON から数え上げています。
                都合のよい結果が出たときだけ書く、ということをしないためです。{" "}
                <Link href="/models/">数字を見る →</Link>
              </p>
            </div>
          )}

          <section style={{ marginTop: 34 }}>
            <h2 style={{ fontSize: 20, marginBottom: 12 }}>この地図帳の約束</h2>
            <div className="grid">
              <div className="card">
                <h3 style={{ fontSize: 15, marginTop: 0 }}>
                  国は、人が付けた札からしか取らない
                </h3>
                <p style={{ fontSize: 14, color: "var(--ink-2)", margin: 0 }}>
                  録音がどの国のものかは、題名や演奏者名から推し量りません。
                  Wikimedia Commons で人が付けたカテゴリだけを根拠にし、
                  その札が無いものはこの地図帳に載せません。
                </p>
              </div>

              <div className="card">
                <h3 style={{ fontSize: 15, marginTop: 0 }}>
                  権利を確かめたものだけを載せる
                </h3>
                <p style={{ fontSize: 14, color: "var(--ink-2)", margin: 0 }}>
                  録音そのものの権利と、その下にある曲の権利を別々に確かめます。
                  判定できない表記は「たぶん大丈夫」で通さず、除きます。
                </p>
              </div>

              <div className="card">
                <h3 style={{ fontSize: 15, marginTop: 0 }}>
                  答えを教わったモデルには、そう書く
                </h3>
                <p style={{ fontSize: 14, color: "var(--ink-2)", margin: 0 }}>
                  国名を教わって学習したモデルが国ごとに固まるのは、
                  発見ではなく仕掛けです。どのモデルが国名を見たかを
                  <span className="tag tag--saw" style={{ margin: "0 4px" }}>
                    ラベルを見た
                  </span>
                  の印で示し、地理の主張には使いません。
                </p>
              </div>
            </div>
          </section>

          <section style={{ marginTop: 30 }}>
            <h2 style={{ fontSize: 20, marginBottom: 12 }}>見て回る</h2>
            <div className="grid">
              <div className="card">
                <h3 style={{ fontSize: 15, marginTop: 0 }}>
                  <Link href="/map/">世界地図 →</Link>
                </h3>
                <p style={{ fontSize: 14, color: "var(--ink-2)", margin: 0 }}>
                  どの国から何本採れたかを見る。偏りもそのまま見えます。
                </p>
              </div>
              <div className="card">
                <h3 style={{ fontSize: 15, marginTop: 0 }}>
                  <Link href="/space/">音響空間 →</Link>
                </h3>
                <p style={{ fontSize: 14, color: "var(--ink-2)", margin: 0 }}>
                  Embedding を 2 次元へ潰した散布図。国で色分けするか、
                  投稿者で色分けするかを切り替えられます。
                </p>
              </div>
              <div className="card">
                <h3 style={{ fontSize: 15, marginTop: 0 }}>
                  <Link href="/distance/">地理と音響 →</Link>
                </h3>
                <p style={{ fontSize: 14, color: "var(--ink-2)", margin: 0 }}>
                  離れているほど音は違うのか。同じ投稿者と違う投稿者の二本の線で、
                  答えが図として見えます。
                </p>
              </div>
              <div className="card">
                <h3 style={{ fontSize: 15, marginTop: 0 }}>
                  <Link href="/network/">類似ネットワーク →</Link>
                </h3>
                <p style={{ fontSize: 14, color: "var(--ink-2)", margin: 0 }}>
                  音響的に近いものどうしを線で結ぶと、何のかたまりが見えるか。
                </p>
              </div>
              <div className="card">
                <h3 style={{ fontSize: 15, marginTop: 0 }}>
                  <Link href="/models/">モデル →</Link>
                </h3>
                <p style={{ fontSize: 14, color: "var(--ink-2)", margin: 0 }}>
                  誰が国名を見たか、そして目玉の検定結果。
                </p>
              </div>
            </div>
          </section>
        </div>
      </main>
    </>
  );
}
