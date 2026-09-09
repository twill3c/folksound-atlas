import Link from "next/link";

import Nav from "@/components/Nav";
import NetworkView from "@/components/NetworkView";
import { getModels } from "@/lib/server-data";

export default function NetworkPage() {
  const models = getModels();

  return (
    <>
      <header className="masthead">
        <div className="masthead__inner">
          <h1 className="masthead__title">類似ネットワーク</h1>
          <p className="masthead__sub">
            音響的に近いものどうしを線で結ぶと、何のかたまりが見えるか
          </p>
        </div>
      </header>
      <Nav current="/network/" />

      <main>
        <div className="wrap">
          {models.length === 0 ? (
            <p className="note">まだ Embedding がありません。</p>
          ) : (
            <>
              <p className="lede" style={{ maxWidth: "68ch" }}>
                録音を点、音響的に近いことを線にした図です。
                線は<strong>互いに相手の上位に入っている組だけ</strong>に絞ってあります
                (片側だけの「近い」を結ぶと毛玉になって読めません)。
              </p>
              <p className="lede" style={{ maxWidth: "68ch", marginTop: 14 }}>
                色分けを<strong>国</strong>と<strong>投稿者</strong>で切り替えられます。
                かたまりがどちらでよく揃うかを、自分の目で見比べてください。
              </p>

              <NetworkView models={models} />

              <p className="note" style={{ marginTop: 22 }}>
                ここで見えるかたまりは「音楽の系統」ではありません。
                この地図帳の測定では、音響的な近さを主に説明していたのは
                <Link href="/models/">録音の出自</Link>でした。
                <Link href="/distance/">地理と音響</Link>の図もあわせて見てください。
              </p>
            </>
          )}
        </div>
      </main>
    </>
  );
}
