import fs from "node:fs";
import path from "node:path";

import type {
  AnalysisFile,
  DistanceProfileFile,
  FeatureRow,
  Manifest,
  ModelInfo,
  NetworkFile,
  ProjectionFile,
  SimilarityRow,
  Song,
  SongsFile,
  SpectrogramFile,
  WaveformRow,
} from "./types";

// 静的書き出しなので、ビルド時にファイルから読む。
// **ここで読んだものだけがページに焼き込まれる** —— 実行時には取りに行かない。
const DATA_DIR = path.join(process.cwd(), "public", "data");

function readJson<T>(name: string): T | null {
  const p = path.join(DATA_DIR, name);
  if (!fs.existsSync(p)) return null;
  return JSON.parse(fs.readFileSync(p, "utf8")) as T;
}

export function getSongs(): Song[] {
  return readJson<SongsFile>("songs.json")?.songs ?? [];
}

export function getManifest(): Manifest | null {
  return readJson<Manifest>("manifest.json");
}

export function getModels(): ModelInfo[] {
  return readJson<{ models: ModelInfo[] }>("models.json")?.models ?? [];
}

export function getAnalysis(): AnalysisFile | null {
  return readJson<AnalysisFile>("analysis.json");
}

export function getFeatures(): Map<string, FeatureRow> {
  const f = readJson<{ items: FeatureRow[] }>("features.json");
  return new Map((f?.items ?? []).map((r) => [r.id, r]));
}

export function getWaveforms(): Map<string, WaveformRow> {
  const f = readJson<{ items: WaveformRow[] }>("waveforms.json");
  return new Map((f?.items ?? []).map((r) => [r.id, r]));
}

export function getNetwork(modelId: string): NetworkFile | null {
  return readJson<NetworkFile>(`network_${modelId}.json`);
}

export function getDistanceProfile(): DistanceProfileFile | null {
  return readJson<DistanceProfileFile>("distance_profile.json");
}

export function getSpectrograms(): SpectrogramFile | null {
  return readJson<SpectrogramFile>("spectrograms.json");
}

export function getSimilarity(modelId: string): Map<string, SimilarityRow> {
  const f = readJson<{ items: SimilarityRow[] }>(`similarity_${modelId}.json`);
  return new Map((f?.items ?? []).map((r) => [r.id, r]));
}

export function getProjection(
  modelId: string,
  method: "umap" | "pca",
): ProjectionFile | null {
  return readJson<ProjectionFile>(`${method}_${modelId}.json`);
}

/**
 * 地理の主張に使ってよいモデルだけを返す(SPEC §2.2 / G-04)。
 * 国ラベルを見たモデルは、ここから出さない。
 */
export function getLabelBlindModels(): ModelInfo[] {
  return getModels().filter((m) => !m.saw_country_labels);
}
