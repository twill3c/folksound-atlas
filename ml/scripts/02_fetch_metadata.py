"""02_fetch_metadata.py — 候補ファイルの権利・出自メタデータを引く(SPEC §5.2 / G-01 / G-02)。

`01_discover.py` が作った `data/raw/discovered.json` を読み、各ファイルについて
Commons の `imageinfo`(`extmetadata` 込み)を引いて、権利判定と出自の記録を作る。

**ここでは判定するだけで、選抜も取得もしない。** 判定の結果を全件残し、
落ちたものも理由つきで残す(捨てると、なぜ載っていないのかが後から言えなくなる)。

出力: data/raw/metadata.json
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from folksound.rights import classify_license  # noqa: E402

API = "https://commons.wikimedia.org/w/api.php"
UA = "FolkSoundAtlas/0.1 (research; contact via repo)"

IIPROP = "url|size|mime|user|extmetadata|mediatype"


def api_get(params: dict, tries: int = 6) -> dict:
    params["format"] = "json"
    req = urllib.request.Request(
        API + "?" + urllib.parse.urlencode(params), headers={"User-Agent": UA}
    )
    backoff = 3.0
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429:
                ra = e.headers.get("Retry-After")
                wait = float(ra) if ra and ra.isdigit() else backoff
                print(f"    429 -> {wait}s", flush=True)
                time.sleep(wait)
                backoff = min(backoff * 2, 60)
                continue
            if attempt == tries - 1:
                raise
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
        except Exception:
            if attempt == tries - 1:
                raise
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
    raise RuntimeError("gave up")


def _ext(md: dict, key: str) -> str | None:
    v = md.get(key)
    if isinstance(v, dict):
        val = v.get("value")
        return str(val) if val is not None else None
    return None


def _strip_html(s: str | None) -> str | None:
    if not s:
        return s
    import re

    return re.sub(r"<[^>]+>", "", s).strip() or None


def fetch_batch(titles: list[str]) -> dict[str, dict]:
    r = api_get(
        {
            "action": "query",
            "titles": "|".join(titles),
            "prop": "imageinfo",
            "iiprop": IIPROP,
            "iilimit": "1",
        }
    )
    out: dict[str, dict] = {}
    pages = r.get("query", {}).get("pages", {})
    for p in pages.values():
        title = p.get("title")
        ii = (p.get("imageinfo") or [{}])[0]
        md = ii.get("extmetadata") or {}
        out[title] = {
            "url": ii.get("url"),
            "size": ii.get("size"),
            "mime": ii.get("mime"),
            "mediatype": ii.get("mediatype"),
            "uploader": ii.get("user"),
            "license_short": _ext(md, "LicenseShortName"),
            "license_machine": _ext(md, "License"),
            "license_url": _ext(md, "LicenseUrl"),
            "usage_terms": _strip_html(_ext(md, "UsageTerms")),
            "artist": _strip_html(_ext(md, "Artist")),
            "credit": _strip_html(_ext(md, "Credit")),
            "date_original": _strip_html(_ext(md, "DateTimeOriginal")),
            "description": _strip_html(_ext(md, "ImageDescription")),
        }
    return out


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    ap = argparse.ArgumentParser()
    ap.add_argument("--inp", type=Path, default=root / "data" / "raw" / "discovered.json")
    ap.add_argument("--out", type=Path, default=root / "data" / "raw" / "metadata.json")
    ap.add_argument("--batch", type=int, default=50)
    ap.add_argument("--delay", type=float, default=0.4)
    ap.add_argument("--limit", type=int, default=0, help="0 なら全件")
    args = ap.parse_args()

    disc = json.loads(args.inp.read_text(encoding="utf-8"))
    files = disc["files"]
    if args.limit:
        files = files[: args.limit]
    by_title = {f["file"]: f for f in files}
    titles = list(by_title)
    print(f"metadata to fetch: {len(titles)}", flush=True)

    info: dict[str, dict] = {}
    for i in range(0, len(titles), args.batch):
        chunk = titles[i : i + args.batch]
        info.update(fetch_batch(chunk))
        print(f"  {min(i + args.batch, len(titles))}/{len(titles)}", flush=True)
        time.sleep(args.delay)

    records = []
    for t in titles:
        d = by_title[t]
        m = info.get(t, {})
        decision = classify_license(m.get("license_short"), m.get("license_machine"))
        records.append(
            {
                "file": t,
                "country": d["country"],
                "country_source_category": d["country_source_category"],
                "attribution_path": d["path"],
                **m,
                "rights_allowed": decision.allowed,
                "rights_family": decision.family,
                "rights_reason": decision.reason,
            }
        )

    allowed = [r for r in records if r["rights_allowed"]]
    by_country: dict[str, int] = {}
    for r in allowed:
        by_country[r["country"]] = by_country.get(r["country"], 0) + 1

    fam: dict[str, int] = {}
    for r in records:
        fam[r["rights_family"]] = fam.get(r["rights_family"], 0) + 1

    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "total_candidates": len(records),
        "rights_allowed": len(allowed),
        "rights_family_counts": fam,
        "allowed_counts_by_country": dict(
            sorted(by_country.items(), key=lambda kv: -kv[1])
        ),
        "records": records,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    print(f"\n候補 {len(records)} 件 / 権利 OK {len(allowed)} 件")
    print("ライセンス族の内訳:")
    for k, v in sorted(fam.items(), key=lambda kv: -kv[1]):
        print(f"  {v:6d}  {k}")
    print(f"\n権利 OK の国数: {len(by_country)}")
    for k, v in list(sorted(by_country.items(), key=lambda kv: -kv[1]))[:40]:
        print(f"  {v:6d}  {k}")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
