"""
alexaroffCoachChess — simple arrow overlay for Coach mode.

Transparent always-on-top window that draws an arrow
from the best-move origin square to the destination square.

Transparency note (macOS + Homebrew Python):
  Full systemTransparent often fails and produces a solid black window.
  We therefore use a low window alpha + bright arrow as a reliable compromise.
  True click-through still requires AppKit (NSWindow.ignoresMouseEvents).
"""

from __future__ import annotations

import tkinter as tk
from typing import Optional, Tuple

from tools import Region
from config import ARROW_COLOR, OVERLAY_LINE_WIDTH


def _rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


DEFAULT_ARROW_COLOR = _rgb_to_hex(ARROW_COLOR)
DEFAULT_ARROW_WIDTH = max(6, OVERLAY_LINE_WIDTH)


class ArrowOverlay:
    def __init__(self):
        self._root: Optional[tk.Toplevel] = None
        self._canvas: Optional[tk.Canvas] = None
        self._region: Optional[Region] = None
        self._visible = False

    def set_region(self, region: Region) -> None:
        self._region = region
        if self._root is not None:
            self.destroy()
        self._ensure_window()

    def _ensure_window(self) -> None:
        if self._root is not None:
            return
        if self._region is None:
            return

        self._root = tk.Toplevel()
        self._root.title("Coach Arrow")
        self._root.geometry(
            f"{self._region.width}x{self._region.height}+{self._region.left}+{self._region.top}"
        )
        self._root.overrideredirect(True)
        self._root.attributes("-topmost", True)

        # --- Transparency strategy ---
        # 1. Try the modern transparent path
        # 2. Fallback to low alpha (this is what actually works on most
        #    Homebrew Python 3.12 + recent macOS setups)
        transparent_ok = False
        try:
            self._root.attributes("-transparent", True)
            self._root.config(bg="systemTransparent")
            transparent_ok = True
        except Exception:
            pass

        if not transparent_ok:
            # Reliable fallback: almost transparent window + bright arrow
            self._root.config(bg="black")
            try:
                self._root.attributes("-alpha", 0.18)
            except Exception:
                pass

        canvas_bg = "systemTransparent" if transparent_ok else "black"

        self._canvas = tk.Canvas(
            self._root,
            width=self._region.width,
            height=self._region.height,
            highlightthickness=0,
            bg=canvas_bg,
            bd=0,
        )
        self._canvas.pack(fill=tk.BOTH, expand=True)

        # Best-effort click-through (unreliable on macOS without AppKit)
        try:
            self._root.attributes("-disabled", True)
        except Exception:
            pass

        self._root.withdraw()
        self._visible = False

    def show_arrow(
        self,
        from_xy: Tuple[int, int],
        to_xy: Tuple[int, int],
        color: Optional[str] = None,
        width: Optional[int] = None,
    ) -> None:
        if self._region is None:
            return

        self._ensure_window()
        if self._root is None or self._canvas is None:
            return

        color = color or DEFAULT_ARROW_COLOR
        width = width or DEFAULT_ARROW_WIDTH

        # Absolute → relative to overlay
        x1 = from_xy[0] - self._region.left
        y1 = from_xy[1] - self._region.top
        x2 = to_xy[0] - self._region.left
        y2 = to_xy[1] - self._region.top

        self._canvas.delete("all")

        # Thick bright arrow so it stays visible even with low window alpha
        self._canvas.create_line(
            x1, y1, x2, y2,
            fill=color,
            width=width,
            arrow=tk.LAST,
            arrowshape=(20, 24, 9),
            capstyle=tk.ROUND,
            smooth=True,
            tags="arrow",
        )

        # Origin marker
        r = max(7, width + 2)
        self._canvas.create_oval(
            x1 - r, y1 - r, x1 + r, y1 + r,
            fill=color,
            outline="",
            tags="arrow",
        )

        self._root.deiconify()
        self._root.lift()
        self._visible = True

    def hide(self) -> None:
        if self._root is not None and self._visible:
            self._canvas.delete("all")
            self._root.withdraw()
            self._visible = False

    def destroy(self) -> None:
        if self._root is not None:
            try:
                self._root.destroy()
            except Exception:
                pass
            self._root = None
            self._canvas = None
            self._visible = False
