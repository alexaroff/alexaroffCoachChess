#!/usr/bin/env python3
"""
Train a piece classifier for Duolingo chess.

Stage 1: Train MobileNetV3-Small (teacher) on the synthetic dataset.
Stage 2: Distill knowledge into a tiny custom CNN (student).

Optimized for MacBook Air M2 8 GB RAM:
- small batch size
- limited num_workers
- uses MPS when available

Usage:
    python train_piece_classifier.py

Outputs:
    models/teacher_mobilenet_v3_small.pt
    models/student_tiny_cnn.pt
    models/class_names.json
"""

from __future__ import annotations

import json
import random
import time
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader, random_split
from torchvision import datasets, models, transforms

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
DATA_DIR = Path(__file__).resolve().parent / "dataset"
MODELS_DIR = Path(__file__).resolve().parent / "models"
MODELS_DIR.mkdir(exist_ok=True)

IMG_SIZE = 64
BATCH_SIZE = 32
NUM_WORKERS = 2
EPOCHS_TEACHER = 12
EPOCHS_STUDENT = 20
LR_TEACHER = 1e-3
LR_STUDENT = 1e-3
VAL_RATIO = 0.15
SEED = 42
TEMPERATURE = 3.0          # distillation temperature
ALPHA = 0.7                # weight of soft loss vs hard loss

CLASS_NAMES = [
    "bB", "bK", "bN", "bP", "bQ", "bR",
    "empty",
    "wB", "wK", "wN", "wP", "wQ", "wR",
]


def set_seed(seed: int = SEED) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def get_device() -> torch.device:
    if torch.backends.mps.is_available():
        return torch.device("mps")
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def get_transforms(train: bool = True):
    if train:
        return transforms.Compose([
            transforms.Resize((IMG_SIZE, IMG_SIZE)),
            transforms.RandomHorizontalFlip(p=0.15),
            transforms.ColorJitter(brightness=0.15, contrast=0.15, saturation=0.1),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406],
                                 std=[0.229, 0.224, 0.225]),
        ])
    return transforms.Compose([
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406],
                             std=[0.229, 0.224, 0.225]),
    ])


def create_dataloaders(device: torch.device):
    full_ds = datasets.ImageFolder(DATA_DIR, transform=get_transforms(train=True))

    # Make sure class order is stable and matches CLASS_NAMES as much as possible
    print("Classes found:", full_ds.classes)

    n_val = int(len(full_ds) * VAL_RATIO)
    n_train = len(full_ds) - n_val
    train_ds, val_ds = random_split(
        full_ds, [n_train, n_val],
        generator=torch.Generator().manual_seed(SEED)
    )

    # Validation should use eval transforms
    val_ds.dataset.transform = get_transforms(train=False)

    train_loader = DataLoader(
        train_ds, batch_size=BATCH_SIZE, shuffle=True,
        num_workers=NUM_WORKERS, pin_memory=False
    )
    val_loader = DataLoader(
        val_ds, batch_size=BATCH_SIZE, shuffle=False,
        num_workers=NUM_WORKERS, pin_memory=False
    )
    return train_loader, val_loader, full_ds.classes


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
def build_teacher(num_classes: int) -> nn.Module:
    model = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.DEFAULT)
    # Replace classifier head
    in_features = model.classifier[-1].in_features
    model.classifier[-1] = nn.Linear(in_features, num_classes)
    return model


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


# ---------------------------------------------------------------------------
# Training helpers
# ---------------------------------------------------------------------------
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


def train_one_epoch(model, loader, optimizer, criterion, device):
    model.train()
    total_loss = 0.0
    correct = total = 0
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        optimizer.zero_grad(set_to_none=True)
        logits = model(x)
        loss = criterion(logits, y)
        loss.backward()
        optimizer.step()

        total_loss += loss.item() * x.size(0)
        correct += (logits.argmax(1) == y).sum().item()
        total += x.size(0)
    return total_loss / total, correct / total


def distillation_loss(student_logits, teacher_logits, labels, temperature=TEMPERATURE, alpha=ALPHA):
    """Soft + hard loss."""
    soft_loss = F.kl_div(
        F.log_softmax(student_logits / temperature, dim=1),
        F.softmax(teacher_logits / temperature, dim=1),
        reduction="batchmean",
    ) * (temperature ** 2)
    hard_loss = F.cross_entropy(student_logits, labels)
    return alpha * soft_loss + (1.0 - alpha) * hard_loss


