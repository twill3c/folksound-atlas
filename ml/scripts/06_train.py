"""06_train.py — 自作 CNN の学習(F-05 / SPEC §8 / G-03 / G-04)。

二つのモデルを **別々に** 学習する:

    self-ae-v1   オートエンコーダ。メルスペクトログラムの再構成だけで学習する。
                 **国ラベルを一度も読まない。** → 地理の主張に使える
    self-clf-v1  国分類器。ラベルを読む。 → 地理の主張には使えない(対照)

分割は **録音単位**(SPEC §9 / G-03)。同じ録音のセグメントが train と test に
またがらないことを、学習に入る前に `assert_no_recording_leak` で止める。
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Dataset

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from folksound.countries import canonical_country  # noqa: E402
from folksound.models import FolkCNNAutoencoder, FolkCNNClassifier  # noqa: E402
from folksound.split import assert_no_recording_leak, split_by_recording  # noqa: E402

MAX_SEGMENTS_PER_RECORDING = 12  # 長尺 1 本が学習を支配しないようにする


class MelSegments(Dataset):
    """セグメント 1 つ = 標本 1 つ。ラベルは **任意**。

    オートエンコーダ用に使うときは `labels=None` で作る。
    そうすれば、この Dataset からラベルを取り出す道がそもそも無い。
    """

    def __init__(self, items: list[dict], meldir: Path, labels: dict[str, int] | None):
        self.items = items
        self.meldir = meldir
        self.labels = labels
        self._cache: dict[str, np.ndarray] = {}

    def __len__(self) -> int:
        return len(self.items)

    def _mels(self, rid: str) -> np.ndarray:
        if rid not in self._cache:
            self._cache[rid] = np.load(self.meldir / f"{rid}.npz")["mels"]
        return self._cache[rid]

    def __getitem__(self, i: int):
        it = self.items[i]
        m = self._mels(it["recording_id"])[it["seg"]]
        # dB スケールを [0,1] 付近へ。ref=max で作っているので概ね [-80,0]
        x = torch.from_numpy(((m + 80.0) / 80.0).astype(np.float32)).unsqueeze(0)
        if self.labels is None:
            return x
        return x, self.labels[it["country"]]


def build_index(selected: list[dict], meldir: Path) -> list[dict]:
    items: list[dict] = []
    for r in selected:
        f = meldir / f"{r['id']}.npz"
        if not f.exists():
            continue
        n = int(np.load(f)["mels"].shape[0])
        for s in range(min(n, MAX_SEGMENTS_PER_RECORDING)):
            items.append({
                "segment_id": f"{r['id']}#{s}",
                "recording_id": r["id"],
                "seg": s,
                "country": canonical_country(r["country"]),
            })
    return items


def train_autoencoder(train_items, meldir, epochs, batch, lr, device) -> FolkCNNAutoencoder:
    """**ラベルを渡さない。** Dataset を labels=None で作るので、渡す道が無い。"""
    ds = MelSegments(train_items, meldir, labels=None)
    dl = DataLoader(ds, batch_size=batch, shuffle=True, num_workers=0)
    model = FolkCNNAutoencoder().to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    lossf = nn.MSELoss()
    model.train()
    for ep in range(epochs):
        tot, n = 0.0, 0
        for x in dl:
            x = x.to(device)
            opt.zero_grad()
            out = model(x)
            loss = lossf(out, x)
            loss.backward()
            opt.step()
            tot += float(loss.detach()) * x.size(0)
            n += x.size(0)
        print(f"  [AE] epoch {ep + 1}/{epochs}  recon MSE {tot / max(n, 1):.5f}", flush=True)
    return model


def train_classifier(train_items, val_items, meldir, labels, epochs, batch, lr, device):
    ds = MelSegments(train_items, meldir, labels=labels)
    dl = DataLoader(ds, batch_size=batch, shuffle=True, num_workers=0)
    vds = MelSegments(val_items, meldir, labels=labels)
    vdl = DataLoader(vds, batch_size=batch, shuffle=False, num_workers=0)

    model = FolkCNNClassifier(n_classes=len(labels)).to(device)
    opt = torch.optim.Adam(model.parameters(), lr=lr)
    lossf = nn.CrossEntropyLoss()
    for ep in range(epochs):
        model.train()
        tot, n = 0.0, 0
        for x, y in dl:
            x, y = x.to(device), y.to(device)
            opt.zero_grad()
            loss = lossf(model(x), y)
            loss.backward()
            opt.step()
            tot += float(loss.detach()) * x.size(0)
            n += x.size(0)
        model.eval()
        correct, seen = 0, 0
        with torch.no_grad():
            for x, y in vdl:
                pred = model(x.to(device)).argmax(1).cpu()
                correct += int((pred == y).sum())
                seen += y.numel()
        acc = correct / seen if seen else float("nan")
        print(f"  [CLF] epoch {ep + 1}/{epochs}  loss {tot / max(n, 1):.4f}  val acc {acc:.3f}",
              flush=True)
    return model, acc


def main() -> int:
    root = Path(__file__).resolve().parents[2]
    ap = argparse.ArgumentParser()
    ap.add_argument("--selected", type=Path, default=root / "data" / "raw" / "selected.json")
    ap.add_argument("--meldir", type=Path, default=root / "data" / "normalized" / "mels")
    ap.add_argument("--outdir", type=Path, default=root / "ml" / "models")
    # CPU 学習なので回数は控えめにする。実測 2026-09-08: この機で AE は 1 エポック
    # 5〜6 分かかり、12 エポックだと AE だけで 1 時間を超えた。
    # ここで作る Embedding は**空間どうしを見比べる**ためのもので、
    # 最高精度を狙うものではないため、回数を落として速さを取る。
    ap.add_argument("--epochs-ae", type=int, default=6)
    ap.add_argument("--epochs-clf", type=int, default=6)
    ap.add_argument("--batch", type=int, default=64)
    ap.add_argument("--lr", type=float, default=1.5e-3)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--threads", type=int, default=6)
    args = ap.parse_args()

    torch.manual_seed(args.seed)
    np.random.seed(args.seed)
    torch.set_num_threads(args.threads)
    device = "cpu"

    sel = json.loads(args.selected.read_text(encoding="utf-8"))["records"]
    items = build_index(sel, args.meldir)
    print(f"セグメント {len(items)} / 録音 {len({i['recording_id'] for i in items})}")

    splits = split_by_recording(items, seed=args.seed)
    # **学習に入る前に漏れで止める**(G-03)
    assert_no_recording_leak(splits)
    for k, v in splits.items():
        print(f"  {k}: {len(v)} セグメント / "
              f"{len({i['recording_id'] for i in v})} 録音")

    args.outdir.mkdir(parents=True, exist_ok=True)

    print("\n=== self-ae-v1(ラベルを見ない)===")
    ae = train_autoencoder(splits["train"], args.meldir,
                           args.epochs_ae, args.batch, args.lr, device)
    torch.save(ae.state_dict(), args.outdir / "self-ae-v1.pt")

    # 分類器は、train に 2 録音以上ある国だけを対象にする
    train_countries: dict[str, set] = {}
    for i in splits["train"]:
        train_countries.setdefault(i["country"], set()).add(i["recording_id"])
    usable = sorted(c for c, r in train_countries.items() if len(r) >= 2)
    labels = {c: k for k, c in enumerate(usable)}
    print(f"\n=== self-clf-v1(ラベルを見る)=== 対象 {len(labels)} 国")

    tr = [i for i in splits["train"] if i["country"] in labels]
    va = [i for i in splits["val"] if i["country"] in labels]
    clf, acc = train_classifier(tr, va, args.meldir, labels,
                                args.epochs_clf, args.batch, args.lr, device)
    torch.save(clf.state_dict(), args.outdir / "self-clf-v1.pt")

    meta = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "seed": args.seed,
        "max_segments_per_recording": MAX_SEGMENTS_PER_RECORDING,
        "segments": {k: len(v) for k, v in splits.items()},
        "recordings": {k: len({i["recording_id"] for i in v}) for k, v in splits.items()},
        "classifier_countries": usable,
        "classifier_val_accuracy": acc,
        "epochs": {"ae": args.epochs_ae, "clf": args.epochs_clf},
    }
    (args.outdir / "training.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nwrote {args.outdir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
