import Nav from "@/components/Nav";

export default function MapPage() {
  return (
    <>
      <header className="masthead">
        <div className="masthead__inner">
          <h1 className="masthead__title">世界地図</h1>
          <p className="masthead__sub">録音された場所から民謡をたどる</p>
        </div>
      </header>
      <Nav current="/map/" />

      <main>
        <div className="wrap">
          <p className="note">
            この画面はまだ作っている途中です。地図に置く録音の集合が確定してから描きます。
            ここに件数や地点を仮に置くことはしません。
          </p>
        </div>
      </main>
    </>
  );
}
