"""
alexaroffCoachChess — simple arrow overlay for Coach mode.

Transparent always-on-top window that draws a green arrow
from the best-move origin square to the destination square.
"""

from __future__ import annotations

import tkinter as tk
from typing import Optional, Tuple

from tools import Region


class ArrowOverlay:
    def __init__(self):
        self._root: Optional[tk.Toplevel] = None
        self._canvas: Optional[tk.Canvas] = None
        self._region: Optional[Region] = None
        self._visible = False

    def set_region(self, region: Region) -> None:
        self._region = region
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
        self._root.attributes("-transparent", True)
        self._root.config(bg="systemTransparent")

        try:
            # macOS specific transparency
            self._root.wm_attributes("-transparent", True)
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

        # Make clicks pass through (best effort)
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
        color: str = "#00FF88",
        width: int = 6,
    ) -> None:
        """
        from_xy / to_xy — absolute screen coordinates of square centers.
        """
        if self._region is None:
            return

        self._ensure_window()
        if self._root is None or self._canvas is None:
            return

        # Convert absolute → relative to the overlay window
        x1 = from_xy[0] - self._region.left
        y1 = from_xy[1] - self._region.top
        x2 = to_xy[0] - self._region.left
        y2 = to_xy[1] - self._region.top

        self._canvas.delete("all")

        # Main line
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
        r = 7
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
