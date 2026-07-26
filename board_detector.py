"""
alexaroffCoachChess — board detection (hybrid-focused + NN classifier)

Priority: very reliable occupancy + color + piece type via TinyCNN.
Piece type is still secondary (recovered by coach.reconcile if needed).
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Optional, Tuple, List, Dict

import chess
import numpy as np
from PIL import Image
import torch
import torch.nn as nn

from tools import Region, capture_region

log = logging.getLogger(__name__)

Orientation = Literal["white", "black"]

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
MODELS_DIR = Path(__file__).resolve().parent / "models"
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


class TinyCNN(nn.Module):
    """Very small CNN tailored for 64x64 chess pieces. Must match train script."""

    def __init__(self, num_classes: int = 13):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(3, 24, 3, padding=1, bias=False),
            nn.BatchNorm2d(24),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(24, 48, 3, padding=1, bias=False),
            nn.BatchNorm2d(48),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(48, 72, 3, padding=1, bias=False),
            nn.BatchNorm2d(72),
            nn.ReLU(inplace=True),
            nn.MaxPool2d(2),
            nn.Conv2d(72, 96, 3, padding=1, bias=False),
            nn.BatchNorm2d(96),
            nn.ReLU(inplace=True),
            nn.AdaptiveAvgPool2d(1),
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Dropout(0.25),
            nn.Linear(96, num_classes),
        )

    def forward(self, x):
        x = self.features(x)
        return self.classifier(x)


class BoardDetector:
    def __init__(self, region: Optional[Region] = None):
        self.region = region
        self._last_orientation: Optional[Orientation] = None
        self._orientation_locked: bool = False
        self._forced_start_once: bool = False
        self._last_img: Optional[np.ndarray] = None
        self._templates: Optional[Dict[str, np.ndarray]] = None
        self._nn_model: Optional[nn.Module] = None
        self._nn_classes: Optional[List[str]] = None
        self._nn_device = torch.device("cpu")
        self._load_nn()

    def _load_nn(self) -> None:
        model_path = MODELS_DIR / "student_tiny_cnn.pt"
        classes_path = MODELS_DIR / "class_names.json"
        if not model_path.exists() or not classes_path.exists():
            log.warning("NN model not found at %s — falling back to templates", model_path)
            return
        try:
            with open(classes_path) as f:
                self._nn_classes = json.load(f)
            num_classes = len(self._nn_classes)
            model = TinyCNN(num_classes)
            ckpt = torch.load(model_path, map_location="cpu", weights_only=False)
            model.load_state_dict(ckpt["model_state"])
            model.eval()
            self._nn_model = model
            log.info("Loaded TinyCNN with %d classes, val_acc=%.3f", num_classes, ckpt.get("val_acc", 0))
        except Exception as e:
            log.error("Failed to load NN model: %s", e)
            self._nn_model = None

    def set_region(self, region: Region) -> None:
        self.region = region
        self._last_orientation = None
        self._orientation_locked = False
        self._forced_start_once = False
        self._last_img = None

    def lock_orientation(self) -> None:
        self._orientation_locked = True

    def unlock_orientation(self) -> None:
        self._orientation_locked = False

    def detect_orientation(self, img: Optional[np.ndarray] = None, force: bool = False) -> Orientation:
        if self.region is None:
            raise RuntimeError("Region not set")

        if self._orientation_locked and self._last_orientation is not None and not force:
            return self._last_orientation

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

        if not self._orientation_locked and occupied >= 10 and confidence > 0.5:
            self._orientation_locked = True
            log.info("Orientation locked to '%s'", orientation)

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

        board.castling_rights = 0
        board.ep_square = None

        if (
            not self._forced_start_once
            and occupied >= 30
            and self._looks_like_starting_position(board)
        ):
            log.info("Starting position detected → forcing classic FEN (once)")
            board = chess.Board()
            avg_conf = max(avg_conf, 0.95)
            occupied = 32
            self._forced_start_once = True

        return board, avg_conf, occupied

    def _looks_like_starting_position(self, board: chess.Board) -> bool:
        r1 = sum(1 for f in range(8) if board.piece_at(chess.square(f, 0)))
        r2 = sum(1 for f in range(8) if board.piece_at(chess.square(f, 1)))
        r7 = sum(1 for f in range(8) if board.piece_at(chess.square(f, 6)))
        r8 = sum(1 for f in range(8) if board.piece_at(chess.square(f, 7)))
        return r1 == 8 and r2 == 8 and r7 == 8 and r8 == 8

    def _classify_square(self, sq: np.ndarray) -> Tuple[Optional[chess.Piece], float]:
        if sq.size == 0 or sq.shape[0] < 12:
            return None, 0.0

        if self._nn_model is not None and self._nn_classes is not None:
            return self._classify_with_nn(sq)

        return self._classify_with_templates(sq)

    def _classify_with_nn(self, sq: np.ndarray) -> Tuple[Optional[chess.Piece], float]:
        pil = Image.fromarray(sq.astype(np.uint8) if sq.dtype != np.uint8 else sq)
        resized = pil.resize((TEMPLATE_SIZE, TEMPLATE_SIZE), Image.Resampling.LANCZOS)
        arr = np.array(resized, dtype=np.float32) / 255.0

        mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
        std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
        arr = (arr - mean) / std
        arr = arr.transpose(2, 0, 1)
        tensor = torch.from_numpy(arr).unsqueeze(0)

        with torch.no_grad():
            logits = self._nn_model(tensor)
            probs = torch.softmax(logits, dim=1)[0]
            conf, idx = probs.max(0)
            conf = float(conf)
            name = self._nn_classes[int(idx)]

        if name == "empty":
            return None, conf

        # Protect kings at all costs — otherwise Stockfish refuses the position.
        if name in ("wK", "bK") and name in _PIECE_FROM_NAME:
            return _PIECE_FROM_NAME[name], conf

        # For other pieces: keep NN type but with capped confidence
        # so reconcile can still override via legal moves when needed.
        if name in _PIECE_FROM_NAME:
            return _PIECE_FROM_NAME[name], min(conf, 0.65)

        return None, 0.0

    def _classify_with_templates(self, sq: np.ndarray) -> Tuple[Optional[chess.Piece], float]:
        margin = max(2, int(sq.shape[0] * 0.17))
        core = sq[margin:-margin, margin:-margin]
        if core.size < 16:
            core = sq

        gray = self._luminance(core)
        mean_lum = float(np.mean(gray))
        std_lum = float(np.std(gray))

        if std_lum < 14.0:
            return None, 0.95

        is_white = mean_lum > 65.0
        color = chess.WHITE if is_white else chess.BLACK
        color_prefix = "w" if is_white else "b"

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

            if best_name and best_score >= 0.55 and best_name in _PIECE_FROM_NAME:
                return _PIECE_FROM_NAME[best_name], float(best_score)

        return chess.Piece(piece_type, color), type_conf

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

        file = chess.square_file(square)
        rank = chess.square_rank(square)

        size = min(self.region.width, self.region.height)
        sq = size // 8
        offset_x = (self.region.width - size) // 2
        offset_y = (self.region.height - size) // 2

        if self._last_orientation == "white":
            col = file
            row = 7 - rank
        else:
            col = 7 - file
            row = rank

        cx = self.region.left + offset_x + col * sq + sq // 2
        cy = self.region.top + offset_y + row * sq + sq // 2
        return cx, cy

    @staticmethod
    def _luminance(img: np.ndarray) -> np.ndarray:
        return (0.299 * img[:, :, 0] + 0.587 * img[:, :, 1] + 0.114 * img[:, :, 2]).astype(np.float32)
