#!/usr/bin/env python3
"""
Train a tiny piece classifier for Duolingo chess (sandbox-friendly version).

Trains only the student TinyCNN from scratch (no MobileNet teacher / distillation)
to avoid torchvision weight / version issues in constrained environments.

Usage:
    python train_piece_classifier.py

Outputs:
    models/student_tiny_cnn.pt
    models/class_names.json
"""

from __future__ import annotations

import json
import random
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import Dataset, DataLoader, random_split
from PIL import Image

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parent / "dataset"
MODELS_DIR = Path(__file__).resolve().parent / "models"
MODELS_DIR.mkdir(exist_ok=True)

IMG_SIZE = 64
BATCH_SIZE = 32
NUM_WORKERS = 0
EPOCHS = 15
LR = 1e-3
VAL_RATIO = 0.15
SEED = 42

CLASS_NAMES = [
    "bB", "bK", "bN", "bP", "bQ", "bR",
    "empty",
    "wB", "wK", "wN", "wP", "wQ", "wR",
]


def set_seed(seed: int = SEED) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def get_device() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


class PieceDataset(Dataset):
    def __init__(self, root: Path, train: bool = True):
        self.samples = []
        self.classes = sorted([d.name for d in root.iterdir() if d.is_dir()])
        self.class_to_idx = {c: i for i, c in enumerate(self.classes)}
        for cls in self.classes:
            for p in (root / cls).glob("*.png"):
                self.samples.append((p, self.class_to_idx[cls]))
        self.train = train

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        img = Image.open(path).convert("RGB")
        img = img.resize((IMG_SIZE, IMG_SIZE), Image.Resampling.LANCZOS)
        arr = np.array(img, dtype=np.float32) / 255.0

        if self.train:
            # simple augmentations
            if random.random() < 0.3:
                arr = np.fliplr(arr).copy()
            # brightness
            if random.random() < 0.5:
                factor = random.uniform(0.85, 1.15)
                arr = np.clip(arr * factor, 0, 1)
            # slight noise
            if random.random() < 0.4:
                arr = np.clip(arr + np.random.normal(0, 0.02, arr.shape), 0, 1)

        # ImageNet-style normalize
        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        arr = (arr - mean) / std
        arr = arr.transpose(2, 0, 1)  # HWC -> CHW
        return torch.from_numpy(arr), label


class TinyCNN(nn.Module):
    """Very small CNN tailored for 64x64 chess pieces."""

    def __init__(self, num_classes: int = 13):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 24, 3, padding=1, bias=False),
            nn.BatchNorm2d(24),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),                    # 32x32

            nn.Conv2d(24, 48, 3, padding=1, bias=False),
            nn.BatchNorm2d(48),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),                    # 16x16

            nn.Conv2d(48, 72, 3, padding=1, bias=False),
            nn.BatchNorm2d(72),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),                    # 8x8

            nn.Conv2d(72, 96, 3, padding=1, bias=False),
            nn.BatchNorm2d(96),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d(1),            # 1x1
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(0.25),
            nn.Linear(96, num_classes),
        )

    def forward(self, x):
        x = self.features(x)
        return self.classifier(x)


@torch.no_grad()
def evaluate(model: nn.Module, loader: DataLoader, device: torch.device) -> float:
    model.eval()
    correct = total = 0
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        pred = model(x).argmax(dim=1)
        correct += (pred == y).sum().item()
        total += y.size(0)
    return correct / total if total else 0.0


def main():
    set_seed()
    device = get_device()
    print(f"Device: {device}")
    print(f"Dataset: {DATA_DIR}")

    if not DATA_DIR.exists():
        raise SystemExit(f"Dataset folder not found: {DATA_DIR}")

    full_ds = PieceDataset(DATA_DIR, train=True)
    classes = full_ds.classes
    print("Classes found:", classes)
    print(f"Total samples: {len(full_ds)}")

    n_val = int(len(full_ds) * VAL_RATIO)
    n_train = len(full_ds) - n_val
    train_ds, val_ds = random_split(
        full_ds, [n_train, n_val],
        generator=torch.Generator().manual_seed(SEED)
    )
    # val without augment
    val_ds.dataset.train = False

    train_loader = DataLoader(train_ds, batch_size=BATCH_SIZE, shuffle=True, num_workers=NUM_WORKERS)
    val_loader = DataLoader(val_ds, batch_size=BATCH_SIZE, shuffle=False, num_workers=NUM_WORKERS)

    model = TinyCNN(len(classes)).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)
    criterion = nn.CrossEntropyLoss()

    best_acc = 0.0
    best_path = MODELS_DIR / "student_tiny_cnn.pt"

    print("\n===== Training TinyCNN =====")
    for epoch in range(1, EPOCHS + 1):
        t0 = time.time()
        model.train()
        total_loss = 0.0
        correct = total = 0
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad(set_to_none=True)
            logits = model(x)
            loss = criterion(logits, y)
            loss.backward()
            optimizer.step()
            total_loss += loss.item() * x.size(0)
            correct += (logits.argmax(1) == y).sum().item()
            total += x.size(0)
        scheduler.step()
        train_acc = correct / total
        val_acc = evaluate(model, val_loader, device)
        dt = time.time() - t0
        print(f"Epoch {epoch:02d}/{EPOCHS}  loss={total_loss/total:.4f}  "
              f"train_acc={train_acc:.3f}  val_acc={val_acc:.3f}  ({dt:.1f}s)")
        if val_acc > best_acc:
            best_acc = val_acc
            torch.save({
                "model_state": model.state_dict(),
                "classes": classes,
                "val_acc": val_acc,
            }, best_path)
            print(f"  → saved best (val_acc={val_acc:.3f})")

    # also save class_names.json
    with open(MODELS_DIR / "class_names.json", "w") as f:
        json.dump(classes, f, indent=2)

    print(f"\n===== DONE =====")
    print(f"Best val accuracy: {best_acc:.3f}")
    print(f"Model: {best_path}")
    print(f"Classes: {MODELS_DIR / 'class_names.json'}")
    print("\nNext step: integrate the student model into board_detector.py")


if __name__ == "__main__":
    main()
