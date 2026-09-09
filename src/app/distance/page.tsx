import Link from "next/link";

import DistanceProfile, { DistanceLegend } from "@/components/DistanceProfile";
import Nav from "@/components/Nav";
import { getDistanceProfile } from "@/lib/server-data";

export default function DistancePage() {
  const prof = getDistanceProfile();

  return (
    <>
      <header className="masthead">
        <div className="masthead__inner">
          <h1 className="masthead__title">地理と音響</h1>
          <p className="masthead__sub">
            離れているほど音は違うのか。図にすると答えが見える
          </p>
        </div>
      </header>
      <Nav current="/distance/" />

      <main>
        <div className="wrap">
          {!prof ? (
            <p className="note">まだ測っていません。</p>
          ) : (
            <>
              <p className="lede" style={{ maxWidth: "68ch" }}>
                録音を二本ずつ組にして、<strong>地理的にどれだけ離れているか</strong>と
                <strong>音響的にどれだけ違うか</strong>を並べました。
                組は全部で {prof.models[0]?.n_pairs.toLocaleString()} 通りあり、
                そのまま点で打つと潰れて読めないので、
                距離で束ねて束ごとの平均を線にしています。
              </p>
              <p className="lede" style={{ maxWidth: "68ch", marginTop: 14 }}>
                線を<strong>二本に分けている</strong>のが要点です。
                <strong>同じ人が投稿した組</strong>と
                <strong>違う人が投稿した組</strong>。
                投稿者はたいてい「どのアーカイブがデジタル化したか」を意味します。
              </p>

              <div className="card" style={{ marginTop: 20 }}>
                <p style={{ margin: 0, fontSize: 15 }}>
                  <strong>読み方。</strong>
                  「違う投稿者」の線が右へ行っても上がらなければ、
                  <strong>どれだけ離れていても音の違いは変わらない</strong>
                  ——つまり地理は音響を説明していません。
                  いっぽう二本の線が離れていれば、
                  <strong>同じアーカイブから来たかどうかが効いている</strong>ことになります。
                </p>
              </div>

              <DistanceLegend />

              {prof.models.map((m) => (
                <section key={m.model_id} style={{ marginTop: 26 }}>
                  <h2 style={{ fontSize: 16, marginBottom: 2 }}>
                    {m.model_name}{" "}
                    <span className="tag tag--blind">ラベルを見ていない</span>
                  </h2>
                  <p className="note" style={{ fontSize: 12.5, marginTop: 0 }}>
                    縦軸は音響距離(1 − コサイン類似度)。
                    <strong>モデルごとに縦軸の目盛が違います</strong>ので、
                    比べるのは高さではなく<strong>線の形</strong>です。
                  </p>
                  <DistanceProfile model={m} />
                </section>
              ))}

              <section style={{ marginTop: 34 }}>
                <h2 style={{ fontSize: 19 }}>
                  地理的に遠いのに、音響的に近い組
                </h2>
                <p style={{ maxWidth: "66ch" }}>
                  仕様の問い Q2「地理的に遠い民謡にも音響的な類似性はあるか」です。
                  8,000km 以上離れた組のうち、音響距離がいちばん小さかったものを並べます。
                </p>
                {prof.models.slice(0, 1).map((m) => (
                  <div className="scrollx" key={m.model_id}>
                    <table className="ftable">
                      <thead>
                        <tr>
                          <th>録音 A</th>
                          <th>録音 B</th>
                          <th className="num">距離</th>
                          <th className="num">音響距離</th>
                          <th>同じ投稿者か</th>
                        </tr>
                      </thead>
                      <tbody>
                        {m.far_but_close.map((p, i) => (
                          <tr key={i}>
                            <td>
                              <Link href={`/song/${p.a.id}/`}>{p.a.title}</Link>
                              <span className="neighbours__country">
                                {" "}
                                {p.a.country}
                              </span>
                            </td>
                            <td>
                              <Link href={`/song/${p.b.id}/`}>{p.b.title}</Link>
                              <span className="neighbours__country">
                                {" "}
                                {p.b.country}
                              </span>
                            </td>
                            <td className="num">
                              {Math.round(p.geo_km).toLocaleString()}km
                            </td>
                            <td className="num">
                              {p.acoustic_distance.toFixed(3)}
                            </td>
                            <td>{p.same_uploader ? "同じ" : "違う"}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ))}
                <p className="note">
                  こうした組を「大陸をまたいだ発見」と読みたくなりますが、
                  <strong>そう読む前に確かめることがあります。</strong>
                  音響的に近い組は、録音の年代や機材が似ているだけのことがあります。
                  この地図帳の測定では、
                  <Link href="/models/">音響的な近さを主に説明していたのは出自</Link>
                  でした。
                </p>
              </section>
            </>
          )}
        </div>
      </main>
    </>
  );
}
