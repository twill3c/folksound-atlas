import Nav from "@/components/Nav";

export default function SpacePage() {
  return (
    <>
      <header className="masthead">
        <div className="masthead__inner">
          <h1 className="masthead__title">音響空間</h1>
          <p className="masthead__sub">Embedding を 2 次元へ落として眺める</p>
        </div>
      </header>
      <Nav current="/space/" />

      <main>
        <div className="wrap">
          <p className="note">
            この画面はまだ作っている途中です。Embedding を計算してから描きます。
          </p>
        </div>
      </main>
    </>
  );
}
