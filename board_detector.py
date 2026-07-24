"""
alexaroffCoachChess — board detection (hybrid-focused)

Priority: very reliable occupancy + color.
Piece type is secondary (recovered by coach.reconcile).
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

    def detect_orientation(self, img: Optional[np.ndarray] = None) -> Orientation:
        if self.region is None:
            raise RuntimeError("Region not set")
        if img is None:
            img = capture_region(self.region)

        if img.size == 0 or img.shape[0] < 16:
            self._last_orientation = "white"
            return "white"

        gray = self._luminance(img)
        h = gray.shape[0]
        band = max(h // 5, 10)

        bottom_val = float(np.percentile(gray[-band:], 75))
        top_val = float(np.percentile(gray[:band], 75))

        if bottom_val > top_val + 12:
            orientation = "white"
        elif top_val > bottom_val + 12:
            orientation = "black"
        else:
            orientation = "white"

        self._last_orientation = orientation
        return orientation

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
        self, img: np.ndarray, orientation: Orientation
    ) -> Tuple[Optional[chess.Board], float, int]:
        h, w = img.shape[:2]
        if h < 64 or w < 64:
            return None, 0.0, 0

        size = min(h, w)
        sq = size // 8
        if sq < 14:
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
                    col, row = file_idx, 7 - rank_idx
                else:
                    col, row = 7 - file_idx, rank_idx

                y1 = offset_y + row * sq
                x1 = offset_x + col * sq
                square_img = img[y1:y1+sq, x1:x1+sq]

                if orientation == "black":
                    square_img = np.rot90(square_img, 2)

                piece, conf = self._classify_square(square_img)
                confidences.append(conf)

                if piece is not None:
                    board.set_piece_at(chess.square(file_idx, rank_idx), piece)
                    occupied += 1

        avg_conf = float(np.mean(confidences)) if confidences else 0.0
        board.turn = chess.WHITE
        board.castling_rights = 0
        board.ep_square = None

        if occupied >= 30 and self._looks_like_starting_position(board):
            log.info("Starting position detected → forcing classic FEN")
            board = chess.Board()
            avg_conf = max(avg_conf, 0.95)
            occupied = 32

        return board, avg_conf, occupied

    def _looks_like_starting_position(self, board: chess.Board) -> bool:
        r1 = sum(1 for f in range(8) if board.piece_at(chess.square(f, 0)))
        r2 = sum(1 for f in range(8) if board.piece_at(chess.square(f, 1)))
        r7 = sum(1 for f in range(8) if board.piece_at(chess.square(f, 6)))
        r8 = sum(1 for f in range(8) if board.piece_at(chess.square(f, 7)))
        return r1 == 8 and r2 == 8 and r7 == 8 and r8 == 8

    def _ensure_templates(self) -> None:
        if self._templates is not None:
            return
        self._templates = {}
        if not TEMPLATES_DIR.exists():
            return
        for path in TEMPLATES_DIR.glob("*.png"):
            name = path.stem
            if name.startswith("empty"):
                continue
            img = Image.open(path).convert("RGB")
            arr = np.array(img, dtype=np.float32) / 255.0
            if arr.shape[0] != TEMPLATE_SIZE or arr.shape[1] != TEMPLATE_SIZE:
                arr = np.array(img.resize((TEMPLATE_SIZE, TEMPLATE_SIZE), Image.Resampling.LANCZOS), dtype=np.float32) / 255.0
            self._templates[name] = arr
        log.info("Loaded %d templates", len(self._templates))

    def _classify_square(self, sq: np.ndarray) -> Tuple[Optional[chess.Piece], float]:
        """
        Focus: reliable empty vs occupied + color.
        Type is best-effort (coach will fix via legal moves).
        """
        if sq.size == 0 or sq.shape[0] < 12:
            return None, 0.0

        margin = max(2, int(sq.shape[0] * 0.17))
        core = sq[margin:-margin, margin:-margin]
        if core.size < 16:
            core = sq

        gray = self._luminance(core)
        mean_lum = float(np.mean(gray))
        std_lum = float(np.std(gray))

        # Empty — very flat on Duolingo
        if std_lum < 13.0:
            return None, 0.95

        is_white = mean_lum > 98.0
        color = chess.WHITE if is_white else chess.BLACK
        color_prefix = "w" if is_white else "b"

        # Try to get type, but we do not trust it strongly
        self._ensure_templates()
        piece_type = chess.PAWN
        type_conf = 0.40

        if self._templates:
            pil = Image.fromarray(sq.astype(np.uint8))
            resized = np.array(pil.resize((TEMPLATE_SIZE, TEMPLATE_SIZE), Image.Resampling.LANCZOS), dtype=np.float32) / 255.0
            m = 9
            cand = self._normalize(self._luminance(resized[m:-m, m:-m]))

            best_name = None
            best_score = -1.0
            for name, tmpl in self._templates.items():
                if not name.startswith(color_prefix):
                    continue
                t = self._normalize(self._luminance(tmpl[m:-m, m:-m]))
                score = float(np.mean(cand * t))
                if score > best_score:
                    best_score = score
                    best_name = name

            if best_name and best_score >= 0.58 and best_name in _PIECE_FROM_NAME:
                return _PIECE_FROM_NAME[best_name], float(best_score)

        return chess.Piece(piece_type, color), type_conf

    @staticmethod
    def _normalize(arr: np.ndarray) -> np.ndarray:
        mean = float(np.mean(arr))
        std = float(np.std(arr)) + 1e-5
        return (arr - mean) / std

    def pixel_to_square(self, x: int, y: int) -> Optional[chess.Square]:
        if self.region is None or self._last_orientation is None:
            return None
        rx = x - self.region.left
        ry = y - self.region.top
        if not (0 <= rx < self.region.width and 0 <= ry < self.region.height):
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
            return chess.square(col, 7 - row)
        return chess.square(7 - col, row)

    def square_to_pixel(self, square: chess.Square) -> Optional[Tuple[int, int]]:
        if self.region is None or self._last_orientation is None:
            return None
        return square_center(self.region, chess.square_file(square), chess.square_rank(square), self._last_orientation)

    @staticmethod
    def _luminance(img: np.ndarray) -> np.ndarray:
        return (0.299 * img[:, :, 0] + 0.587 * img[:, :, 1] + 0.114 * img[:, :, 2]).astype(np.float32)
