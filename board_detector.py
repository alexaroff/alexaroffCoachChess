"""
alexaroffCoachChess — board detection & orientation + position recognition.

Given a screen Region that tightly contains a chessboard:
- Detect which side is at the bottom (white or black)
- Extract current position as FEN / chess.Board (Stage 2)

Stage 2: occupancy + color side + basic piece type estimation.
Templates can be added later for higher accuracy.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Literal, Optional, Tuple, List

import chess
import numpy as np

from tools import Region, capture_region, square_center

log = logging.getLogger(__name__)

Orientation = Literal["white", "black"]  # who is at the bottom of the image


@dataclass
class BoardSnapshot:
    """Result of one detection cycle."""
    region: Region
    orientation: Orientation
    fen: Optional[str] = None
    board: Optional[chess.Board] = None
    confidence: float = 0.0
    # debug info
    occupied_count: int = 0


class BoardDetector:
    """
    Detector responsible for:
    - orientation
    - turning a screen region into a chess.Board (FEN)
    """

    def __init__(self, region: Optional[Region] = None):
        self.region = region
        self._last_orientation: Optional[Orientation] = None
        self._last_img: Optional[np.ndarray] = None

    def set_region(self, region: Region) -> None:
        self.region = region
        self._last_orientation = None
        self._last_img = None

    # ------------------------------------------------------------------
    # Orientation (Stage 1)
    # ------------------------------------------------------------------

    def detect_orientation(self, img: Optional[np.ndarray] = None) -> Orientation:
        """
        Determine whether white or black pieces are at the bottom of the region.

        Heuristic: compare average luminance of bottom vs top bands.
        White pieces are lighter → brighter band = white side.
        """
        if self.region is None:
            raise RuntimeError("Region not set")

        if img is None:
            img = capture_region(self.region)

        if img.size == 0 or img.shape[0] < 16 or img.shape[1] < 16:
            orientation: Orientation = "white"
            self._last_orientation = orientation
            return orientation

        gray = self._luminance(img)
        h = gray.shape[0]
        band = max(h // 4, 8)

        bottom_mean = float(np.mean(gray[-band:, :]))
        top_mean = float(np.mean(gray[:band, :]))

        if bottom_mean > top_mean + 12:
            orientation = "white"
        elif top_mean > bottom_mean + 12:
            orientation = "black"
        else:
            orientation = "white"  # ambiguous → default

        self._last_orientation = orientation
        return orientation

    # ------------------------------------------------------------------
    # Position recognition (Stage 2)
    # ------------------------------------------------------------------

    def get_snapshot(self) -> BoardSnapshot:
        """
        Capture current region → orientation → FEN / chess.Board.
        """
        if self.region is None:
            raise RuntimeError("Region not set")

        img = capture_region(self.region)
        self._last_img = img
        orientation = self.detect_orientation(img)

        board, confidence, occupied = self._img_to_board(img, orientation)

        fen = board.fen() if board is not None else None

        return BoardSnapshot(
            region=self.region,
            orientation=orientation,
            fen=fen,
            board=board,
            confidence=confidence,
            occupied_count=occupied,
        )

    def _img_to_board(
        self,
        img: np.ndarray,
        orientation: Orientation,
    ) -> Tuple[Optional[chess.Board], float, int]:
        """
        Convert the board image into a chess.Board.

        Returns (board, average_confidence, occupied_squares_count).
        """
        h, w = img.shape[:2]
        if h < 64 or w < 64:
            log.warning("Board region too small: %dx%d", w, h)
            return None, 0.0, 0

        # Assume tight crop. Use the smaller side to keep squares square.
        size = min(h, w)
        sq = size // 8
        if sq < 12:
            log.warning("Square size too small: %d px", sq)
            return None, 0.0, 0

        # Center the 8x8 grid inside the image
        offset_x = (w - size) // 2
        offset_y = (h - size) // 2

        board = chess.Board(None)  # empty board
        confidences: List[float] = []
        occupied = 0

        for rank_idx in range(8):          # 0 = rank 1 (bottom from white's view)
            for file_idx in range(8):      # 0 = file a
                # Map chess rank/file to image coordinates depending on orientation
                if orientation == "white":
                    # white at bottom → rank 0 is at the bottom of the image
                    col = file_idx
                    row = 7 - rank_idx
                else:
                    # black at bottom → board rotated 180°
                    col = 7 - file_idx
                    row = rank_idx

                y1 = offset_y + row * sq
                x1 = offset_x + col * sq
                y2 = y1 + sq
                x2 = x1 + sq

                square_img = img[y1:y2, x1:x2]
                piece, conf = self._classify_square(square_img)

                confidences.append(conf)

                if piece is not None:
                    square = chess.square(file_idx, rank_idx)
                    board.set_piece_at(square, piece)
                    occupied += 1

        avg_conf = float(np.mean(confidences)) if confidences else 0.0

        # Side to move: for Stage 2 we default to white.
        # Later we can track moves or let the user set it.
        board.turn = chess.WHITE

        # Clear castling / en-passant for safety (Stage 2)
        board.castling_rights = 0
        board.ep_square = None

        return board, avg_conf, occupied

    def _classify_square(
        self, sq: np.ndarray
    ) -> Tuple[Optional[chess.Piece], float]:
        """
        Classify one square image.

        Returns (piece or None if empty, confidence 0..1).

        Current Stage 2 approach (no templates):
        1. Decide empty vs occupied by luminance variance.
        2. Decide white vs black piece by mean luminance.
        3. Piece type: basic heuristic (can be replaced by templates later).
        """
        if sq.size == 0 or sq.shape[0] < 8:
            return None, 0.0

        # Use the central 70% of the square to avoid border artifacts
        margin = max(1, int(sq.shape[0] * 0.15))
        core = sq[margin:-margin, margin:-margin]
        if core.size == 0:
            core = sq

        gray = self._luminance(core)
        mean_lum = float(np.mean(gray))
        std_lum = float(np.std(gray))

        # --- Empty detection ---
        # Empty squares have low variance (mostly one color)
        # Occupied squares have higher variance because of the piece shape
        EMPTY_STD_THRESHOLD = 18.0

        if std_lum < EMPTY_STD_THRESHOLD:
            return None, 0.85  # fairly confident it's empty

        # --- Side (color) of the piece ---
        # White pieces are bright, black pieces are dark.
        # Threshold is roughly in the middle of typical board themes.
        WHITE_LUM_THRESHOLD = 140.0

        is_white = mean_lum > WHITE_LUM_THRESHOLD
        color = chess.WHITE if is_white else chess.BLACK

        # --- Piece type (basic heuristic for Stage 2) ---
        # This is the weakest part. We use relative size of the "blob"
        # and brightness distribution. Real accuracy will come with templates.
        piece_type = self._guess_piece_type(core, gray, is_white)

        piece = chess.Piece(piece_type, color)

        # Confidence is lower for type guessing
        conf = 0.55 if piece_type != chess.PAWN else 0.65
        return piece, conf

    def _guess_piece_type(
        self,
        core: np.ndarray,
        gray: np.ndarray,
        is_white: bool,
    ) -> chess.PieceType:
        """
        Very rough piece type estimation without templates.

        Strategy:
        - Compute how "filled" the square is (percentage of pixels that differ
          strongly from the background).
        - Larger / more complex pieces occupy more of the square.
        - Kings and queens tend to be taller / brighter in the center.

        This is intentionally simple. Accuracy will be mediocre.
        The architecture is ready for a proper template matcher later.
        """
        # Background estimate = median of the border
        border = np.concatenate([
            gray[0, :],
            gray[-1, :],
            gray[:, 0],
            gray[:, -1],
        ])
        bg = float(np.median(border))

        # Pixels that differ from background (the piece)
        if is_white:
            mask = gray > bg + 25
        else:
            mask = gray < bg - 25

        fill_ratio = float(np.mean(mask))

        # Center brightness
        cy, cx = gray.shape[0] // 2, gray.shape[1] // 2
        center_patch = gray[cy - 3:cy + 4, cx - 3:cx + 4]
        center_mean = float(np.mean(center_patch)) if center_patch.size else bg

        # Heuristic thresholds (tuned for typical online boards)
        if fill_ratio < 0.18:
            return chess.PAWN
        if fill_ratio < 0.28:
            # could be knight or bishop
            return chess.KNIGHT if abs(center_mean - bg) > 40 else chess.BISHOP
        if fill_ratio < 0.38:
            return chess.ROOK
        if fill_ratio < 0.50:
            return chess.QUEEN
        return chess.KING

    # ------------------------------------------------------------------
    # Coordinate helpers
    # ------------------------------------------------------------------

    def pixel_to_square(self, x: int, y: int) -> Optional[chess.Square]:
        """Convert absolute screen pixel to chess.Square (0..63)."""
        if self.region is None or self._last_orientation is None:
            return None

        # Relative to region
        rx = x - self.region.left
        ry = y - self.region.top
        if rx < 0 or ry < 0 or rx >= self.region.width or ry >= self.region.height:
            return None

        size = min(self.region.width, self.region.height)
        sq = size // 8
        offset_x = (self.region.width - size) // 2
        offset_y = (self.region.height - size) // 2

        col = (rx - offset_x) // sq
        row = (ry - offset_y) // sq
        if not (0 <= col < 8 and 0 <= row < 8):
            return None

        if self._last_orientation == "white":
            file_idx = col
            rank_idx = 7 - row
        else:
            file_idx = 7 - col
            rank_idx = row

        return chess.square(file_idx, rank_idx)

    def square_to_pixel(self, square: chess.Square) -> Optional[Tuple[int, int]]:
        """Center of the given square in absolute screen coordinates."""
        if self.region is None or self._last_orientation is None:
            return None
        file = chess.square_file(square)
        rank = chess.square_rank(square)
        return square_center(self.region, file, rank, self._last_orientation)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _luminance(img: np.ndarray) -> np.ndarray:
        """RGB → luminance (float32)."""
        return (
            0.299 * img[:, :, 0].astype(np.float32)
            + 0.587 * img[:, :, 1].astype(np.float32)
            + 0.114 * img[:, :, 2].astype(np.float32)
        )
