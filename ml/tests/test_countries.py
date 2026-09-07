"""test_countries.py — 国名の正規化(SPEC §5.4 / §5.5)。

期待値の出所(HC-016):
  **実測 2026-09-07**。`data/raw/discovered.json` に現れた国名を目で見て、
  同じ国が二つの名前で立っている例を確かめてから別名表を書いた。
  `Category:Folk songs of Italia` の中身を実際に開き、Bella ciao / Calabrisella /
  Maremma amara / Uva fogarina などイタリアの民謡であることを確認している。
  **推測で足した別名は無い。**
"""

from __future__ import annotations

import pytest

from folksound.countries import ALIASES, canonical_country


@pytest.mark.unit
def test_italia_merges_into_italy():
    """実測で確かめた唯一の別名(SPEC §5.4)。"""
    assert canonical_country("Italia") == "Italy"
    assert canonical_country("Italy") == "Italy"


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw,want",
    [
        ("the United States", "United States"),
        ("the United Kingdom", "United Kingdom"),
        ("the Netherlands", "Netherlands"),
        ("the Philippines", "Philippines"),
    ],
)
def test_leading_article_is_dropped(raw, want):
    """Commons のカテゴリは 'the' を含む。表示名からは落とす。"""
    assert canonical_country(raw) == want


@pytest.mark.unit
@pytest.mark.parametrize("name", ["Japan", "Sweden", "Finland", "Nigeria", "Ivory Coast"])
def test_plain_names_pass_through_unchanged(name):
    """陰性対照: 触ってはいけないものを触っていないこと(HC-074)。"""
    assert canonical_country(name) == name


@pytest.mark.unit
def test_whitespace_is_trimmed():
    assert canonical_country("  Japan  ") == "Japan"


@pytest.mark.unit
def test_empty_stays_empty():
    assert canonical_country("") == ""
    assert canonical_country(None) == ""


@pytest.mark.unit
def test_alias_table_is_small_and_documented():
    """別名表が勝手に育っていないことを固定する。

    別名を足すのは「実物を見て確かめた」ときだけである。
    この検査は、確かめずに足す変更を目立たせるためにある。
    """
    assert len(ALIASES) <= 5, (
        "別名表が増えている。足すなら、その国のカテゴリの中身を実際に見て、"
        "確かめた事実を test のコメントに残すこと"
    )


@pytest.mark.unit
def test_canonicalization_is_idempotent():
    """二度掛けても変わらないこと(集計の途中で二重適用されうる)。"""
    for raw in ["Italia", "the United States", "Japan", ""]:
        once = canonical_country(raw)
        assert canonical_country(once) == once
