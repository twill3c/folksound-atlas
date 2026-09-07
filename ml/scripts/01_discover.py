"""01_discover.py — Wikimedia Commons から民謡音源の候補を洗い出す。

地理帰属の出所は **カテゴリ所属のみ**(SPEC §5.1)。題名・演奏者名から推定しない。

なぜ `deepcat:` を使わないか(実測 2026-09-07 / HC-204):
    Commons の CirrusSearch には `deepcat:"<カテゴリ>"` という便利な演算子があり、
    カテゴリ木をサーバ側で展開してくれる。しかしこれは **誤りを黙って返す**。
    `deepcat:"Folk music of Ireland" filemime:audio` は totalhits=112 を返すが、
    その上位はスウェーデンの SMV 音源であり、当該ファイルの categories を直接引くと
    アイルランド系カテゴリに一切属していない。警告もエラーも出ない。
    したがって本スクリプトは `list=categorymembers` による明示的な所属だけを使い、
    さらに各ファイルについて「どの国カテゴリから、どの経路で到達したか」を残す。

出力: data/raw/discovered.json
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

API = "https://commons.wikimedia.org/w/api.php"
# Wikimedia の UA 方針(実在の連絡先を出す)。HC-204 / loop_001 の実測を参照。
UA = (
    "FolkSoundAtlas/0.1 "
    "(https://github.com/twill3c/folksound-atlas; research dataset builder) "
    "python-urllib"
)

AUDIO_EXT = (".ogg", ".oga", ".wav", ".flac", ".mp3", ".opus", ".m4a")

# 走査対象の国カテゴリを集める親カテゴリ
ROOTS = [
    "Category:Folk music by country",
    "Category:Traditional music by country",
    "Category:Folk songs by country",
]

# 到達しても降りないカテゴリ(保守用・横断的で、国の帰属を運ばない)。
# ここを降りるとカテゴリ・グラフの遠くへ迷い込み、別の国の音源を拾ってしまう。
SKIP_SUBSTRINGS = (
    "Files with",
    "Media contributed by",
    "Uploaded with",
    "CC-Zero",
    "CC-BY",
    "PD-",
    "Self-published",
    "Flickr",
    "Videos",
    "Sheet music",
    "Scores",
    "Images",
    "Photographs",
    "Musicians",
    "People",
    "Festivals",
    "Museums",
    "Logos",
    "Maps",
    "Stubs",
    "by year",
    "by date",
)


class Api:
    def __init__(self, delay: float = 0.4) -> None:
        self.delay = delay
        self.calls = 0

    def get(self, params: dict) -> dict:
        params["format"] = "json"
        url = API + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        backoff = 3.0
        for attempt in range(6):
            try:
                with urllib.request.urlopen(req, timeout=120) as r:
                    self.calls += 1
                    time.sleep(self.delay)
                    return json.load(r)
            except urllib.error.HTTPError as e:
                if e.code == 429:
                    ra = e.headers.get("Retry-After")
                    wait = float(ra) if ra and ra.isdigit() else backoff
                    print(f"    429 -> {wait}s", flush=True)
                    time.sleep(wait)
                    backoff = min(backoff * 2, 60)
                    continue
                if attempt == 5:
                    raise
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)
            except Exception:
                if attempt == 5:
                    raise
                time.sleep(backoff)
                backoff = min(backoff * 2, 60)
        raise RuntimeError("gave up")

    def members(self, cat: str, cmtype: str) -> list[str]:
        out: list[str] = []
        cont: dict = {}
        while True:
            p = {
                "action": "query",
                "list": "categorymembers",
                "cmtitle": cat,
                "cmtype": cmtype,
                "cmlimit": "500",
            }
            p.update(cont)
            r = self.get(p)
            out += [m["title"] for m in r.get("query", {}).get("categorymembers", [])]
            if "continue" in r:
                cont = r["continue"]
            else:
                return out


def should_skip(cat: str) -> bool:
    return any(s.lower() in cat.lower() for s in SKIP_SUBSTRINGS)


def country_of(cat: str) -> str | None:
    """'Category:Folk music of Sweden' -> 'Sweden'"""
    body = cat.replace("Category:", "")
    for kw in (" of ", " in ", " from "):
        if kw in body:
            return body.split(kw, 1)[1].strip()
    return None


def discover(api: Api, max_depth: int) -> dict:
    country_cats: list[str] = []
    for root in ROOTS:
        for c in api.members(root, "subcat"):
            if country_of(c) and not should_skip(c):
                country_cats.append(c)
    country_cats = sorted(set(country_cats))
    print(f"country categories: {len(country_cats)}", flush=True)

    # file title -> attribution record
    found: dict[str, dict] = {}
    visited: set[str] = set()

    def walk(cat: str, root_cat: str, path: list[str], depth: int) -> None:
        key = (cat, root_cat)
        if depth > max_depth or key in visited:
            return
        visited.add(key)
        try:
            for f in api.members(cat, "file"):
                if not f.lower().endswith(AUDIO_EXT):
                    continue
                if f not in found:
                    found[f] = {
                        "file": f,
                        "country": country_of(root_cat),
                        "country_source_category": root_cat,
                        "path": path + [cat],
                    }
            if depth < max_depth:
                for sub in api.members(cat, "subcat"):
                    if should_skip(sub):
                        continue
                    walk(sub, root_cat, path + [cat], depth + 1)
        except Exception as e:  # noqa: BLE001
            print(f"  ERR {cat}: {e}", flush=True)

    for i, c in enumerate(country_cats, 1):
        before = len(found)
        walk(c, c, [], 0)
        got = len(found) - before
        if got:
            print(f"  [{i}/{len(country_cats)}] +{got:4d}  {country_of(c)}", flush=True)

    return found


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-depth", type=int, default=2)
    ap.add_argument("--out", type=Path,
                    default=Path(__file__).resolve().parents[2] / "data" / "raw" / "discovered.json")
    ap.add_argument("--delay", type=float, default=0.4)
    args = ap.parse_args()

    api = Api(delay=args.delay)
    found = discover(api, args.max_depth)

    by_country: dict[str, int] = {}
    for rec in found.values():
        by_country[rec["country"]] = by_country.get(rec["country"], 0) + 1

    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "source": "Wikimedia Commons",
        "method": "list=categorymembers (deepcat is NOT used; see HC-204)",
        "max_depth": args.max_depth,
        "api_calls": api.calls,
        "counts_by_country": dict(sorted(by_country.items(), key=lambda kv: -kv[1])),
        "total_files": len(found),
        "files": sorted(found.values(), key=lambda r: r["file"]),
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\nTOTAL distinct audio files: {len(found)}")
    print(f"countries with >=1: {len(by_country)}")
    for k, v in sorted(by_country.items(), key=lambda kv: -kv[1])[:40]:
        print(f"  {v:5d}  {k}")
    print(f"\nwrote {args.out}  (api calls: {api.calls})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
