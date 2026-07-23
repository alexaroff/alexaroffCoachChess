"""
alexaroffCoachChess — low-level tools.

Screen capture, region selection, mouse control.
Platform: primarily macOS (Screen Recording + Accessibility permissions required).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional, Tuple

import numpy as np
from PIL import Image

# Optional imports — will be used when packages are installed
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
    """Screen region in absolute pixels (macOS global coordinates)."""
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
    """Return primary screen (width, height)."""
    if HAS_PYAUTOGUI:
        return pyautogui.size()
    # Fallback
    return 1920, 1080


def capture_region(region: Region) -> np.ndarray:
    """
    Capture the given screen region.
    Returns RGB numpy array (H, W, 3), dtype=uint8.
    """
    if not HAS_MSS:
        raise RuntimeError("mss is required for screen capture. Install: pip install mss")

    with mss.mss() as sct:
        monitor = {
            "left": region.left,
            "top": region.top,
            "width": region.width,
            "height": region.height,
        }
        shot = sct.grab(monitor)
        # mss returns BGRA
        img = np.array(shot)[:, :, :3]  # drop alpha
        img = img[:, :, ::-1]  # BGR -> RGB
        return img


def capture_region_pil(region: Region) -> Image.Image:
    """Same as capture_region but returns PIL Image (RGB)."""
    arr = capture_region(region)
    return Image.fromarray(arr)


def click_at(x: int, y: int, button: str = "left", clicks: int = 1) -> None:
    """Simulate mouse click at absolute screen coordinates."""
    if not HAS_PYAUTOGUI:
        raise RuntimeError("pyautogui is required for mouse control")
    pyautogui.click(x=x, y=y, button=button, clicks=clicks)


def move_to(x: int, y: int, duration: float = 0.1) -> None:
    """Move mouse to absolute coordinates."""
    if not HAS_PYAUTOGUI:
        raise RuntimeError("pyautogui is required for mouse control")
    pyautogui.moveTo(x, y, duration=duration)


def select_region_interactive() -> Optional[Region]:
    """
    Interactive region selection (Stage 1 implementation).

    Placeholder: currently returns None.
    Real implementation will use a transparent fullscreen overlay
    where user drags a rectangle over the chessboard.
    """
    # TODO Stage 1: implement drag-select overlay (tkinter or quartz)
    print("[tools] select_region_interactive() — not implemented yet (Stage 1)")
    return None


# ---------------------------------------------------------------------------
# Convenience helpers for board squares (used later by coach)
# ---------------------------------------------------------------------------

def square_center(region: Region, file: int, rank: int, orientation: str = "white") -> Tuple[int, int]:
    """
    Absolute screen coordinates of the center of a chess square.

    file, rank: 0..7 (file 0 = a, rank 0 = 1st rank in standard chess notation).
    orientation:
      "white" — white pieces at the bottom of the captured region
      "black" — black pieces at the bottom of the captured region
    """
    sq = region.width // 8
    # Image row 0 = top of region
    if orientation == "white":
        # white at bottom → rank 0 at bottom of image
        col = file
        row = 7 - rank
    else:
        # black at bottom → board is rotated 180°
        col = 7 - file
        row = rank

    cx = region.left + col * sq + sq // 2
    cy = region.top + row * sq + sq // 2
    return cx, cy
