"""models.py — 自作 CNN(SPEC §8 / F-05 / 仕様書 §13–14)。

二つのモデルを **別のクラス**として持つ。これは設計上の要点である(SPEC §2.2 / G-04):

    FolkCNNAutoencoder  再構成のみで学習する。**国ラベルを引数に取らない。**
                        → 地理の主張に使ってよい
    FolkCNNClassifier   国を当てるように学習する。**ラベルを見る。**
                        → 地理の主張に使ってはならない(対照としてのみ表示)

「ラベルを見ていない」を注釈で約束すると、いずれ静かに破られる。
ここでは **署名にラベルを生やさない**ことで不可能にし、
`ml/tests/test_models.py` が署名そのものを検査する。
"""

from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F

N_MELS = 128         # SPEC §7
EMBEDDING_DIM = 128  # SPEC §8


def _block(cin: int, cout: int) -> nn.Sequential:
    return nn.Sequential(
        nn.Conv2d(cin, cout, kernel_size=3, padding=1),
        nn.BatchNorm2d(cout),
        nn.ReLU(inplace=True),
    )


class _Encoder(nn.Module):
    """メルスペクトログラム -> 128 次元。

    時間長に依存しないよう、最後は**大域平均プーリング**で潰す。
    """

    def __init__(self, dim: int = EMBEDDING_DIM) -> None:
        super().__init__()
        self.net = nn.Sequential(
            _block(1, 32),
            nn.MaxPool2d(2),
            _block(32, 64),
            nn.MaxPool2d(2),
            _block(64, 128),
            nn.MaxPool2d(2),
            _block(128, 128),
        )
        self.head = nn.Linear(128, dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.net(x)
        h = F.adaptive_avg_pool2d(h, 1).flatten(1)
        return self.head(h)


class FolkCNNAutoencoder(nn.Module):
    """自己教師あり(再構成)の CNN。**国ラベルを受け取らない。**

    `forward` も `encode` も、引数は入力テンソルだけである。
    """

    def __init__(self, dim: int = EMBEDDING_DIM) -> None:
        super().__init__()
        self.encoder = _Encoder(dim)
        self.decoder_fc = nn.Linear(dim, 128 * (N_MELS // 8))
        self.decoder = nn.Sequential(
            _block(128, 64),
            _block(64, 32),
            nn.Conv2d(32, 1, kernel_size=3, padding=1),
        )

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        return self.encoder(x)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        n, _, n_mels, t = x.shape
        z = self.encode(x)
        h = self.decoder_fc(z).view(n, 128, n_mels // 8, 1)
        h = h.expand(-1, -1, -1, max(t // 8, 1))
        h = self.decoder(h)
        return F.interpolate(h, size=(n_mels, t), mode="bilinear", align_corners=False)


class FolkCNNClassifier(nn.Module):
    """国を当てる CNN。**ラベルを見る側**であることを `n_classes` が示す。

    このモデルの Embedding は、国ごとに固まって当然である。
    その固まりを「地理と音響の一致」と読んではならない(SPEC §2.2)。
    """

    def __init__(self, n_classes: int, dim: int = EMBEDDING_DIM) -> None:
        super().__init__()
        self.encoder = _Encoder(dim)
        self.classifier = nn.Linear(dim, n_classes)

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        return self.encoder(x)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.classifier(self.encode(x))


@torch.no_grad()
def embed(model: nn.Module, x: torch.Tensor) -> torch.Tensor:
    """Embedding を取り、L2 正規化して返す(SPEC F-07 / 仕様書 §101)。

    コサイン類似度は L2 正規化した内積と一致するので、
    ここで一度だけ揃えておき、後段では正規化しない。
    """
    was_training = model.training
    model.eval()
    z = model.encode(x)
    z = F.normalize(z, p=2, dim=1)
    if was_training:
        model.train()
    return z
