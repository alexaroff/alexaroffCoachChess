"""
alexaroffCoachChess — board detection & orientation + position recognition.

Improved Stage 2.5 (24.07.2026):
- Normalized Cross-Correlation (NCC) instead of mean abs diff
- Better preprocessing (per-square mean/std normalization)
- More robust empty / color detection tuned for Duolingo
- Lower but safer decision thresholds
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

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
TEMPLATE_SIZE = 64


@dataclass
class BoardSnapshot:
    region: Region
    orientation: Orientation
    fen: Optional[str] = None
    board: Optional[chess.Board] = None
    confidence: float = 0.0
    occupied_count: int = 0


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
        self._templates: Optional[Dict[str, np.ndarray]] = None

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
        band = max(h // 5, 10)

        bottom = gray[-band:, :]
        top = gray[:band, :]

        # Use 75th percentile — more robust to empty squares
        bottom_val = float(np.percentile(bottom, 75))
        top_val = float(np.percentile(top, 75))

        if bottom_val > top_val + 15:
            orientation = "white"
        elif top_val > bottom_val + 15:
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
        if sq < 14:
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

        # Starting position force (very reliable)
        if occupied >= 30 and self._looks_like_starting_position(board):
            log.info("Starting position detected → forcing classic FEN")
            board = chess.Board()
            avg_conf = max(avg_conf, 0.95)
            occupied = 32

        return board, avg_conf, occupied

    def _looks_like_starting_position(self, board: chess.Board) -> bool:
        rank1 = sum(1 for f in range(8) if board.piece_at(chess.square(f, 0)))
        rank2 = sum(1 for f in range(8) if board.piece_at(chess.square(f, 1)))
        rank7 = sum(1 for f in range(8) if board.piece_at(chess.square(f, 6)))
        rank8 = sum(1 for f in range(8) if board.piece_at(chess.square(f, 7)))
        return rank1 == 8 and rank2 == 8 and rank7 == 8 and rank8 == 8

    # ------------------------------------------------------------------
    # Template matching (improved)
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
            if name.startswith("empty"):
                continue
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
        if sq.size == 0 or sq.shape[0] < 10:
            return None, 0.0

        # --- 1. Empty detection (variance of central area) ---
        margin = max(2, int(sq.shape[0] * 0.18))
        core = sq[margin:-margin, margin:-margin]
        if core.size == 0:
            core = sq

        gray = self._luminance(core)
        mean_lum = float(np.mean(gray))
        std_lum = float(np.std(gray))

        # Empty squares on Duolingo are very flat
        if std_lum < 14.0:
            return None, 0.93

        # --- 2. Color (white / black piece) ---
        # White pieces are significantly brighter
        is_white = mean_lum > 105.0
        color_prefix = "w" if is_white else "b"

        # --- 3. Template matching with NCC ---
        self._ensure_templates()
        if not self._templates:
            piece = chess.Piece(chess.PAWN, chess.WHITE if is_white else chess.BLACK)
            return piece, 0.35

        # Resize candidate to template size
        pil = Image.fromarray(sq.astype(np.uint8))
        resized = pil.resize((TEMPLATE_SIZE, TEMPLATE_SIZE), Image.Resampling.LANCZOS)
        candidate = np.array(resized, dtype=np.float32) / 255.0

        # Use central region + grayscale + normalize
        m = 10
        cand = candidate[m:-m, m:-m]
        cand_gray = self._luminance(cand)
        cand_norm = self._normalize(cand_gray)

        best_name = None
        best_score = -1.0

        for name, tmpl in self._templates.items():
            if not name.startswith(color_prefix):
                continue

            t = tmpl[m:-m, m:-m]
            t_gray = self._luminance(t)
            t_norm = self._normalize(t_gray)

            score = self._ncc(cand_norm, t_norm)
            if score > best_score:
                best_score = score
                best_name = name

        # Decision
        if best_name is not None and best_score >= 0.55 and best_name in _PIECE_FROM_NAME:
            return _PIECE_FROM_NAME[best_name], float(best_score)

        # Fallback: correct color, unknown type → pawn
        piece = chess.Piece(chess.PAWN, chess.WHITE if is_white else chess.BLACK)
        return piece, 0.40

    @staticmethod
    def _normalize(arr: np.ndarray) -> np.ndarray:
        """Zero-mean, unit-variance normalization."""
        mean = float(np.mean(arr))
        std = float(np.std(arr)) + 1e-6
        return (arr - mean) / std

    @staticmethod
    def _ncc(a: np.ndarray, b: np.ndarray) -> float:
        """Normalized Cross-Correlation. Range roughly [-1, 1]."""
        if a.shape != b.shape:
            return -1.0
        return float(np.mean(a * b))

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
