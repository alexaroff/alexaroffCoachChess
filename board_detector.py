"""
alexaroffCoachChess — board detection & orientation + position recognition.

Given a screen Region that tightly contains a chessboard:
- Detect which side is at the bottom (white or black)
- Extract current position as FEN / chess.Board

Stage 2+: template matching (templates extracted from Duolingo).
Works for both orientations (white or black at bottom).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional, Tuple, List, Dict

import chess
import numpy as np
from PIL import Image

from tools import Region, capture_region, square_center

log = logging.getLogger(__name__)

Orientation = Literal["white", "black"]

# Templates live next to this file
TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
TEMPLATE_SIZE = 64  # all templates are 64x64


@dataclass
class BoardSnapshot:
    region: Region
    orientation: Orientation
    fen: Optional[str] = None
    board: Optional[chess.Board] = None
    confidence: float = 0.0
    occupied_count: int = 0


# Mapping from template filename stem → chess.Piece
_PIECE_FROM_NAME: Dict[str, chess.Piece] = {
    "wP": chess.Piece.from_symbol("P"),
    "wN": chess.Piece.from_symbol("N"),
    "wB": chess.Piece.from_symbol("B"),
    "wR": chess.Piece.from_symbol("R"),
    "wQ": chess.Piece.from_symbol("Q"),
    "wK": chess.Piece.from_symbol("K"),
    "bP": chess.Piece.from_symbol("p"),
    "bN": chess.Piece.from_symbol("n"),
    "bB": chess.Piece.from_symbol("b"),
    "bR": chess.Piece.from_symbol("r"),
    "bQ": chess.Piece.from_symbol("q"),
    "bK": chess.Piece.from_symbol("k"),
}


class BoardDetector:
    def __init__(self, region: Optional[Region] = None):
        self.region = region
        self._last_orientation: Optional[Orientation] = None
        self._last_img: Optional[np.ndarray] = None
        self._templates: Optional[Dict[str, np.ndarray]] = None  # name → float32 [0,1] HxWx3

    def set_region(self, region: Region) -> None:
        self.region = region
        self._last_orientation = None
        self._last_img = None

    # ------------------------------------------------------------------
    # Orientation
    # ------------------------------------------------------------------

    def detect_orientation(self, img: Optional[np.ndarray] = None) -> Orientation:
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
            orientation = "white"

        self._last_orientation = orientation
        return orientation

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def get_snapshot(self) -> BoardSnapshot:
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
        h, w = img.shape[:2]
        if h < 64 or w < 64:
            log.warning("Board region too small: %dx%d", w, h)
            return None, 0.0, 0

        size = min(h, w)
        sq = size // 8
        if sq < 12:
            log.warning("Square size too small: %d px", sq)
            return None, 0.0, 0

        offset_x = (w - size) // 2
        offset_y = (h - size) // 2

        self._ensure_templates()

        board = chess.Board(None)
        confidences: List[float] = []
        occupied = 0

        for rank_idx in range(8):
            for file_idx in range(8):
                if orientation == "white":
                    col = file_idx
                    row = 7 - rank_idx
                else:
                    col = 7 - file_idx
                    row = rank_idx

                y1 = offset_y + row * sq
                x1 = offset_x + col * sq
                square_img = img[y1:y1 + sq, x1:x1 + sq]

                # When black is at the bottom the whole board is rotated 180°.
                # Piece sprites are also upside-down relative to our templates,
                # so we rotate the square back before matching.
                if orientation == "black":
                    square_img = np.rot90(square_img, 2)

                piece, conf = self._classify_square(square_img)
                confidences.append(conf)

                if piece is not None:
                    square = chess.square(file_idx, rank_idx)
                    board.set_piece_at(square, piece)
                    occupied += 1

        avg_conf = float(np.mean(confidences)) if confidences else 0.0
        board.turn = chess.WHITE
        board.castling_rights = 0
        board.ep_square = None

        # --- Starting position detection ---
        # If we see ~32 pieces and both back ranks look occupied,
        # force the classic starting FEN (huge accuracy win on move 1).
        if occupied >= 30 and self._looks_like_starting_position(board):
            log.info("Starting position detected → forcing classic FEN")
            board = chess.Board()
            avg_conf = max(avg_conf, 0.95)
            occupied = 32

        return board, avg_conf, occupied

    def _looks_like_starting_position(self, board: chess.Board) -> bool:
        """Heuristic: both ranks 1/2 and 7/8 are fully occupied."""
        rank1 = sum(1 for f in range(8) if board.piece_at(chess.square(f, 0)))
        rank2 = sum(1 for f in range(8) if board.piece_at(chess.square(f, 1)))
        rank7 = sum(1 for f in range(8) if board.piece_at(chess.square(f, 6)))
        rank8 = sum(1 for f in range(8) if board.piece_at(chess.square(f, 7)))
        return rank1 == 8 and rank2 == 8 and rank7 == 8 and rank8 == 8

    # ------------------------------------------------------------------
    # Template matching
    # ------------------------------------------------------------------

    def _ensure_templates(self) -> None:
        if self._templates is not None:
            return
        self._templates = {}
        if not TEMPLATES_DIR.exists():
            log.warning("Templates directory not found: %s", TEMPLATES_DIR)
            return
        for path in TEMPLATES_DIR.glob("*.png"):
            name = path.stem
            img = Image.open(path).convert("RGB")
            arr = np.array(img, dtype=np.float32) / 255.0
            if arr.shape[0] != TEMPLATE_SIZE or arr.shape[1] != TEMPLATE_SIZE:
                arr = np.array(
                    img.resize((TEMPLATE_SIZE, TEMPLATE_SIZE), Image.Resampling.LANCZOS),
                    dtype=np.float32,
                ) / 255.0
            self._templates[name] = arr
        log.info("Loaded %d templates from %s", len(self._templates), TEMPLATES_DIR)

    def _classify_square(
        self, sq: np.ndarray
    ) -> Tuple[Optional[chess.Piece], float]:
        """
        Hybrid classification:
        1. Fast luminance check → empty / white / black
        2. Template matching only among templates of the detected color
        """
        if sq.size == 0 or sq.shape[0] < 8:
            return None, 0.0

        # --- Step 1: occupancy + color by luminance (very reliable on Duolingo) ---
        margin = max(1, int(sq.shape[0] * 0.15))
        core = sq[margin:-margin, margin:-margin]
        if core.size == 0:
            core = sq
        gray = self._luminance(core)
        mean_lum = float(np.mean(gray))
        std_lum = float(np.std(gray))

        if std_lum < 12.0:
            return None, 0.92  # empty

        is_white = mean_lum > 95.0
        color_prefix = "w" if is_white else "b"

        # --- Step 2: template match only against same-color pieces ---
        self._ensure_templates()
        if not self._templates:
            piece = chess.Piece(chess.PAWN, chess.WHITE if is_white else chess.BLACK)
            return piece, 0.40

        pil = Image.fromarray(sq)
        resized = pil.resize((TEMPLATE_SIZE, TEMPLATE_SIZE), Image.Resampling.LANCZOS)
        candidate = np.array(resized, dtype=np.float32) / 255.0

        # Match on central region only (reduces influence of square color)
        m = 8
        cand_core = candidate[m:-m, m:-m]
        # Use grayscale for shape matching
        cand_gray = (
            0.299 * cand_core[:, :, 0]
            + 0.587 * cand_core[:, :, 1]
            + 0.114 * cand_core[:, :, 2]
        )

        best_name = None
        best_score = -1.0

        for name, tmpl in self._templates.items():
            if not name.startswith(color_prefix):
                continue
            tmpl_core = tmpl[m:-m, m:-m]
            tmpl_gray = (
                0.299 * tmpl_core[:, :, 0]
                + 0.587 * tmpl_core[:, :, 1]
                + 0.114 * tmpl_core[:, :, 2]
            )
            score = 1.0 - float(np.mean(np.abs(cand_gray - tmpl_gray)))
            if score > best_score:
                best_score = score
                best_name = name

        if best_name is not None and best_score >= 0.70 and best_name in _PIECE_FROM_NAME:
            return _PIECE_FROM_NAME[best_name], best_score

        # Fallback: correct color, unknown type → pawn
        piece = chess.Piece(chess.PAWN, chess.WHITE if is_white else chess.BLACK)
        return piece, 0.50

    @staticmethod
    def _similarity(a: np.ndarray, b: np.ndarray) -> float:
        """
        Simple and fast similarity: 1 - mean absolute difference.
        Range [0, 1], higher = more similar.
        """
        return 1.0 - float(np.mean(np.abs(a - b)))

    # ------------------------------------------------------------------
    # Heuristic fallback (color + occupancy)
    # ------------------------------------------------------------------

    def _classify_square_heuristic(
        self, sq: np.ndarray
    ) -> Tuple[Optional[chess.Piece], float]:
        margin = max(1, int(sq.shape[0] * 0.15))
        core = sq[margin:-margin, margin:-margin]
        if core.size == 0:
            core = sq

        gray = self._luminance(core)
        mean_lum = float(np.mean(gray))
        std_lum = float(np.std(gray))

        if std_lum < 12.0:
            return None, 0.85

        # On Duolingo both sides are brighter than the board;
        # white pieces are still significantly brighter than black.
        is_white = mean_lum > 95.0
        color = chess.WHITE if is_white else chess.BLACK

        # Without reliable type we default to pawn (better than random)
        # so that at least the engine gets the correct material color.
        piece = chess.Piece(chess.PAWN, color)
        return piece, 0.45

    # ------------------------------------------------------------------
    # Coordinates
    # ------------------------------------------------------------------

    def pixel_to_square(self, x: int, y: int) -> Optional[chess.Square]:
        if self.region is None or self._last_orientation is None:
            return None
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
            file_idx, rank_idx = col, 7 - row
        else:
            file_idx, rank_idx = 7 - col, row
        return chess.square(file_idx, rank_idx)

    def square_to_pixel(self, square: chess.Square) -> Optional[Tuple[int, int]]:
        if self.region is None or self._last_orientation is None:
            return None
        file = chess.square_file(square)
        rank = chess.square_rank(square)
        return square_center(self.region, file, rank, self._last_orientation)

    @staticmethod
    def _luminance(img: np.ndarray) -> np.ndarray:
        return (
            0.299 * img[:, :, 0].astype(np.float32)
            + 0.587 * img[:, :, 1].astype(np.float32)
            + 0.114 * img[:, :, 2].astype(np.float32)
        )
