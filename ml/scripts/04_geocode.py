"""04_geocode.py — 国名に座標を与える(F-08 / SPEC §5.1 / 仕様書 §59)。

座標は **Wikidata の国エンティティの P625(coordinate location)** から取る。
自分で緯度経度を書かない —— 書いた瞬間、出所の言えない数が地図に載る。

重要な限定(仕様書 §59「位置が正確でないなら無理に一点へ固定しない」):
    ここで付く座標は **国の代表点**であって、録音された場所ではない。
    したがって `coordinate_precision` は `country_centroid` になる。
    録音地点そのものが分かる録音は今のところ扱わない。
    地理距離もこの代表点間の距離であり、その粒度を超える主張はしない。

名前の揺れ(Commons のカテゴリは "Italia" と "Italy"、"the United States" のように揺れる)は
**ラベルと別名の両方**で突き合わせ、それでも当たらないものは
`unmatched` として残す。**推測で埋めない。**

出力: data/raw/country_coords.json
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from folksound.countries import canonical_country  # noqa: E402

ENDPOINT = "https://query.wikidata.org/sparql"

# ラベル・別名の索引で当たらなかった国を、**根拠つきで**手当てする表。
# 推測で足してはならない。足すときは、その QID を実際に引いて
# ラベルと座標を目で見た事実をここに書くこと。
#
# China:
#   Commons のカテゴリは "Folk music of China" だが、Wikidata の Q148 のラベルは
#   "People's Republic of China" で、英語別名の索引からは当たらなかった。
#   2026-09-07 に Q148 を直接引き、ラベルが "People's Republic of China"、
#   P625 が Point(103.451944444 35.844722222) であることを確認した。
MANUAL_QIDS: dict[str, dict] = {
    "China": {
        "qid": "Q148",
        "label": "People's Republic of China",
        "lat": 35.844722222,
        "lon": 103.451944444,
        "note": "Q148 を直接引いて確認(2026-09-07)。索引はラベル差で当たらなかった",
    },
}
# Wikimedia の UA 方針(実在の連絡先を出す)。HC-204 / loop_001 の実測を参照。
UA = (
    "FolkSoundAtlas/0.1 "
    "(https://github.com/twill3c/folksound-atlas; research dataset builder) "
    "python-urllib"
)

# 国だけでなく、歴史的国家・地域も拾う(民謡のカテゴリには "Tibet" のような
# 主権国家でない地名も出る)。P31 の候補を広げ、どれで当たったかを残す。
QUERY = """
SELECT ?c ?cLabel ?alias ?coord WHERE {
  VALUES ?type { wd:Q6256 wd:Q3624078 wd:Q3024240 wd:Q1520223 wd:Q10864048 }
  ?c wdt:P31 ?type .
  ?c wdt:P625 ?coord .
  OPTIONAL { ?c skos:altLabel ?alias . FILTER(LANG(?alias) = "en") }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
"""


def sparql(query: str) -> dict:
    url = ENDPOINT + "?" + urllib.parse.urlencode({"query": query, "format": "json"})
    req = urllib.request.Request(
        url, headers={"User-Agent": UA, "Accept": "application/sparql-results+json"}
    )
    backoff = 5.0
    for attempt in range(4):
        try:
            with urllib.request.urlopen(req, timeout=180) as r:
                return json.load(r)
        except Exception as e:  # noqa: BLE001
            if attempt == 3:
                raise
            print(f"  retry ({e})", flush=True)
            time.sleep(backoff)
            backoff *= 2
    raise RuntimeError("unreachable")


def norm(s: str) -> str:
    """突き合わせ用の正規化。**表示には使わない。**"""
    s = s.strip().lower()
    s = re.sub(r"^(the|le|la|les|el)\s+", "", s)
    s = re.sub(r"[^a-z0-9]+", "", s)
    return s


def parse_point(p: str) -> tuple[float, float] | None:
    m = re.match(r"Point\(([-0-9.eE]+)\s+([-0-9.eE]+)\)", p)
    if not m:
        return None
    return float(m.group(2)), float(m.group(1))  # (lat, lon)


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    ap = argparse.ArgumentParser()
    ap.add_argument("--inp", type=Path, default=root / "data" / "raw" / "discovered.json")
    ap.add_argument("--out", type=Path,
                    default=root / "data" / "raw" / "country_coords.json")
    args = ap.parse_args()

    disc = json.loads(args.inp.read_text(encoding="utf-8"))
    # 正規化してから突き合わせる('Italia' -> 'Italy'、'the United States' -> 'United States')
    wanted = sorted(
        {canonical_country(f["country"]) for f in disc["files"] if f.get("country")}
    )
    print(f"突き合わせる国名(正規化後): {len(wanted)}", flush=True)

    print("Wikidata へ問い合わせ中 ...", flush=True)
    res = sparql(QUERY)
    rows = res["results"]["bindings"]
    print(f"  返答 {len(rows)} 行", flush=True)

    # 正規化キー -> 候補
    index: dict[str, dict] = {}
    for b in rows:
        qid = b["c"]["value"].rsplit("/", 1)[-1]
        label = b["cLabel"]["value"]
        pt = parse_point(b["coord"]["value"])
        if not pt:
            continue
        entry = {"qid": qid, "label": label, "lat": pt[0], "lon": pt[1]}
        for key in filter(None, [label, b.get("alias", {}).get("value")]):
            k = norm(key)
            # ラベル一致を別名一致より優先する
            if k not in index or (norm(label) == k and index[k]["label"] != label):
                index[k] = entry

    matched: dict[str, dict] = {}
    unmatched: list[str] = []
    for name in wanted:
        hit = index.get(norm(name))
        via = "wikidata_index"
        if not hit and name in MANUAL_QIDS:
            hit = MANUAL_QIDS[name]
            via = "manual_verified"
        if hit:
            matched[name] = {
                "qid": hit["qid"],
                "label": hit["label"],
                "lat": hit["lat"],
                "lon": hit["lon"],
                "matched_on": name,
                "matched_via": via,
                "coordinate_precision": "country_centroid",
                "source": "Wikidata P625",
                "source_url": f"https://www.wikidata.org/wiki/{hit['qid']}",
            }
        else:
            unmatched.append(name)

    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "source": "Wikidata SPARQL (P625 coordinate location)",
        "endpoint": ENDPOINT,
        "note": "座標は国の代表点であり、録音地点ではない(coordinate_precision=country_centroid)",
        "matched_count": len(matched),
        "unmatched": unmatched,
        "countries": matched,
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\n一致 {len(matched)} / {len(wanted)}")
    if unmatched:
        print(f"未一致 {len(unmatched)} 件(**推測で埋めない**。別名表を足すか、対象から外す):")
        for u in unmatched:
            print(f"  - {u}")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
