import Nav from "@/components/Nav";
import { getManifest, getSongs } from "@/lib/server-data";

export default function About() {
  const manifest = getManifest();
  const songs = getSongs();

  // 投稿者の偏りは **出荷したデータから数え直す**。文中に数を手書きしない(HC-152)。
  const uploaderCounts = new Map<string, number>();
  for (const s of songs) {
    const u = s.uploader ?? "(不明)";
    uploaderCounts.set(u, (uploaderCounts.get(u) ?? 0) + 1);
  }
  const topUploaders = [...uploaderCounts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5);

  return (
    <>
      <header className="masthead">
        <div className="masthead__inner">
          <h1 className="masthead__title">この地図帳について</h1>
          <p className="masthead__sub">出自・権利・限界</p>
        </div>
      </header>
      <Nav current="/about/" />

      <main>
        <div className="wrap" style={{ maxWidth: 780 }}>
          <h2 style={{ fontSize: 19 }}>何を集めているか</h2>
          <p>
            Wikimedia Commons に置かれた民謡・伝統音楽の録音のうち、
            <strong>人が付けた国のカテゴリ</strong>を持ち、
            <strong>ライセンス表記が許可リストに一致する</strong>ものだけを集めています。
            どちらかが欠けたものは、この地図帳には載りません。
          </p>
          {manifest && (
            <p>
              いま載っているのは <strong>{manifest.recording_count} 本</strong>、
              <strong>{manifest.country_count} か国</strong>ぶんです。
              候補そのものは 5,492 件ありました(2026-09-07 実測)。
              そこから国ごとに上限を設けて選び直しています。
            </p>
          )}

          <h2 style={{ fontSize: 19 }}>なぜ全部載せないのか</h2>
          <p>
            候補 5,492 件のうち、<strong>スウェーデンが 3,660 件、フィンランドが 1,170 件</strong>で、
            この 2 国だけで 87.9% を占めていました。これは
            「その国に民謡が多い」ということではなく、
            <strong>その国のアーカイブが Commons へ大量に投稿した</strong>ということです。
          </p>
          <p>
            そのまま使うと、「地理的に近い音楽は音響的にも近いか」という問いは、
            実質<strong>「北欧の二つのアーカイブが同じ機材で録ったか否か」</strong>を
            測るものになってしまいます。そこで国ごとに上限(20 件)を設けて均しました。
            <strong>均したのであって、代表にしたのではありません。</strong>
          </p>
          {topUploaders.length > 0 && (
            <>
              <p>いま載っているぶんの投稿者の内訳は次のとおりです。</p>
              <div className="scrollx">
                <table className="ftable">
                  <thead>
                    <tr>
                      <th>投稿者</th>
                      <th className="num">件数</th>
                    </tr>
                  </thead>
                  <tbody>
                    {topUploaders.map(([u, n]) => (
                      <tr key={u}>
                        <td className="mono-sm">{u}</td>
                        <td className="num">{n}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="note">
                この表は、載せている録音から数え直したものです。
                「国」と「どのアーカイブがデジタル化したか」がどれくらい重なっているかを、
                読む人が自分で確かめられるように出しています。
              </p>
            </>
          )}

          <h2 style={{ fontSize: 19 }}>物差しを三本にして確かめたこと</h2>
          <p>
            「地理的に近い音楽は音響的にも近いか」を、系統の違う三つの表現で測りました。
            人が設計した音響特徴量、この地図帳の音源で学習した自作 CNN、そして
            <strong>この地図帳の音源も国名も一度も見ていない外部モデル</strong>
            (英語の話し声 960 時間で学習した wav2vec 2.0)です。
          </p>
          <p>
            三つとも、地理との相関は<strong>効果と呼べる大きさで出ませんでした</strong>。
            いっぽう<strong>「どのアーカイブがデジタル化したか」との相関は三つとも有意に出ました。</strong>
          </p>
          <p className="note">
            外部モデルの結果が効きます。自作 CNN だけなら
            「この地図帳の音源で学習したから録音の癖を覚えたのだろう」と言えました。
            けれど<strong>この音源を一度も見ていないモデルでも同じ向きに出た</strong>ので、
            それは学習のしかたの産物ではなく、<strong>録音そのものに宿っている</strong>ことになります。
            なお外部モデルは話し声のモデルであって音楽のモデルではありません。
            音楽向けの表現なら別の結果になりうる、という限界は残ります。
          </p>

          <h2 style={{ fontSize: 19 }}>採らなかった源</h2>
          <p>
            もとの仕様は Library of Congress(Citizen DJ / National Jukebox)を
            主データ源に据えていました。<strong>この経路は採っていません。</strong>
            2026-09-07 に測ったところ、<code>www.loc.gov</code> は対話型のチャレンジの
            内側にあり、<code>robots.txt</code> すら機械には返らず、
            JSON API は 403 を返しました。
            取得できないものを「主データ源」と書いたままにしておくと、
            後から同じ源がまた提案されるので、採らなかった理由ごとここに残します。
          </p>

          <h2 style={{ fontSize: 19 }}>国の札はどこから来たか</h2>
          <p>
            国名は Commons のカテゴリ(たとえば{" "}
            <code>Category:Folk music of Finland</code>)からのみ取り、
            題名や演奏者名からは推定していません。各録音には、
            その国名の根拠になったカテゴリ名を残してあります。
          </p>
          <p className="note">
            Commons には <code>deepcat:</code> というカテゴリ木を展開してくれる
            検索演算子がありますが、この地図帳では使っていません。
            2026-09-07 に測ったところ、アイルランドのカテゴリを指定したのに、
            アイルランド系のカテゴリに属していないスウェーデンの音源が 112 件返りました。
            警告もエラーも出ません。実際にカテゴリ所属で数え直すと 24 件でした。
            <strong>もっともらしい件数を返す誤りは、件数を数えるだけでは捕まりません。</strong>
          </p>

          <h2 style={{ fontSize: 19 }}>位置について</h2>
          <p>
            地図上の点は <strong>国の代表点</strong>(Wikidata の P625)であって、
            録音された場所ではありません。地理距離もこの粒度で計算しています。
            それ以上の精度は主張しません。
          </p>

          <h2 style={{ fontSize: 19 }}>音源について</h2>
          <p>
            この地図帳は音源を持たず、複製もしていません。
            再生ボタンが指しているのは Wikimedia Commons にある原本です。
            権利表示・クレジットも原本のものをそのまま載せています。
          </p>

          <h2 style={{ fontSize: 19 }}>この地図帳が主張しないこと</h2>
          <ul>
            <li>ある録音がその国・その文化を「代表する」とは主張しません。</li>
            <li>
              音響的に近いことは、歴史的・系統的なつながりを意味しません。
              録音された年代や機材が似ているだけのことがあります。
            </li>
            <li>
              カテゴリが表すのは<strong>曲の出自</strong>であって、
              演奏者の出身地でも録音地でもありません。
              イタリアの曲をセルビアの楽団が演奏した録音も「イタリア」に入ります。
            </li>
            <li>
              集まった件数は国によって大きく偏ります。多く集まった国が
              「民謡の多い国」ということではなく、
              <strong>Commons に載せた人がいた国</strong>ということです。
            </li>
          </ul>
        </div>
      </main>
    </>
  );
}
