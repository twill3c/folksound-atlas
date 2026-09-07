import Nav from "@/components/Nav";

export default function ModelsPage() {
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
          <p>
            この地図帳では、Embedding を作ったモデルを
            <strong>国名を教わったかどうか</strong>で二つに分けています。
          </p>
          <p>
            <span className="tag tag--blind">ラベルを見ていない</span>{" "}
            のモデルだけが「地理的に近い音楽は音響的にも近いか」の話に使えます。{" "}
            <span className="tag tag--saw">ラベルを見た</span>{" "}
            のモデルが国ごとに固まるのは、発見ではなく仕掛けだからです。
          </p>
          <p className="note">
            一覧はまだ空です。モデルを学習してから、
            <code>models.json</code> の内容をそのまま表にします。
          </p>
        </div>
      </main>
    </>
  );
}