def train_teacher(device):
    print("\n===== STAGE 1: Training MobileNetV3-Small (Teacher) =====")
    train_loader, val_loader, classes = create_dataloaders(device)
    num_classes = len(classes)

    model = build_teacher(num_classes).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=LR_TEACHER, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS_TEACHER)
    criterion = nn.CrossEntropyLoss()

    best_acc = 0.0
    best_path = MODELS_DIR / "teacher_mobilenet_v3_small.pt"

    for epoch in range(1, EPOCHS_TEACHER + 1):
        t0 = time.time()
        train_loss, train_acc = train_one_epoch(model, train_loader, optimizer, criterion, device)
        val_acc = evaluate(model, val_loader, device)
        scheduler.step()
        dt = time.time() - t0

        print(f"Epoch {epoch:02d}/{EPOCHS_TEACHER}  "
              f"loss={train_loss:.4f}  train_acc={train_acc:.3f}  "
              f"val_acc={val_acc:.3f}  ({dt:.1f}s)")

        if val_acc > best_acc:
            best_acc = val_acc
            torch.save({
                "model_state": model.state_dict(),
                "classes": classes,
                "val_acc": val_acc,
            }, best_path)
            print(f"  → saved best teacher (val_acc={val_acc:.3f})")

    print(f"Teacher finished. Best val accuracy: {best_acc:.3f}")
    return best_path, classes


def train_student(teacher_path: Path, classes: list, device: torch.device):
    print("\n===== STAGE 2: Distilling into TinyCNN (Student) =====")
    train_loader, val_loader, _ = create_dataloaders(device)
    num_classes = len(classes)

    # Load frozen teacher
    teacher = build_teacher(num_classes).to(device)
    ckpt = torch.load(teacher_path, map_location=device, weights_only=False)
    teacher.load_state_dict(ckpt["model_state"])
    teacher.eval()
    for p in teacher.parameters():
        p.requires_grad = False

    student = TinyCNN(num_classes).to(device)
    optimizer = torch.optim.AdamW(student.parameters(), lr=LR_STUDENT, weight_decay=1e-4)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS_STUDENT)

    best_acc = 0.0
    best_path = MODELS_DIR / "student_tiny_cnn.pt"

    for epoch in range(1, EPOCHS_STUDENT + 1):
        t0 = time.time()
        student.train()
        total_loss = 0.0
        correct = total = 0

        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad(set_to_none=True)

            with torch.no_grad():
                teacher_logits = teacher(x)

            student_logits = student(x)
            loss = distillation_loss(student_logits, teacher_logits, y)

            loss.backward()
            optimizer.step()

            total_loss += loss.item() * x.size(0)
            correct += (student_logits.argmax(1) == y).sum().item()
            total += x.size(0)

        scheduler.step()
        train_acc = correct / total
        val_acc = evaluate(student, val_loader, device)
        dt = time.time() - t0

        print(f"Epoch {epoch:02d}/{EPOCHS_STUDENT}  "
              f"loss={total_loss/total:.4f}  train_acc={train_acc:.3f}  "
              f"val_acc={val_acc:.3f}  ({dt:.1f}s)")

        if val_acc > best_acc:
            best_acc = val_acc
            torch.save({
                "model_state": student.state_dict(),
                "classes": classes,
                "val_acc": val_acc,
            }, best_path)
            print(f"  → saved best student (val_acc={val_acc:.3f})")

    print(f"Student finished. Best val accuracy: {best_acc:.3f}")
    return best_path


def main():
    set_seed()
    device = get_device()
    print(f"Device: {device}")
    print(f"Dataset: {DATA_DIR}")

    if not DATA_DIR.exists():
        raise SystemExit(
            f"Dataset folder not found: {DATA_DIR}\n"
            "Run generate_synthetic_dataset.py first."
        )

    teacher_path, classes = train_teacher(device)

    # Save class names for later use in board_detector
    with open(MODELS_DIR / "class_names.json", "w") as f:
        json.dump(classes, f, indent=2)

    student_path = train_student(teacher_path, classes, device)

    print("\n===== DONE =====")
    print(f"Teacher : {teacher_path}")
    print(f"Student : {student_path}")
    print(f"Classes : {MODELS_DIR / 'class_names.json'}")
    print("\nNext step: integrate the student model into board_detector.py")


if __name__ == "__main__":
    main()
