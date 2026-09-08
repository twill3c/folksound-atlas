import Nav from "@/components/Nav";
import { getAnalysis, getModels } from "@/lib/server-data";

function fmt(v: number | undefined, d = 3) {
  return v === undefined ? "—" : v.toFixed(d);
}

export default function ModelsPage() {
  const models = getModels();
  const analysis = getAnalysis();

  return (
    <>
      <header className="masthead">
        <div className="masthead__inner">
          <h1 className="masthead__title">モデル</h1>
          <p className="masthead__sub">
            Embedding を作った側の一覧と、国ラベルを見たかどうか
          </p>
        </div>
      </header>
      <Nav current="/models/" />

      <main>
        <div className="wrap">
          <p className="lede" style={{ maxWidth: "70ch" }}>
            この地図帳では、Embedding を作ったモデルを
            <strong>国名を教わったかどうか</strong>で二つに分けています。
            国名を教わったモデルの Embedding が国ごとに固まるのは、
            発見ではなく<strong>仕掛け</strong>だからです。
          </p>

          {models.length === 0 ? (
            <p className="note">一覧はまだ空です。</p>
          ) : (
            <div className="scrollx">
              <table className="ftable">
                <thead>
                  <tr>
                    <th>モデル</th>
                    <th>種別</th>
                    <th className="num">次元</th>
                    <th>学習のしかた</th>
                    <th>国ラベル</th>
                    <th>地理の主張</th>
                  </tr>
                </thead>
                <tbody>
                  {models.map((m) => (
                    <tr key={m.model_id}>
                      <td>{m.name}</td>
                      <td className="mono-sm">{m.type}</td>
                      <td className="num">{m.embedding_dimension}</td>
                      <td>{m.training_objective}</td>
                      <td>
                        <span
                          className={`tag ${m.saw_country_labels ? "tag--saw" : "tag--blind"}`}
                        >
                          {m.saw_country_labels ? "見た" : "見ていない"}
                        </span>
                      </td>
                      <td>{m.may_support_geographic_claim ? "使える" : "使えない"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <section style={{ marginTop: 36 }}>
            <h2 style={{ fontSize: 20 }}>目玉の測定結果</h2>
            {!analysis ? (
              <p className="note">まだ測っていません。</p>
            ) : (
              <>
                <div className="card" style={{ marginBottom: 18 }}>
                  <p style={{ marginTop: 0, fontSize: 14 }}>
                    <strong>測る前に登録した仮説</strong>
                  </p>
                  <ul style={{ fontSize: 14, marginBottom: 6 }}>
                    <li>
                      <strong>H-01</strong> — {analysis.preregistered.H01}
                    </li>
                    <li>
                      <strong>H-02</strong> — {analysis.preregistered.H02}
                    </li>
                  </ul>
                  <p className="note" style={{ fontSize: 13 }}>
                    {analysis.preregistered.note}
                  </p>
                  <p className="note" style={{ fontSize: 13, marginTop: 8 }}>
                    <strong>物差しは二つ出します。</strong>
                    距離の相関(Mantel)と、群れの切り方の一致(ARI)です。
                    この二つは同じことを言っていません —— 距離で見ると国との関係はほぼ 0 ですが、
                    群れで見ると 0 ではありません。Mantel は全部の組を平等に見るので
                    数の多い「別の国どうし」に薄められ、ARI は大きな塊の構造に効くからです。
                    <strong>結果を見てから都合のよい物差しを選ばないために、両方を置いています。</strong>
                  </p>
                </div>

                {analysis.results.map((r) => {
                  if (r.excluded_from_geographic_claim) {
                    return (
                      <div key={r.model_id} className="card" style={{ marginBottom: 14 }}>
                        <h3 style={{ marginTop: 0, fontSize: 15 }}>
                          {r.model_id}{" "}
                          <span className="tag tag--saw">解析から除外</span>
                        </h3>
                        <p style={{ fontSize: 14, margin: 0 }}>{r.reason}</p>
                      </div>
                    );
                  }
                  return (
                    <div key={r.model_id} className="card" style={{ marginBottom: 14 }}>
                      <h3 style={{ marginTop: 0, fontSize: 15 }}>
                        {r.model_name ?? r.model_id}{" "}
                        <span className="tag tag--blind">ラベルを見ていない</span>
                      </h3>
                      <div className="scrollx">
                        <table className="ftable">
                          <thead>
                            <tr>
                              <th>測ったもの</th>
                              <th className="num">相関 r</th>
                              <th className="num">p 値</th>
                            </tr>
                          </thead>
                          <tbody>
                            <tr>
                              <td>地理距離 × 音響距離(H-01)</td>
                              <td className="num">{fmt(r.geo_vs_acoustic?.r)}</td>
                              <td className="num">{fmt(r.geo_vs_acoustic?.p, 4)}</td>
                            </tr>
                            <tr>
                              <td>同上・録音の出自を統制(H-02)</td>
                              <td className="num">
                                {fmt(r.geo_vs_acoustic_given_provenance?.r)}
                              </td>
                              <td className="num">
                                {fmt(r.geo_vs_acoustic_given_provenance?.p, 4)}
                              </td>
                            </tr>
                            <tr>
                              <td>出自 × 音響距離(対抗仮説)</td>
                              <td className="num">
                                {fmt(r.provenance_vs_acoustic?.r)}
                              </td>
                              <td className="num">
                                {fmt(r.provenance_vs_acoustic?.p, 4)}
                              </td>
                            </tr>
                          </tbody>
                        </table>
                      </div>
                      <p style={{ fontSize: 14, marginBottom: 4 }}>
                        H-01: <strong>{r.H01_supported ? "成立" : "不成立"}</strong>
                        {" ・ "}
                        H-02: <strong>{r.H02_supported ? "成立" : "不成立"}</strong>
                        {" → 目玉は "}
                        <strong>
                          {r.headline_supported ? "立った" : "立たなかった"}
                        </strong>
                      </p>
                      {r.clustering && (
                        <div style={{ marginTop: 14 }}>
                          <h4 style={{ fontSize: 13.5, margin: "0 0 6px" }}>
                            別の物差し —— 群れの切り方で見る(k={r.clustering.k})
                          </h4>
                          <div className="scrollx">
                            <table className="ftable">
                              <thead>
                                <tr>
                                  <th>音響クラスタと一致するか</th>
                                  <th className="num">ARI</th>
                                  <th className="num">まとまり</th>
                                </tr>
                              </thead>
                              <tbody>
                                <tr>
                                  <td>国</td>
                                  <td className="num">
                                    {r.clustering.vs_country.ari.toFixed(4)}
                                  </td>
                                  <td className="num">
                                    {r.clustering.silhouette_country?.toFixed(3) ?? "—"}
                                  </td>
                                </tr>
                                <tr>
                                  <td>投稿者(どのアーカイブか)</td>
                                  <td className="num">
                                    {r.clustering.vs_uploader.ari.toFixed(4)}
                                  </td>
                                  <td className="num">
                                    {r.clustering.silhouette_uploader?.toFixed(3) ?? "—"}
                                  </td>
                                </tr>
                              </tbody>
                            </table>
                          </div>
                          <p className="note" style={{ fontSize: 13 }}>
                            ARI は偶然の一致を差し引いた指標で、0 なら「偶然と変わらない」です。
                            ここでも{" "}
                            <strong>
                              {r.clustering.uploader_beats_country
                                ? "投稿者のほうが国よりよく一致しました"
                                : "国のほうが投稿者よりよく一致しました"}
                            </strong>
                            。ただし「まとまり」(シルエット係数)は
                            <strong>どちらも負</strong>で、
                            録音は平均して自分の群れの仲間より他の群れに近い状態です。
                            つまり<strong>どちらの札も音響空間の良い説明ではありません。</strong>
                          </p>
                        </div>
                      )}

                      <p className="note" style={{ fontSize: 13 }}>
                        録音 {r.n_recordings} 本 / {r.n_countries} 国 /{" "}
                        投稿者 {r.n_uploaders} 人・置換 {r.permutations} 回(乱数種{" "}
                        {r.seed})
                      </p>
                    </div>
                  );
                })}
              </>
            )}
          </section>
        </div>
      </main>
    </>
  );
}
