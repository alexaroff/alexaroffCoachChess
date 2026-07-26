#!/usr/bin/env python3
"""
Generate a synthetic dataset for Duolingo chess pieces from the existing templates.

Optimized for MacBook Air M2 8 GB RAM:
- processes one image at a time
- no heavy libraries (only Pillow + numpy)
- writes files immediately

Usage:
    python generate_synthetic_dataset.py

Output structure:
    dataset/
      wP/   wN/   wB/   wR/   wQ/   wK/
      bP/   bN/   bB/   bR/   bQ/   bK/
      empty/
"""

from __future__ import annotations

import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
OUTPUT_DIR = Path(__file__).resolve().parent / "dataset"

# How many augmented versions to create per source image
VARIANTS_PER_PIECE = 350          # 12 pieces × 350 ≈ 4200
VARIANTS_PER_EMPTY = 400          # 2 empties × 400 = 800
TARGET_SIZE = 64                  # final size of every sample

# Classes we care about
PIECE_NAMES = [
    "wP", "wN", "wB", "wR", "wQ", "wK",
    "bP", "bN", "bB", "bR", "bQ", "bK",
]
EMPTY_NAMES = ["empty_light", "empty_dark"]


def load_template(name: str) -> Image.Image:
    path = TEMPLATES_DIR / f"{name}.png"
    if not path.exists():
        raise FileNotFoundError(f"Template not found: {path}")
    img = Image.open(path).convert("RGB")
    if img.size != (TARGET_SIZE, TARGET_SIZE):
        img = img.resize((TARGET_SIZE, TARGET_SIZE), Image.Resampling.LANCZOS)
    return img


def random_augment(img: Image.Image) -> Image.Image:
    """Apply a random but realistic set of augmentations."""
    arr = np.array(img, dtype=np.float32)

    # 1. Small brightness / contrast jitter
    if random.random() < 0.85:
        brightness = random.uniform(0.75, 1.25)
        arr = np.clip(arr * brightness, 0, 255)

    if random.random() < 0.7:
        # simple contrast around mean
        mean = arr.mean()
        contrast = random.uniform(0.8, 1.25)
        arr = np.clip((arr - mean) * contrast + mean, 0, 255)

    # 2. Mild Gaussian-like noise
    if random.random() < 0.65:
        noise = np.random.normal(0, random.uniform(2.0, 9.0), arr.shape)
        arr = np.clip(arr + noise, 0, 255)

    img = Image.fromarray(arr.astype(np.uint8))

    # 3. Very small rotation (±4 degrees)
    if random.random() < 0.45:
        angle = random.uniform(-4.0, 4.0)
        img = img.rotate(angle, resample=Image.Resampling.BILINEAR, fillcolor=(30, 40, 50))

    # 4. Small random shift (simulate imperfect crop)
    if random.random() < 0.55:
        max_shift = 3
        dx = random.randint(-max_shift, max_shift)
        dy = random.randint(-max_shift, max_shift)
        img = img.transform(
            img.size,
            Image.AFFINE,
            (1, 0, dx, 0, 1, dy),
            resample=Image.Resampling.BILINEAR,
            fillcolor=(30, 40, 50),
        )

    # 5. Occasional light blur (animation / focus)
    if random.random() < 0.25:
        img = img.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.4, 1.1)))

    # 6. Occasional slight color temperature shift
    if random.random() < 0.3:
        enhancer = ImageEnhance.Color(img)
        img = enhancer.enhance(random.uniform(0.85, 1.15))

    return img


def generate_for_class(src_name: str, out_class: str, n_variants: int) -> None:
    out_dir = OUTPUT_DIR / out_class
    out_dir.mkdir(parents=True, exist_ok=True)

    base = load_template(src_name)
    print(f"  {src_name:12} → {out_class:8}  ({n_variants} variants)", end=" ", flush=True)

    for i in range(n_variants):
        aug = random_augment(base)
        aug.save(out_dir / f"{out_class}_{i:04d}.png", optimize=True)

        if (i + 1) % 50 == 0:
            print(".", end="", flush=True)

    print(" done")


def main() -> None:
    print("Generating synthetic Duolingo chess dataset")
    print(f"Templates : {TEMPLATES_DIR}")
    print(f"Output    : {OUTPUT_DIR}")
    print()

    if not TEMPLATES_DIR.exists():
        raise SystemExit(f"Templates folder not found: {TEMPLATES_DIR}")

    # Pieces
    for name in PIECE_NAMES:
        generate_for_class(name, name, VARIANTS_PER_PIECE)

    # Empty squares → single class "empty"
    for name in EMPTY_NAMES:
        generate_for_class(name, "empty", VARIANTS_PER_EMPTY)

    # Summary
    print("\nFinished.")
    total = 0
    for d in sorted(OUTPUT_DIR.iterdir()):
        if d.is_dir():
            count = len(list(d.glob("*.png")))
            total += count
            print(f"  {d.name:8} : {count}")
    print(f"\nTotal images: {total}")
    print(f"Size on disk : ~{total * 4 / 1024:.0f} MB (approximate)")


if __name__ == "__main__":
    main()
