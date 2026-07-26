"""
alexaroffCoachChess — simple arrow overlay for Coach mode.

Transparent always-on-top window that draws a green/cyan arrow
from the best-move origin square to the destination square.

Note on click-through (macOS):
  Tk's -disabled is only a best-effort. True mouse event passthrough
  on modern macOS usually requires AppKit (NSWindow.ignoresMouseEvents).
  If clicks are blocked while the arrow is visible, the overlay is
  interfering — this is the first thing to verify in a live game.
"""

from __future__ import annotations

import tkinter as tk
from typing import Optional, Tuple

from tools import Region
from config import ARROW_COLOR, OVERLAY_LINE_WIDTH


def _rgb_to_hex(rgb: Tuple[int, int, int]) -> str:
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


DEFAULT_ARROW_COLOR = _rgb_to_hex(ARROW_COLOR)
DEFAULT_ARROW_WIDTH = OVERLAY_LINE_WIDTH


class ArrowOverlay:
    def __init__(self):
        self._root: Optional[tk.Toplevel] = None
        self._canvas: Optional[tk.Canvas] = None
        self._region: Optional[Region] = None
        self._visible = False

    def set_region(self, region: Region) -> None:
        self._region = region
        # Recreate window if region changed
        if self._root is not None:
            self.destroy()
        self._ensure_window()

    def _ensure_window(self) -> None:
        if self._root is not None:
            return
        if self._region is None:
            return

        # Create a borderless transparent window exactly over the board
        self._root = tk.Toplevel()
        self._root.title("Coach Arrow")
        self._root.geometry(
            f"{self._region.width}x{self._region.height}+{self._region.left}+{self._region.top}"
        )
        self._root.overrideredirect(True)
        self._root.attributes("-topmost", True)

        # Transparency (macOS prefers systemTransparent)
        try:
            self._root.attributes("-transparent", True)
            self._root.config(bg="systemTransparent")
        except Exception:
            self._root.config(bg="black")
            try:
                self._root.attributes("-alpha", 0.01)  # almost invisible background
            except Exception:
                pass

        self._canvas = tk.Canvas(
            self._root,
            width=self._region.width,
            height=self._region.height,
            highlightthickness=0,
            bg="systemTransparent",
        )
        self._canvas.pack(fill=tk.BOTH, expand=True)

        # Best-effort click-through.
        # On Windows -disabled works well.
        # On macOS it is unreliable; real solution needs AppKit.
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
        """
        from_xy / to_xy — absolute screen coordinates of square centers.
        """
        if self._region is None:
            return

        self._ensure_window()
        if self._root is None or self._canvas is None:
            return

        color = color or DEFAULT_ARROW_COLOR
        width = width or DEFAULT_ARROW_WIDTH

        # Convert absolute → relative to the overlay window
        x1 = from_xy[0] - self._region.left
        y1 = from_xy[1] - self._region.top
        x2 = to_xy[0] - self._region.left
        y2 = to_xy[1] - self._region.top

        self._canvas.delete("all")

        # Main line with arrow head
        self._canvas.create_line(
            x1, y1, x2, y2,
            fill=color,
            width=width,
            arrow=tk.LAST,
            arrowshape=(18, 22, 8),
            capstyle=tk.ROUND,
            smooth=True,
            tags="arrow",
        )

        # Small circle at origin
        r = max(6, width + 1)
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
