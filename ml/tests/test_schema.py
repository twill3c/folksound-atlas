"""test_schema.py — 配布 JSON が宣言したスキーマに適合するか(T-014 / G-05)。

`schemas/*.schema.json` は**宣言**であって、書いた時点では何も守っていない。
実際に当てて初めて検査になる(SPEC のゲート表と同じ性質 — HC-157)。

陽性対照も置く。壊した文書を同じ検証器に通し、**必ず落ちる**ことを確かめる。
落ちないなら、この検査は緑を返すだけの飾りである。
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

jsonschema = pytest.importorskip("jsonschema")

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "public" / "data"
SCHEMAS = ROOT / "schemas"

pytestmark = pytest.mark.validation


def load(p: Path):
    if not p.exists():
        pytest.skip(f"{p.name} がまだ無い")
    return json.loads(p.read_text(encoding="utf-8"))


def schema(name: str):
    return load(SCHEMAS / name)


def validate(doc, sch) -> None:
    jsonschema.validate(instance=doc, schema=sch)


def test_songs_json_matches_its_schema():
    validate(load(DATA / "songs.json"), schema("songs.schema.json"))


def test_models_json_matches_its_schema():
    validate(load(DATA / "models.json"), schema("models.schema.json"))


def test_derived_files_match_their_schemas():
    """features / embeddings / umap / similarity を `derived.schema.json` の
    該当定義に当てる。"""
    defs = schema("derived.schema.json")["$defs"]

    def sub(name: str) -> dict:
        # $defs 同士の参照を解決できるよう、$defs ごと持たせる
        return {**defs[name], "$defs": defs}

    validate(load(DATA / "features.json"), sub("features_file"))

    checked = 0
    for m in load(DATA / "models.json")["models"]:
        mid = m["model_id"]
        for fname, defname in (
            (f"umap_{mid}.json", "umap_file"),
            (f"pca_{mid}.json", "umap_file"),
            (f"similarity_{mid}.json", "similarity_file"),
        ):
            p = DATA / fname
            if not p.exists():
                continue
            validate(json.loads(p.read_text(encoding="utf-8")), sub(defname))
            checked += 1
    # 走査対象が空でないことを別に確かめる(HC-041)
    assert checked > 0, "派生ファイルが 1 つも無く、この検査は何も見ていない"


def test_schema_check_catches_a_broken_document():
    """陽性対照: 壊した文書を必ず落とすこと。

    (a) 必須フィールドを消す (b) 型を変える (c) 禁止された値を入れる
    の三通りで、検証器が実際に撃つことを確かめる。
    """
    doc = load(DATA / "songs.json")
    sch = schema("songs.schema.json")
    validate(doc, sch)  # 前提: 素のままなら通る

    # (a) 必須フィールドを消す
    a = copy.deepcopy(doc)
    a["songs"][0].pop("source_url")
    with pytest.raises(jsonschema.ValidationError):
        validate(a, sch)

    # (b) 型を変える
    b = copy.deepcopy(doc)
    b["songs"][0]["latitude"] = "35.0"
    with pytest.raises(jsonschema.ValidationError):
        validate(b, sch)

    # (c) 禁止された値(rights_verified は const true)
    c = copy.deepcopy(doc)
    c["songs"][0]["rights_verified"] = False
    with pytest.raises(jsonschema.ValidationError):
        validate(c, sch)


def test_models_schema_catches_label_inconsistency():
    """陽性対照: モデル台帳の型違反を落とすこと。"""
    doc = load(DATA / "models.json")
    sch = schema("models.schema.json")
    validate(doc, sch)

    bad = copy.deepcopy(doc)
    bad["models"][0].pop("saw_country_labels")
    with pytest.raises(jsonschema.ValidationError):
        validate(bad, sch)
