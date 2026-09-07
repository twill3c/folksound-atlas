import Nav from "@/components/Nav";

export default function About() {
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
        <div className="wrap" style={{ maxWidth: 760 }}>
          <h2 style={{ fontSize: 19 }}>何を集めているか</h2>
          <p>
            Wikimedia Commons に置かれた民謡・伝統音楽の録音のうち、
            <strong>人が付けた国のカテゴリ</strong>を持ち、
            <strong>ライセンス表記が許可リストに一致する</strong>ものだけを集めています。
            どちらかが欠けたものは、この地図帳には載りません。
          </p>

          <h2 style={{ fontSize: 19 }}>採らなかった源</h2>
          <p>
            もとの仕様は Library of Congress(Citizen DJ / National Jukebox)を主データ源に
            据えていました。<strong>この経路は採っていません。</strong>
            2026-09-07 に測ったところ、<code>www.loc.gov</code> は対話型のチャレンジの内側にあり、
            <code>robots.txt</code> すら機械には返らず、JSON API は 403 を返しました。
            取得できないものを「主データ源」と書いたままにしておくと、
            後から同じ源がまた提案されるので、採らなかった理由ごとここに残します。
          </p>

          <h2 style={{ fontSize: 19 }}>国の札はどこから来たか</h2>
          <p>
            国名は Commons のカテゴリ(たとえば <code>Category:Folk music of Finland</code>)
            からのみ取り、題名や演奏者名からは推定していません。各録音には、
            その国名の根拠になったカテゴリ名を残してあります。
          </p>
          <p className="note">
            Commons には <code>deepcat:</code> というカテゴリ木を展開してくれる検索演算子が
            ありますが、この地図帳では使っていません。2026-09-07 に測ったところ、
            アイルランドのカテゴリを指定したのに、
            アイルランド系のカテゴリに属していないスウェーデンの音源が
            112 件返りました。警告もエラーも出ません。
            <strong>もっともらしい件数を返す誤りは、件数を数えるだけでは捕まりません。</strong>
          </p>

          <h2 style={{ fontSize: 19 }}>この地図帳が主張しないこと</h2>
          <ul>
            <li>ある録音がその国・その文化を「代表する」とは主張しません。</li>
            <li>
              音響的に近いことは、歴史的・系統的なつながりを意味しません。
              録音された年代や機材が似ているだけのことがあります。
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
