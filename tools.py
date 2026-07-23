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
    Interactive region selection via transparent fullscreen overlay (Tkinter).

    User drags a rectangle over the chessboard.
    Returns Region in absolute screen coordinates, or None if cancelled (Esc / right-click).

    Notes for macOS:
    - Requires the app to have Accessibility + Screen Recording permissions.
    - On Retina displays Tkinter coordinates are in points; mss uses pixels.
      If the selected region is consistently offset/wrong size, we will add
      explicit scale handling in a later iteration.
    """
    try:
        import tkinter as tk
    except ImportError:
        print("[tools] tkinter is required for interactive region selection")
        return None

    result: list[Optional[Region]] = [None]

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)

    overlay = tk.Toplevel(root)
    overlay.attributes("-fullscreen", True)
    overlay.attributes("-alpha", 0.25)
    overlay.attributes("-topmost", True)
    overlay.configure(bg="black")
    overlay.focus_force()

    canvas = tk.Canvas(overlay, cursor="cross", bg="black", highlightthickness=0)
    canvas.pack(fill=tk.BOTH, expand=True)

    start_x = start_y = 0
    rect_id = None

    def on_press(event):
        nonlocal start_x, start_y, rect_id
        start_x, start_y = event.x, event.y
        if rect_id is not None:
            canvas.delete(rect_id)
        rect_id = canvas.create_rectangle(
            start_x, start_y, start_x, start_y,
            outline="#00ff88", width=2
        )

    def on_drag(event):
        if rect_id is not None:
            canvas.coords(rect_id, start_x, start_y, event.x, event.y)

    def on_release(event):
        nonlocal result
        if rect_id is None:
            return
        x1, y1 = start_x, start_y
        x2, y2 = event.x, event.y
        left = min(x1, x2)
        top = min(y1, y2)
        width = abs(x2 - x1)
        height = abs(y2 - y1)

        # Ignore tiny accidental clicks
        if width < 40 or height < 40:
            canvas.delete(rect_id)
            return

        result[0] = Region(left=left, top=top, width=width, height=height)
        overlay.destroy()
        root.destroy()

    def on_cancel(event=None):
        result[0] = None
        overlay.destroy()
        root.destroy()

    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<B1-Motion>", on_drag)
    canvas.bind("<ButtonRelease-1>", on_release)
    overlay.bind("<Escape>", on_cancel)
    overlay.bind("<Button-3>", on_cancel)  # right-click cancel

    # Instruction text
    canvas.create_text(
        overlay.winfo_screenwidth() // 2,
        40,
        text="Перетащите прямоугольник поверх доски  ·  Esc / ПКМ — отмена",
        fill="#00ff88",
        font=("Helvetica", 16, "bold"),
    )

    overlay.mainloop()
    return result[0]


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
