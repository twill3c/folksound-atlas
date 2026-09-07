export type CoordinatePrecision = "exact" | "country_centroid" | "unknown";

export interface Song {
  id: string;
  title: string;
  country: string;
  country_source_category: string;
  region: string | null;
  latitude: number | null;
  longitude: number | null;
  coordinate_precision: CoordinatePrecision;
  source: string;
  source_url: string;
  audio_url: string | null;
  license: string;
  license_url: string | null;
  attribution: string | null;
  rights_verified: true;
  underlying_work_status: string;
  retrieval_date: string;
  sha256: string;
  duration_s: number | null;
  sample_rate_original: number | null;
  segment_count: number | null;
  uploader: string | null;
}

export interface SongsFile {
  dataset_version: string;
  generated_at: string;
  songs: Song[];
}

export interface FeatureRow {
  id: string;
  rms: number;
  zcr: number;
  spectral_centroid: number;
  spectral_bandwidth: number;
  spectral_rolloff: number;
  spectral_contrast: number[];
  mfcc: number[];
  chroma: number[];
  tempo: number;
}

export interface WaveformRow {
  id: string;
  envelope: number[];
  duration_s: number;
}

export interface ModelInfo {
  model_id: string;
  name: string;
  type: "features" | "cnn-autoencoder" | "cnn-classifier" | "pretrained";
  embedding_dimension: number;
  training_objective: string;
  training_dataset: string | null;
  /** SPEC §2.2 / G-04。true のモデルは地理の主張に使えない。 */
  saw_country_labels: boolean;
  may_support_geographic_claim: boolean;
  label_note: string;
  version: string;
}

export interface ProjectionRow {
  id: string;
  x: number;
  y: number;
}

export interface ProjectionFile {
  model: string;
  method: "umap" | "pca";
  params: Record<string, unknown>;
  random_state: number;
  items: ProjectionRow[];
}

export interface SimilarityRow {
  id: string;
  similar: { id: string; score: number }[];
}

/** 事前登録した目玉(H-01)と対照(H-02)の測定結果。 */
export interface AnalysisResult {
  model_id: string;
  model_name?: string;
  saw_country_labels: boolean;
  excluded_from_geographic_claim?: boolean;
  reason?: string;
  n_recordings?: number;
  n_countries?: number;
  n_uploaders?: number;
  permutations?: number;
  seed?: number;
  alpha?: number;
  geo_vs_acoustic?: { r: number; p: number };
  geo_vs_acoustic_given_provenance?: { r: number; p: number };
  provenance_vs_acoustic?: { r: number; p: number };
  H01_supported?: boolean;
  H02_supported?: boolean;
  headline_supported?: boolean;
}

export interface AnalysisFile {
  generated_at: string;
  preregistered: {
    H01: string;
    H02: string;
    decision_rule: Record<string, string>;
    note: string;
  };
  results: AnalysisResult[];
}

export interface Manifest {
  dataset_version: string;
  generated_at: string;
  recording_count: number;
  country_count: number;
  uploader_count: number;
  feature_version: string;
  embedding_models: string[];
  audio_hosting: string;
  projection: Record<string, unknown> | null;
}
