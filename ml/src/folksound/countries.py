"""countries.py — 国名の正規化(SPEC §5.4)。

Commons のカテゴリ名は揺れる。同じ国が二つの名前で立つことがあるので、
集計・地図・地理距離の前に一つへ寄せる。

**別名を足してよいのは、そのカテゴリの中身を実際に開いて確かめたときだけである。**
題名の言語や語感からの推測で足してはならない(HC-012)。

確かめた記録:
    Italia -> Italy
        `Category:Folk songs of Italia` の中身を実際に見た(2026-09-07)。
        Bella ciao / Calabrisella / Cicerenella / Maremma amara / Uva fogarina /
        Porta Romana bella など、イタリアの民謡である。
        なお同カテゴリには「イタリアの曲をセルビアの楽団が演奏した録音」も含まれる。
        **カテゴリが表すのは曲の出自であって、演奏者や録音地ではない**(§注意)。
"""

from __future__ import annotations

# 実測で確かめた別名だけを置く。増やすときはテストのコメントに根拠を残すこと。
ALIASES: dict[str, str] = {
    "Italia": "Italy",
}

_ARTICLES = ("the ", "The ")


def canonical_country(name: str | None) -> str:
    """表示・集計に使う国名へ寄せる。

    (1) 前後の空白を落とす
    (2) 冠詞 'the ' を落とす('the United States' -> 'United States')
    (3) 別名表を当てる
    """
    if not name:
        return ""
    s = name.strip()
    for a in _ARTICLES:
        if s.startswith(a):
            s = s[len(a) :]
            break
    return ALIASES.get(s, s)
