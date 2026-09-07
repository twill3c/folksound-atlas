import Nav from "@/components/Nav";
import SpaceExplorer from "@/components/SpaceExplorer";
import { getModels, getProjection, getSongs } from "@/lib/server-data";
import type { ProjectionFile } from "@/lib/types";

export default function SpacePage() {
  const songs = getSongs();
  const models = getModels();

  const projections: Record<
    string,
    { umap: ProjectionFile | null; pca: ProjectionFile | null }
  > = {};
  for (const m of models) {
    projections[m.model_id] = {
      umap: getProjection(m.model_id, "umap"),
      pca: getProjection(m.model_id, "pca"),
    };
  }

  return (
    <>
      <header className="masthead">
        <div className="masthead__inner">
          <h1 className="masthead__title">音響空間</h1>
          <p className="masthead__sub">
            Embedding を 2 次元へ落として眺める。点ひとつが 1 録音
          </p>
        </div>
      </header>
      <Nav current="/space/" />

      <main>
        <div className="wrap">
          {models.length === 0 ? (
            <p className="note">
              まだ Embedding がありません。学習を通してから描きます。
            </p>
          ) : (
            <SpaceExplorer songs={songs} models={models} projections={projections} />
          )}

          <p className="note" style={{ marginTop: 22 }}>
            この配置は「音楽の絶対的な分類」ではありません。
            選んだ Embedding 空間を 2 次元へ潰して見せているだけで、
            潰し方(UMAP か PCA か)を変えると見え方も変わります。
            だから両方を置いてあります。
          </p>
        </div>
      </main>
    </>
  );
}
