"""02b_rights_summary.py — 権利判定の要約を作る(G-01 / G-02 の監査証跡)。

`metadata.json` は 6.8MB あり、そのまま commit すると履歴が重くなる。
いっぽう「何件を候補にし、どの表記で何件が通り、**何が落ちたか**」は残さなければ、
後から「なぜこの録音が載っていないのか」に答えられない。

そこで要約だけを commit する。**落ちたものは全件を名指しで残す**
(件数だけ残すと、落ちた理由の妥当性を後から検算できない)。

出力: data/raw/rights_summary.json
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from folksound.countries import canonical_country  # noqa: E402


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    ap = argparse.ArgumentParser()
    ap.add_argument("--inp", type=Path, default=root / "data" / "raw" / "metadata.json")
    ap.add_argument(
        "--out", type=Path, default=root / "data" / "raw" / "rights_summary.json"
    )
    args = ap.parse_args()

    d = json.loads(args.inp.read_text(encoding="utf-8"))
    recs = d["records"]

    fam = collections.Counter(r["rights_family"] for r in recs)
    labels = collections.Counter(
        (r.get("license_short") or "<none>") for r in recs if r["rights_allowed"]
    )
    by_country = collections.Counter(
        canonical_country(r["country"]) for r in recs if r["rights_allowed"]
    )
    uploaders = collections.Counter(
        (r.get("uploader") or "<none>") for r in recs if r["rights_allowed"]
    )

    rejected = [
        {
            "file": r["file"],
            "country": canonical_country(r["country"]),
            "license_short": r.get("license_short"),
            "license_machine": r.get("license_machine"),
            "family": r["rights_family"],
            "reason": r["rights_reason"],
        }
        for r in recs
        if not r["rights_allowed"]
    ]

    payload = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "source_file": args.inp.name,
        "total_candidates": len(recs),
        "allowed": sum(1 for r in recs if r["rights_allowed"]),
        "excluded": len(rejected),
        "family_counts": dict(fam.most_common()),
        "allowed_license_labels": dict(labels.most_common()),
        "allowed_by_country": dict(by_country.most_common()),
        # H-02(録音の出自による交絡)の材料。**表示には使わない。**
        "allowed_top_uploaders": dict(uploaders.most_common(15)),
        "distinct_uploaders": len(uploaders),
        "excluded_records": rejected,
    }
    args.out.write_text(
        json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    print(f"候補 {len(recs)} / 許可 {payload['allowed']} / 除外 {len(rejected)}")
    print("ライセンス族:", dict(fam.most_common()))
    print(f"許可された録音の投稿者数: {len(uploaders)}")
    print("投稿者の上位(交絡の材料):")
    for k, v in uploaders.most_common(8):
        print(f"  {v:6d}  {k}")
    print(f"\nwrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
