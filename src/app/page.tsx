import Nav from "@/components/Nav";

export default function Home() {
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

          <p className="lede" style={{ marginTop: 18 }}>
            この地図帳は、その問いに「はい」と答えるために作られていません。
            <strong>測って、答えが何であれ画面に出す</strong>ために作られています。
          </p>

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
            <p className="note">
              このページの数値・図・判定は、すべて手元で計算した結果の JSON から描いています。
              まだ測っていない欄は、もっともらしい数を置かずに空のままにしてあります。
            </p>
          </section>
        </div>
      </main>
    </>
  );
}
