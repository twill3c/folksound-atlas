"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import SoundSpace from "@/components/SoundSpace";
import type { ModelInfo, ProjectionFile, Song } from "@/lib/types";

interface Props {
  songs: Song[];
  models: ModelInfo[];
  projections: Record<string, { umap: ProjectionFile | null; pca: ProjectionFile | null }>;
}

export default function SpaceExplorer({ songs, models, projections }: Props) {
  const router = useRouter();
  const [modelId, setModelId] = useState(models[0]?.model_id ?? "");
  const [method, setMethod] = useState<"umap" | "pca">("umap");
  const [colorBy, setColorBy] = useState<"country" | "uploader">("country");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  const songMap = useMemo(() => new Map(songs.map((s) => [s.id, s])), [songs]);
  const model = models.find((m) => m.model_id === modelId);
  const proj = projections[modelId]?.[method] ?? null;

  return (
    <>
      <div className="controls">
        <div className="controls__group">
          <span className="controls__label">モデル</span>
          {models.map((m) => (
            <button
              key={m.model_id}
              type="button"
              className={m.model_id === modelId ? "is-on" : ""}
              onClick={() => setModelId(m.model_id)}
            >
              {m.name}
              <span
                className={`tag ${m.saw_country_labels ? "tag--saw" : "tag--blind"}`}
                style={{ marginLeft: 6 }}
              >
                {m.saw_country_labels ? "ラベルを見た" : "見ていない"}
              </span>
            </button>
          ))}
        </div>

        <div className="controls__group">
          <span className="controls__label">射影</span>
          {(["umap", "pca"] as const).map((m) => (
            <button
              key={m}
              type="button"
              className={m === method ? "is-on" : ""}
              onClick={() => setMethod(m)}
            >
              {m.toUpperCase()}
            </button>
          ))}
        </div>

        <div className="controls__group">
          <span className="controls__label">色分け</span>
          <button
            type="button"
            className={colorBy === "country" ? "is-on" : ""}
            onClick={() => setColorBy("country")}
          >
            国
          </button>
          <button
            type="button"
            className={colorBy === "uploader" ? "is-on" : ""}
            onClick={() => setColorBy("uploader")}
          >
            投稿者(出自)
          </button>
        </div>
      </div>

      {model?.saw_country_labels && (
        <p className="warnbox">
          <strong>このモデルは国名を教わって学習しています。</strong>
          国ごとに固まって見えるのは当たり前で、
          「音響的に近い国どうしが近い」という証拠にはなりません。
          並べてあるのは、<em>そう見えること</em>と<em>そう言えること</em>が
          別だと示すためです。
        </p>
      )}

      {colorBy === "uploader" && (
        <p className="note" style={{ marginBottom: 10 }}>
          投稿者で色分けすると、「国の固まり」に見えていたものが
          <strong>デジタル化したアーカイブの固まり</strong>でないかを見比べられます。
          この二つが重なっているなら、地理を測ったとは言えません。
        </p>
      )}

      {proj ? (
        <SoundSpace
          points={proj.items}
          songs={songMap}
          colorBy={colorBy}
          selectedId={selectedId}
          onSelect={(id) => {
            setSelectedId(id);
            router.push(`/song/${id}/`);
          }}
        />
      ) : (
        <p className="note">この組み合わせの射影はまだありません。</p>
      )}

      {model && (
        <dl className="modelcard">
          <div>
            <dt>学習のしかた</dt>
            <dd>{model.training_objective}</dd>
          </div>
          <div>
            <dt>次元</dt>
            <dd>{model.embedding_dimension}</dd>
          </div>
          <div>
            <dt>国ラベル</dt>
            <dd>{model.label_note}</dd>
          </div>
          {proj?.method === "umap" && (
            <div>
              <dt>再現の種</dt>
              <dd>
                random_state = {proj.random_state}(同じ種なら同じ配置になります)
              </dd>
            </div>
          )}
        </dl>
      )}
    </>
  );
}
