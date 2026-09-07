import MapExplorer from "@/components/MapExplorer";
import Nav from "@/components/Nav";
import { getManifest, getSongs } from "@/lib/server-data";

export default function MapPage() {
  const songs = getSongs();
  const manifest = getManifest();

  return (
    <>
      <header className="masthead">
        <div className="masthead__inner">
          <h1 className="masthead__title">世界地図</h1>
          <p className="masthead__sub">
            {manifest
              ? `${manifest.recording_count} 録音 / ${manifest.country_count} 国`
              : "録音された国から民謡をたどる"}
          </p>
        </div>
      </header>
      <Nav current="/map/" />

      <main>
        <div className="wrap">
          {songs.length === 0 ? (
            <p className="note">
              まだデータがありません。ETL を通してから描きます。
            </p>
          ) : (
            <MapExplorer songs={songs} />
          )}
        </div>
      </main>
    </>
  );
}
