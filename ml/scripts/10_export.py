"""10_export.py — Web アプリへ配る JSON を作る(F-16 / N-02 / N-03 / G-05)。

Vercel には**計算を置かない**。ここで作った JSON を静的に配るだけにする(仕様書 §73–76)。

音源は**再配布しない**。再生は Commons の原本 URL を直接指す(仕様書 §71–72)。
こうすると Vercel の容量も課金経路も増えず、出典が常に原本を指す。

出力: public/data/*.json
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from folksound.countries import canonical_country  # noqa: E402

DATASET_VERSION = "1.1.0"


def strip_query(url: str | None) -> str | None:
    """utm 付きの取得用 URL から、素の原本 URL に戻す。"""
    if not url:
        return url
    return url.split("?", 1)[0]


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", type=Path, default=root / "public" / "data")
    args = ap.parse_args()

    raw = root / "data" / "raw"
    feat = root / "data" / "features"
    emb = root / "data" / "embeddings"
    exports = root / "data" / "exports"

    sel = json.loads((raw / "selected.json").read_text(encoding="utf-8"))
    coords = json.loads((raw / "country_coords.json").read_text(encoding="utf-8"))["countries"]
    segs = json.loads((feat / "segments.json").read_text(encoding="utf-8"))
    seg_by_id = {s["id"]: s for s in segs["items"]}
    features = json.loads((feat / "features.json").read_text(encoding="utf-8"))
    have = {f["id"] for f in features["items"]}

    args.outdir.mkdir(parents=True, exist_ok=True)

    # --- songs.json ---------------------------------------------------------
    songs = []
    for r in sel["records"]:
        if r["id"] not in have:
            continue  # 特徴量まで通らなかったものは出荷しない
        c = canonical_country(r["country"])
        co = coords.get(c)
        s = seg_by_id.get(r["id"], {})
        songs.append({
            "id": r["id"],
            "title": r["file"].replace("File:", "").rsplit(".", 1)[0],
            "country": c,
            "country_source_category": r["country_source_category"],
            "region": None,
            "latitude": co["lat"] if co else None,
            "longitude": co["lon"] if co else None,
            "coordinate_precision": "country_centroid" if co else "unknown",
            "source": "Wikimedia Commons",
            "source_url": "https://commons.wikimedia.org/wiki/"
                          + r["file"].replace(" ", "_"),
            "audio_url": strip_query(r.get("url")),
            "license": r.get("license_short") or r.get("license_machine") or "",
            "license_url": r.get("license_url"),
            "attribution": r.get("artist") or r.get("credit"),
            "rights_verified": True,
            "underlying_work_status": "traditional",
            "retrieval_date": r["retrieval_date"],
            "sha256": r["sha256"],
            "duration_s": s.get("duration_s"),
            "sample_rate_original": s.get("sample_rate_original"),
            "segment_count": s.get("segments"),
            "uploader": r.get("uploader"),
        })
    (args.outdir / "songs.json").write_text(json.dumps({
        "dataset_version": DATASET_VERSION,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "songs": songs,
    }, ensure_ascii=False), encoding="utf-8")

    # --- そのまま写すもの -----------------------------------------------------
    copies = [
        (feat / "features.json", "features.json"),
        (feat / "waveforms.json", "waveforms.json"),
        (emb / "models.json", "models.json"),
        (exports / "analysis.json", "analysis.json"),
    ]
    for src, name in copies:
        if src.exists():
            shutil.copyfile(src, args.outdir / name)

    models = json.loads((emb / "models.json").read_text(encoding="utf-8"))["models"]
    # **生の Embedding は配らない**(N-03)。画面が使うのは射影と近傍だけで、
    # 128 次元 × 全件を配ると数 MB 増えるのに、誰も読まない。
    # 生の Embedding は `data/embeddings/` に残り、検査もそちらに当てる。
    for m in models:
        for kind in ("umap", "pca", "similarity"):
            p = emb / f"{kind}_{m['model_id']}.json"
            if p.exists():
                shutil.copyfile(p, args.outdir / p.name)

    # --- manifest(仕様書 §81 / §135)----------------------------------------
    (args.outdir / "manifest.json").write_text(json.dumps({
        "dataset_version": DATASET_VERSION,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "recording_count": len(songs),
        "country_count": len({s["country"] for s in songs}),
        "uploader_count": len({s["uploader"] for s in songs if s["uploader"]}),
        "feature_version": features.get("feature_version", "1.0"),
        "embedding_models": [m["model_id"] for m in models],
        "audio_hosting": "Wikimedia Commons(原本を直接参照。本サイトは音源を再配布しない)",
        "projection": json.loads(
            (emb / "projection_manifest.json").read_text(encoding="utf-8")
        ) if (emb / "projection_manifest.json").exists() else None,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    total = sum(f.stat().st_size for f in args.outdir.glob("*.json"))
    print(f"出荷 {len(songs)} 録音 / {len({s['country'] for s in songs})} 国")
    print(f"public/data の合計: {total / 1e6:.2f} MB")
    for f in sorted(args.outdir.glob("*.json")):
        print(f"  {f.stat().st_size / 1e3:8.1f} KB  {f.name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
