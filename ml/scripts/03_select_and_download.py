"""03_select_and_download.py — 選抜して音源を取得する(SPEC §6 / F-01 / 仕様書 §42)。

選抜の考え方(**偏りを承知のうえで、承知していると分かる形に均す**):

    Commons の民謡音源は国ごとの件数が桁違いに偏る。スウェーデンとフィンランドの
    公的アーカイブが大量に投稿しているためで、これは「その国に民謡が多い」ことではなく
    「その国のアーカイブが Commons に載せた」ことを意味する。

    そのまま使うと、H-01(地理距離 vs 音響距離)は
    **「北欧の二つのアーカイブが同じ機材で録ったか否か」**をほぼそのまま測ってしまう。
    そこで **国ごとに上限を設ける**。上限は「均した」のであって「代表にした」のではない。
    どの国から何件採ったかは manifest に残し、画面にも出す。

出力: data/raw/selected.json と data/raw/audio/<id>.<ext>
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from folksound.countries import canonical_country  # noqa: E402
from folksound.preprocess import sha256_of  # noqa: E402

# Wikimedia の User-Agent 方針は「クライアント名/版 + 連絡先」を求める。
# 連絡先は**リポジトリの URL**を出す(要求されていない相手にメールアドレスを送らない)。
# 実測 2026-09-07: 連絡先が実在の URL でない UA だと upload.wikimedia.org が
# 早い段階で 429 を返し、600 秒の待機を指示してきた。
UA = (
    "FolkSoundAtlas/0.1 "
    "(https://github.com/twill3c/folksound-atlas; research dataset builder) "
    "python-urllib"
)


def select(
    records: list[dict],
    per_country: int,
    min_per_country: int,
    seed: int,
    min_bytes: int = 20_000,
    max_bytes: int = 40_000_000,
) -> list[dict]:
    """権利 OK の中から、国ごとに上限まで無作為に採る。

    大きさで絞る理由(**偏るので、偏り方を書いておく**):
      Commons には「LP の片面まるごと」「1 時間の実演」のような長尺録音があり、
      最大 1,172 MB の音源が実在する(実測 2026-09-07)。全部取ると 5.4 GB になるうえ、
      1 本から数千セグメントが出て学習が**その 1 本に支配される**。
      上限を置くのは通信量の都合だけでなく、標本の偏りを抑えるためでもある。
      **その代わり長尺の演奏形式(組曲・語り物)が落ちる**。これは承知のうえの限定である。
      下限は、壊れた・実質空のファイルを避けるために置く。
    """
    usable = [r for r in records if r.get("rights_allowed") and r.get("url")]
    by_country: dict[str, list[dict]] = {}
    for r in usable:
        # 正規化した国名で束ねる。しないと 'Italy' と 'Italia' が別枠になり、
        # イタリアだけ上限の 2 倍取れてしまう(SPEC §5.4)
        r["country"] = canonical_country(r["country"])
        by_country.setdefault(r["country"], []).append(r)

    rng = random.Random(seed)
    chosen: list[dict] = []
    for country, rows in sorted(by_country.items()):
        if len(rows) < min_per_country:
            continue
        in_range = [
            r for r in rows if min_bytes <= (r.get("size") or 0) <= max_bytes
        ]
        if in_range:
            pool = sorted(in_range, key=lambda r: r["file"])  # 入力順に依存させない
            rng.shuffle(pool)
            picked = pool[:per_country]
        else:
            # **大きさを理由に国を落とさない。** 範囲内が一つも無い国は、
            # いちばん小さいものを 1 件だけ採り、そのことを記録する。
            # 国を落とすと地理の網が欠け、H-01 の標本が「取りやすかった国」に寄る。
            smallest = min(rows, key=lambda r: (r.get("size") or 0) or 1 << 62)
            smallest = {**smallest, "oversize_fallback": True}
            picked = [smallest]
        chosen += picked
    return sorted(chosen, key=lambda r: (r["country"], r["file"]))


def download(url: str, dest: Path, tries: int = 8) -> bool:
    """音源を 1 件取る。

    `upload.wikimedia.org` は API とは **別枠の、より厳しい**制限を持つ
    (実測 2026-09-07: 0.3 秒間隔で 6 件目から 429 が連続した)。
    429 は失敗ではなく「待て」の指示なので、`Retry-After` を読んで待ち、
    無ければ指数バックオフする。**429 を通常の例外と同じ短い再試行で扱わない。**
    """
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    backoff = 10.0
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=300) as r, open(dest, "wb") as f:
                while True:
                    b = r.read(1 << 16)
                    if not b:
                        break
                    f.write(b)
            return True
        except urllib.error.HTTPError as e:
            dest.unlink(missing_ok=True)
            if e.code == 429:
                ra = e.headers.get("Retry-After")
                wait = float(ra) if ra and str(ra).isdigit() else backoff
                print(f"    429 -> {wait:.0f}s 待機", flush=True)
                time.sleep(wait)
                backoff = min(backoff * 2, 300)
                continue
            if attempt == tries - 1:
                print(f"    FAIL[{e.code}] {url[:90]}", flush=True)
                return False
            time.sleep(backoff)
            backoff = min(backoff * 2, 120)
        except Exception as e:  # noqa: BLE001
            dest.unlink(missing_ok=True)
            if attempt == tries - 1:
                print(f"    FAIL {url[:90]}: {e}", flush=True)
                return False
            time.sleep(backoff)
            backoff = min(backoff * 2, 120)
    return False


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    ap = argparse.ArgumentParser()
    ap.add_argument("--inp", type=Path, default=root / "data" / "raw" / "metadata.json")
    ap.add_argument("--outdir", type=Path, default=root / "data" / "raw" / "audio")
    ap.add_argument("--out", type=Path, default=root / "data" / "raw" / "selected.json")
    ap.add_argument("--per-country", type=int, default=20)
    ap.add_argument("--min-per-country", type=int, default=2)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--min-bytes", type=int, default=20_000)
    ap.add_argument("--max-bytes", type=int, default=40_000_000)
    # upload.wikimedia.org は API より厳しい。既定を余裕のある間隔にする(HC-204)
    ap.add_argument("--delay", type=float, default=2.0)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    meta = json.loads(args.inp.read_text(encoding="utf-8"))
    chosen = select(
        meta["records"], args.per_country, args.min_per_country, args.seed,
        min_bytes=args.min_bytes, max_bytes=args.max_bytes,
    )
    total_bytes = sum(r.get("size") or 0 for r in chosen)
    print(f"選抜の合計サイズ: {total_bytes / 1e6:.1f} MB")

    by_country: dict[str, int] = {}
    for r in chosen:
        by_country[r["country"]] = by_country.get(r["country"], 0) + 1
    print(f"選抜: {len(chosen)} 件 / {len(by_country)} 国 "
          f"(国あたり上限 {args.per_country}、下限 {args.min_per_country})")
    for k, v in sorted(by_country.items(), key=lambda kv: -kv[1]):
        print(f"  {v:4d}  {k}")

    if args.dry_run:
        print("\n--dry-run のため取得しない")
        return 0

    args.outdir.mkdir(parents=True, exist_ok=True)
    out_records = []
    seen_sha: dict[str, str] = {}
    for i, r in enumerate(chosen, 1):
        fid = f"folk_{i:06d}"
        ext = Path(urllib.parse.urlparse(r["url"]).path).suffix.lower() or ".ogg"
        dest = args.outdir / f"{fid}{ext}"
        if not dest.exists():
            if not download(r["url"], dest):
                continue
            time.sleep(args.delay)
        sha = sha256_of(dest)
        if sha in seen_sha:
            # 仕様書 §82: SHA-256 で重複を検出する
            print(f"  重複のため除外: {r['file']}(= {seen_sha[sha]})", flush=True)
            dest.unlink(missing_ok=True)
            continue
        seen_sha[sha] = fid
        out_records.append({
            "id": fid,
            "path": str(dest.relative_to(root)).replace("\\", "/"),
            "sha256": sha,
            "bytes": dest.stat().st_size,
            "retrieval_date": time.strftime("%Y-%m-%d"),
            **r,
        })
        if i % 25 == 0:
            print(f"  {i}/{len(chosen)}", flush=True)

    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "per_country_cap": args.per_country,
        "min_per_country": args.min_per_country,
        "seed": args.seed,
        "selected": len(out_records),
        "records": out_records,
    }
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\n取得 {len(out_records)} 件 → {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
