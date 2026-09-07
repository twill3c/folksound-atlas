"""rights.py — 権利ゲート(SPEC §5.2 / G-01)。

方針は「許可リスト方式」である。**判定できないものは通さない。**
判定不能を `unknown` として黙って通すと、権利未確認の音源が公開データセットに混ざる。
未知の表記が出たら、それは「新しいライセンス表記を人が見て許可リストへ足す」合図であって、
実装が推測で埋める場所ではない。

Commons の `extmetadata` は少なくとも次を返しうる:
    LicenseShortName : 人間向け表示(例 "CC BY-SA 4.0", "Public domain", "CC0")
    License          : 機械向けの短縮形(例 "cc-by-sa-4.0", "pd", "cc0")
    UsageTerms       : 利用条件の文
両方が欠けることもあるので、**欠けている場合は不許可**とする。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# --- 許可する族 -------------------------------------------------------------
# 民謡の音響特徴量を抽出する行為は「改変」を含みうるため ND(改変禁止)は採らない。
# 本アプリは研究・教育目的だが、NC(非営利限定)は再利用条件を狭めるため採らない。
# これは SPEC §5.2 の決定であり、ここを緩めるときは SPEC を先に変える。

_PD_PATTERNS = (
    r"^public\s*domain$",
    r"^pd$",
    r"^pd[-_ ]",
    r"^public\s*domain[-_ ]",
    r"^cc0$",
    r"^cc[-\s]?zero$",
    r"^cc0\s*1\.0",
)

# 版のあとに法域の移植版(ported)を示す 2 文字の国コードが付くことがある。
# 実測 2026-09-07: Commons の 5,492 件に 'CC BY 3.0 us' / 'CC BY-SA 2.0 de' /
# 'CC BY-SA 3.0 cl' が現れた。これらは CC BY / CC BY-SA そのものなので通す。
# **NC/ND の移植版まで通さないよう、拒否リストを先に評価する順序は変えない。**
_CC_ALLOWED = (
    r"^cc[-\s]?by(?:[-\s]?sa)?(?:[-\s]?\d(?:\.\d)?)?(?:[-\s]?[a-z]{2})?$",
)

# 明示的に拒否する族(見つけたら即座に不許可。許可判定より先に評価する)
_DENY_PATTERNS = (
    r"\bnc\b",          # NonCommercial
    r"noncommercial",
    r"\bnd\b",          # NoDerivatives
    r"noderiv",
    r"fair\s*use",
    r"non[-\s]?free",
    r"copyright",
    r"all\s*rights\s*reserved",
    r"gfdl",            # 単体の GFDL は再利用条件が重いので本件では採らない
)


@dataclass(frozen=True)
class RightsDecision:
    allowed: bool
    license_label: str
    family: str          # "public_domain" | "cc_by" | "cc_by_sa" | "rejected" | "unknown"
    reason: str


def _norm(s: str | None) -> str:
    if not s:
        return ""
    s = s.strip().lower()
    s = re.sub(r"\s+", " ", s)
    # "CC BY-SA 4.0 International" -> 末尾の語を落とす前に判定するので、ここでは削らない
    return s


def classify_license(short_name: str | None, machine: str | None = None) -> RightsDecision:
    """ライセンス表記から可否を決める。

    引数はどちらも欠けうる。**両方欠けたら不許可**(SPEC §5.2)。
    """
    raw_short = (short_name or "").strip()
    raw_machine = (machine or "").strip()
    if not raw_short and not raw_machine:
        return RightsDecision(False, "", "unknown", "ライセンス表記が無い")

    label = raw_short or raw_machine

    for cand in (_norm(raw_machine), _norm(raw_short)):
        if not cand:
            continue
        # 拒否を先に見る(例 "CC BY-NC-SA 4.0" は by も sa も含むが不許可)
        for pat in _DENY_PATTERNS:
            if re.search(pat, cand):
                return RightsDecision(
                    False, label, "rejected", f"禁止パターンに一致: {pat}"
                )

    # 版・国際表記の語尾を落として族を見る
    def core(s: str) -> str:
        s = re.sub(r"\b(international|unported|generic|deed|license|licence)\b", "", s)
        s = re.sub(r"[()]", " ", s)
        return re.sub(r"\s+", " ", s).strip()

    for cand in (_norm(raw_machine), _norm(raw_short)):
        if not cand:
            continue
        c = core(cand)
        for pat in _PD_PATTERNS:
            if re.match(pat, c):
                return RightsDecision(True, label, "public_domain", f"PD 系: {c}")
        for pat in _CC_ALLOWED:
            if re.match(pat, c):
                fam = "cc_by_sa" if re.search(r"sa", c) else "cc_by"
                return RightsDecision(True, label, fam, f"CC 許可系: {c}")

    return RightsDecision(
        False, label, "unknown",
        f"許可リストに無い表記: {label!r}(人が確認して許可リストへ足すこと)",
    )
