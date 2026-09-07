"""conftest.py — テスト実行時の環境固定。

torch のスレッド数を 1 にする。理由は速度ではなく **見分けが付くようにする**ためである。

実測(2026-09-07 / この機 / torch 2.14.0+cpu / Python 3.14.2):
    複数スレッドのまま Conv2d を前向きに通すと、呼ぶたびに faulthandler が
    "Windows fatal exception: access violation" を吐く。計算は完走し、値も正しい
    (独立に numpy で手計算した畳み込みと最大差 1.19e-7)。つまり first-chance 例外である。

害は無いが、**本物のクラッシュとまったく同じ見た目**になるのが困る。
テストでは 1 スレッドに固定して、この行が出たら本物だと分かるようにしておく。
**学習側では固定しない**(そちらは速度が要るので、この雑音は受け入れる)。
"""

from __future__ import annotations


def pytest_configure(config):  # noqa: ARG001
    try:
        import torch

        torch.set_num_threads(1)
    except Exception:
        pass
