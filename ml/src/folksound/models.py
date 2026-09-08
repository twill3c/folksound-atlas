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


def _block(cin: int, cout: int, stride: int = 1) -> nn.Sequential:
    return nn.Sequential(
        nn.Conv2d(cin, cout, kernel_size=3, padding=1, stride=stride),
        nn.BatchNorm2d(cout),
        nn.ReLU(inplace=True),
    )


# 各段のチャネル数。CPU で学習しきれる大きさにしてある。
#
# 実測 2026-09-08(この機 / torch 2.14.0+cpu / 6 スレッド):
#   最初は 32/64/128/128 で組んでいたが、前向きだけで 42 GFLOP/バッチ になり、
#   バッチ 64 で 1 ステップ 36.2 秒(encode だけで 19.7 秒)、1 エポック 22 分だった。
#   畳み込み自体は壊れていない(conv 32->64 @64x108 b16 で 0.210 秒 ≒ 11 GFLOPS)。
#   **単に設計が重すぎた。**
#   第 1 層に stride 2 を入れ、チャネルを半分にして約 1/16 に落とした。
#   ここで作る Embedding は「空間どうしを見比べる」ためのもので、
#   最高精度を狙うものではないので、この取り替えは目的を損なわない。
CHANNELS = (16, 32, 64, 64)


class _Encoder(nn.Module):
    """メルスペクトログラム -> 128 次元。

    時間長に依存しないよう、最後は**大域平均プーリング**で潰す。
    第 1 層で stride 2 を使い、いちばん高い解像度で厚い畳み込みをしない。
    """

    def __init__(self, dim: int = EMBEDDING_DIM) -> None:
        super().__init__()
        c1, c2, c3, c4 = CHANNELS
        self.net = nn.Sequential(
            _block(1, c1, stride=2),   # 128xT -> 64x(T/2)
            nn.MaxPool2d(2),           #       -> 32x(T/4)
            _block(c1, c2),
            nn.MaxPool2d(2),           #       -> 16x(T/8)
            _block(c2, c3),
            nn.MaxPool2d(2),           #       ->  8x(T/16)
            _block(c3, c4),
        )
        self.head = nn.Linear(c4, dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        h = self.net(x)
        h = F.adaptive_avg_pool2d(h, 1).flatten(1)
        return self.head(h)


class FolkCNNAutoencoder(nn.Module):
    """自己教師あり(再構成)の CNN。**国ラベルを受け取らない。**

    `forward` も `encode` も、引数は入力テンソルだけである。
    """

    # 復号は低い解像度で組み立ててから引き伸ばす。
    # 高い解像度で畳み込むと、符号化側と同じ理由で CPU に載らなくなる。
    DEC_ROWS = 16

    def __init__(self, dim: int = EMBEDDING_DIM) -> None:
        super().__init__()
        c1, c2, c3, c4 = CHANNELS
        self.encoder = _Encoder(dim)
        self.decoder_fc = nn.Linear(dim, c4 * self.DEC_ROWS)
        self.decoder = nn.Sequential(
            _block(c4, c3),
            _block(c3, c2),
            nn.Conv2d(c2, 1, kernel_size=3, padding=1),
        )

    def encode(self, x: torch.Tensor) -> torch.Tensor:
        return self.encoder(x)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        n, _, n_mels, t = x.shape
        c4 = CHANNELS[-1]
        z = self.encode(x)
        h = self.decoder_fc(z).view(n, c4, self.DEC_ROWS, 1)
        h = h.expand(-1, -1, -1, max(t // 16, 1))
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
