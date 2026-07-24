"""
alexaroffCoachChess — low-level tools.

Stable region selection for macOS Tahoe (two-click method).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
from PIL import Image

try:
    import mss
    HAS_MSS = True
except ImportError:
    HAS_MSS = False

try:
    import pyautogui
    pyautogui.FAILSAFE = True
    pyautogui.PAUSE = 0.03
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False


@dataclass
class Region:
    left: int
    top: int
    width: int
    height: int

    @property
    def right(self) -> int:
        return self.left + self.width

    @property
    def bottom(self) -> int:
        return self.top + self.height

    def as_tuple(self) -> Tuple[int, int, int, int]:
        return self.left, self.top, self.width, self.height

    def __repr__(self) -> str:
        return f"Region(left={self.left}, top={self.top}, w={self.width}, h={self.height})"


def get_screen_size() -> Tuple[int, int]:
    if HAS_PYAUTOGUI:
        return pyautogui.size()
    return 1920, 1080


def capture_region(region: Region) -> np.ndarray:
    if not HAS_MSS:
        raise RuntimeError("mss is required for screen capture")

    with mss.mss() as sct:
        monitor = {
            "left": region.left,
            "top": region.top,
            "width": region.width,
            "height": region.height,
        }
        shot = sct.grab(monitor)
        img = np.array(shot)[:, :, :3][:, :, ::-1]  # BGRA → RGB
        return img


def capture_region_pil(region: Region) -> Image.Image:
    return Image.fromarray(capture_region(region))


def click_at(x: int, y: int, button: str = "left", clicks: int = 1) -> None:
    if not HAS_PYAUTOGUI:
        raise RuntimeError("pyautogui is required")
    pyautogui.click(x=x, y=y, button=button, clicks=clicks)


def move_to(x: int, y: int, duration: float = 0.1) -> None:
    if not HAS_PYAUTOGUI:
        raise RuntimeError("pyautogui is required")
    pyautogui.moveTo(x, y, duration=duration)


def select_region_interactive() -> Optional[Region]:
    """
    Надёжный выбор области двумя кликами (без fullscreen Tk).
    Работает стабильно на macOS Tahoe + Retina.
    """
    if not HAS_PYAUTOGUI:
        print("[tools] pyautogui required")
        return None

    print("\n=== Выбор области доски ===")
    print("1. Наведи мышь на ЛЕВЫЙ ВЕРХНИЙ угол доски")
    print("   и нажми Enter в терминале...")
    input()
    x1, y1 = pyautogui.position()
    print(f"   Зафиксировано: ({x1}, {y1})")

    print("\n2. Наведи мышь на ПРАВЫЙ НИЖНИЙ угол доски")
    print("   и нажми Enter в терминале...")
    input()
    x2, y2 = pyautogui.position()
    print(f"   Зафиксировано: ({x2}, {y2})")

    left = min(x1, x2)
    top = min(y1, y2)
    width = abs(x2 - x1)
    height = abs(y2 - y1)

    if width < 120 or height < 120:
        print("Область слишком маленькая — отмена.")
        return None

    region = Region(left=left, top=top, width=width, height=height)
    print(f"\nОбласть выбрана: {region}")
    return region


def square_center(region: Region, file: int, rank: int, orientation: str = "white") -> Tuple[int, int]:
    sq = region.width // 8
    if orientation == "white":
        col = file
        row = 7 - rank
    else:
        col = 7 - file
        row = rank
    cx = region.left + col * sq + sq // 2
    cy = region.top + row * sq + sq // 2
    return cx, cy
