"""test_env.py — 実行環境の検査(T-000)。

この機はシェルの `VIRTUAL_ENV` が別プロジェクト(juchu-desk)を指したままになることがある
(HC-171)。別の venv で走ると、入っている依存も版も違うため、
**緑でも赤でも意味が無い**。テストの一番手前で、自分の venv で走っていることを固定する。

CI(GitHub Actions)では専用の `.venv` を作らず、ランナーの Python に直接入れる。
この漏れはこの機のシェルの問題なので、CI では venv の照合だけを外す。
依存が実在することの検査は CI でも走らせる。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.unit
def test_running_inside_this_projects_venv():
    if os.environ.get("CI"):
        pytest.skip("CI では専用の .venv を作らない(HC-171 の漏れはこの機のシェルの問題)")
    prefix = Path(sys.prefix).resolve()
    expected = (PROJECT_ROOT / ".venv").resolve()
    assert prefix == expected, (
        f"別の仮想環境で走っている。\n"
        f"  sys.prefix = {prefix}\n"
        f"  期待       = {expected}\n"
        f"HC-171: シェルの VIRTUAL_ENV が別プロジェクトを指していないか確かめること。"
    )


@pytest.mark.unit
def test_required_packages_are_importable():
    """出荷経路で使う依存が、この環境に実在すること(CI でも走らせる)。"""
    import importlib.util

    for mod in ("numpy", "scipy", "sklearn", "librosa", "soundfile", "umap", "torch"):
        assert importlib.util.find_spec(mod) is not None, f"{mod} が無い"
