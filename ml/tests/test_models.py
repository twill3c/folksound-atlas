"""test_models.py — 自作 CNN の形と、ラベル依存の分離(F-05 / G-04 / SPEC §8)。

期待値の出所(HC-016): **SPEC §8 / §14 の条項**(128 次元 Embedding、
入力は 128 メルビン × 時間フレーム)。学習結果の実測値ではない。

ここでいちばん大事なのは形ではなく、
**オートエンコーダが国ラベルを引数に取らないこと**である(G-04)。
「見ていない」を口約束ではなく、**署名で不可能にする**。
"""

from __future__ import annotations

import inspect

import pytest

torch = pytest.importorskip("torch")

from folksound.models import (  # noqa: E402
    EMBEDDING_DIM,
    N_MELS,
    FolkCNNAutoencoder,
    FolkCNNClassifier,
    embed,
)


@pytest.mark.unit
def test_embedding_dimension_matches_spec():
    assert EMBEDDING_DIM == 128  # SPEC §8 / 仕様書 §14
    assert N_MELS == 128         # SPEC §7


@pytest.mark.unit
def test_autoencoder_embedding_shape():
    m = FolkCNNAutoencoder()
    x = torch.randn(4, 1, N_MELS, 216)
    z = m.encode(x)
    assert z.shape == (4, EMBEDDING_DIM)


@pytest.mark.unit
def test_autoencoder_reconstructs_to_input_shape():
    """再構成が入力と同じ形に戻ること(損失が計算できる前提)。"""
    m = FolkCNNAutoencoder()
    x = torch.randn(2, 1, N_MELS, 216)
    out = m(x)
    assert out.shape == x.shape


@pytest.mark.unit
def test_autoencoder_accepts_variable_time_length():
    """時間長が変わっても Embedding は 128 次元のままであること。

    セグメントは 5 秒固定だが、端数や別設定でフレーム数は動く。
    大域プーリングが効いていることを外から確かめる。
    """
    m = FolkCNNAutoencoder()
    for t in (128, 216, 400):
        z = m.encode(torch.randn(1, 1, N_MELS, t))
        assert z.shape == (1, EMBEDDING_DIM), f"T={t} で {z.shape}"


@pytest.mark.unit
def test_classifier_outputs_one_logit_per_class():
    m = FolkCNNClassifier(n_classes=7)
    logits = m(torch.randn(3, 1, N_MELS, 216))
    assert logits.shape == (3, 7)


@pytest.mark.unit
def test_autoencoder_signature_cannot_take_labels():
    """G-04(循環の禁止)の要。

    「ラベルを見ていない」を**署名で不可能にする**。forward / encode に
    ラベルらしき引数が生えたら落ちる。口約束は時間が経つと破られるが、
    署名の検査は破られたときに必ず鳴る。
    """
    banned = {"y", "label", "labels", "country", "countries", "target", "targets"}
    for fn in (FolkCNNAutoencoder.forward, FolkCNNAutoencoder.encode):
        params = set(inspect.signature(fn).parameters) - {"self"}
        leaked = params & banned
        assert not leaked, f"{fn.__qualname__} がラベルを受け取っている: {leaked}"


@pytest.mark.unit
def test_classifier_is_the_one_that_takes_labels():
    """対照が対照として成り立つ前提(HC-079)。

    分類器の側は n_classes を必要とする —— つまり
    「ラベルを見た側」と「見ていない側」が実際に別物であることを固定する。
    """
    params = inspect.signature(FolkCNNClassifier.__init__).parameters
    assert "n_classes" in params
    ae_params = inspect.signature(FolkCNNAutoencoder.__init__).parameters
    assert "n_classes" not in ae_params


@pytest.mark.unit
def test_embed_returns_l2_normalized_vectors():
    """SPEC F-07 / 仕様書 §101: 比較の前に L2 正規化する。"""
    m = FolkCNNAutoencoder()
    x = torch.randn(5, 1, N_MELS, 216)
    z = embed(m, x)
    norms = z.norm(dim=1)
    assert torch.allclose(norms, torch.ones_like(norms), atol=1e-5)


@pytest.mark.unit
def test_embed_is_deterministic_in_eval_mode():
    """同じ入力に二度当てて同じ値が出ること(dropout 等が残っていない)。"""
    m = FolkCNNAutoencoder()
    x = torch.randn(3, 1, N_MELS, 216)
    a = embed(m, x)
    b = embed(m, x)
    assert torch.allclose(a, b, atol=1e-6)
