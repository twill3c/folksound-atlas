import Link from "next/link";

import Nav from "@/components/Nav";
import { getAnalysis, getManifest } from "@/lib/server-data";

export default function Home() {
  const manifest = getManifest();
  const analysis = getAnalysis();

  // 目玉の見出しは **測定結果の JSON から導く**。手書きしない(F-15 / T-019)。
  const headline = analysis?.results.find(
    (r) => !r.saw_country_labels && r.headline_supported !== undefined,
  );

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

          {headline && (
            <div
              className="card"
              style={{ marginTop: 24, borderLeft: "4px solid var(--aco)" }}
            >
              <h2 style={{ marginTop: 0, fontSize: 17 }}>測ってみた答え</h2>
              <p style={{ fontSize: 15, marginBottom: 8 }}>
                {headline.headline_supported ? (
                  <>
                    地理的に近い録音は、音響的にも近い傾向がありました。
                    しかもその傾向は、録音の出自(どのアーカイブがデジタル化したか)を
                    差し引いても残っています。
                  </>
                ) : headline.H01_supported ? (
                  <>
                    <strong>相関は出ましたが、目玉は立ちませんでした。</strong>
                    地理的に近い録音は音響的にも近く見えるものの、
                    その見かけは<strong>録音の出自</strong>
                    (どのアーカイブが同じ機材でデジタル化したか)で
                    説明できてしまい、地理を測ったとは言えませんでした。
                  </>
                ) : (
                  <>
                    <strong>目玉は立ちませんでした。</strong>
                    この標本では、地理的な近さと音響的な近さのあいだに
                    主張できるほどの関係は見つかりませんでした。
                  </>
                )}
              </p>
              <p className="note" style={{ fontSize: 13 }}>
                この文は、測定結果の JSON から選ばれています。
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
