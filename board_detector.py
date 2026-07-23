"""
alexaroffCoachChess — board detection & orientation.

Given a screen Region that tightly contains a chessboard:
- Detect which side is at the bottom (white or black)
- (Stage 2) Extract current position as FEN / chess.Board

Stage 1: orientation heuristic implemented.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Optional, Tuple

import chess
import numpy as np

from tools import Region, capture_region, square_center

Orientation = Literal["white", "black"]  # who is at the bottom of the image


@dataclass
class BoardSnapshot:
    """Result of one detection cycle."""
    region: Region
    orientation: Orientation
    fen: Optional[str] = None
    board: Optional[chess.Board] = None
    confidence: float = 0.0


class BoardDetector:
    """
    Stateless (or lightly stateful) detector.

    Responsibility:
    - Given a fixed Region → determine orientation
    - Later: map the 8x8 grid of pixels to a chess.Board
    """

    def __init__(self, region: Optional[Region] = None):
        self.region = region
        self._last_orientation: Optional[Orientation] = None

    def set_region(self, region: Region) -> None:
        self.region = region
        self._last_orientation = None

    def detect_orientation(self, img: Optional[np.ndarray] = None) -> Orientation:
        """
        Determine whether white or black pieces are at the bottom of the region.

        Stage 1 heuristic (no templates / OpenCV):
        - Convert to grayscale luminance.
        - Compare average brightness of the bottom ~25% of the image
          vs the top ~25%.
        - White pieces are significantly lighter → if bottom is brighter,
          white is at the bottom.

        This works reliably on most common themes (chess.com, lichess, etc.)
        when the board contains pieces. Empty boards or very dark themes
        can be ambiguous — we will add a manual override later.
        """
        if self.region is None:
            raise RuntimeError("Region not set")

        if img is None:
            img = capture_region(self.region)

        if img.size == 0 or img.shape[0] < 16 or img.shape[1] < 16:
            orientation: Orientation = "white"
            self._last_orientation = orientation
            return orientation

        # Luminance (BT.601)
        # img is RGB uint8
        gray = (
            0.299 * img[:, :, 0].astype(np.float32)
            + 0.587 * img[:, :, 1].astype(np.float32)
            + 0.114 * img[:, :, 2].astype(np.float32)
        )

        h = gray.shape[0]
        band = max(h // 4, 8)

        bottom_mean = float(np.mean(gray[-band:, :]))
        top_mean = float(np.mean(gray[:band, :]))

        # Threshold: white side is usually 12–40 points brighter
        # when pieces are present.
        if bottom_mean > top_mean + 12:
            orientation = "white"
        elif top_mean > bottom_mean + 12:
            orientation = "black"
        else:
            # Ambiguous (empty board / unusual theme) → default to white
            orientation = "white"

        self._last_orientation = orientation
        return orientation

    def get_snapshot(self) -> BoardSnapshot:
        """
        Capture current region, detect orientation, (later) extract FEN.
        """
        if self.region is None:
            raise RuntimeError("Region not set")

        img = capture_region(self.region)
        orientation = self.detect_orientation(img)

        # Stage 2 will fill fen / board
        return BoardSnapshot(
            region=self.region,
            orientation=orientation,
            fen=None,
            board=None,
            confidence=0.0,
        )

    def pixel_to_square(self, x: int, y: int) -> Optional[chess.Square]:
        """
        Convert absolute screen pixel to chess.Square (0..63).
        Requires known orientation and that (x,y) is inside the region.
        """
        if self.region is None or self._last_orientation is None:
            return None
        # TODO Stage 1/2
        return None

    def square_to_pixel(self, square: chess.Square) -> Optional[Tuple[int, int]]:
        """
        Center of the given square in absolute screen coordinates.
        """
        if self.region is None or self._last_orientation is None:
            return None
        file = chess.square_file(square)
        rank = chess.square_rank(square)
        return square_center(self.region, file, rank, self._last_orientation)
