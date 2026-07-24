"""
alexaroffCoachChess — Coach / Auto logic.

Hybrid temporal consistency (24.07.2026):
- Detector is trusted mainly for occupancy + color
- Piece types are recovered via legal-move search from previous position
"""

from __future__ import annotations

import logging
import time
from typing import Optional

import chess

from board_detector import BoardDetector, BoardSnapshot
from engine_manager import EngineManager
from tools import click_at
from config import MODE_COACH, MODE_AUTO, AUTO_CLICK_DELAY_MS
from advisor import Advisor, Advice

log = logging.getLogger(__name__)


class Coach:
    def __init__(self, detector: BoardDetector, engine: EngineManager):
        self.detector = detector
        self.engine = engine
        self.advisor = Advisor()
        self.mode: str = MODE_COACH
        self._running = False

        self._last_fen: Optional[str] = None
        self._last_board: Optional[chess.Board] = None
        self._last_advice: Optional[Advice] = None

    def set_mode(self, mode: str) -> None:
        if mode not in (MODE_COACH, MODE_AUTO):
            raise ValueError(f"Unknown mode: {mode}")
        self.mode = mode
        log.info("Mode set to %s", mode)

    def start(self) -> None:
        if self.detector.region is None:
            raise RuntimeError("Board region not selected")
        if not self.engine.is_running:
            self.engine.start()
        self._running = True
        self._last_fen = None
        self._last_board = None
        log.info("Coach started in %s mode", self.mode)

    def stop(self) -> None:
        self._running = False
        log.info("Coach stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def last_advice(self) -> Optional[Advice]:
        return self._last_advice

    def tick(self) -> Optional[chess.Move]:
        if not self._running:
            return None

        snapshot = self.detector.get_snapshot()
        if snapshot.fen is None or snapshot.board is None:
            return None

        board = self._reconcile(snapshot.board)

        if board is None:
            return None

        fen = board.fen()
        if fen == self._last_fen:
            return None

        self._last_fen = fen
        self._last_board = board.copy()

        if board.is_game_over():
            log.info("Game over detected")
            self._last_advice = self.advisor.game_over(board)
            return None

        move = self.engine.get_best_move(board)
        if move is None:
            return None

        self._last_advice = self.advisor.advice(board, move)

        log.info(
            "Best move: %s | phase=%s | tip: %s",
            move.uci(),
            self._last_advice.phase if self._last_advice else "?",
            self._last_advice.text if self._last_advice else "-",
        )

        if self.mode == MODE_COACH:
            self._show_move(snapshot, move)
        elif self.mode == MODE_AUTO:
            self._execute_move(snapshot, move)

        return move

    def _reconcile(self, detected: chess.Board) -> Optional[chess.Board]:
        """
        Hybrid reconcile:
        We trust the detector mainly for which squares are occupied and of which color.
        Exact piece type is recovered by finding the legal move that best explains
        the observed occupancy + color pattern.
        """
        if self._last_board is None:
            return detected

        prev = self._last_board

        # Exact match (including types)
        if detected.piece_map() == prev.piece_map():
            return prev

        best_board = None
        best_score = -1.0

        for move in prev.legal_moves:
            b = prev.copy()
            b.push(move)
            score = self._color_similarity(b, detected)
            if score > best_score:
                best_score = score
                best_board = b

        no_move_score = self._color_similarity(prev, detected)

        # Thresholds are lower because we only compare colors + occupancy
        if best_board is not None and best_score >= 30.0 and best_score >= no_move_score:
            log.info("Reconciled via legal move (color-score=%.1f)", best_score)
            return best_board

        if no_move_score >= 31.0:
            return prev

        log.debug("Using raw detection (best color-score=%.1f)", best_score)
        return detected

    @staticmethod
    def _color_similarity(a: chess.Board, b: chess.Board) -> float:
        """
        Score based on occupancy + color only (ignores piece type).
        Each square contributes:
          1.0 if both empty or both have piece of same color
          0.0 otherwise
        """
        score = 0.0
        for sq in chess.SQUARES:
            pa = a.piece_at(sq)
            pb = b.piece_at(sq)

            if pa is None and pb is None:
                score += 1.0
            elif pa is not None and pb is not None and pa.color == pb.color:
                score += 1.0
            # else 0

        return score

    def _show_move(self, snapshot: BoardSnapshot, move: chess.Move) -> None:
        log.debug("Would show arrow for %s", move.uci())

    def _execute_move(self, snapshot: BoardSnapshot, move: chess.Move) -> None:
        from_xy = self.detector.square_to_pixel(move.from_square)
        to_xy = self.detector.square_to_pixel(move.to_square)
        if from_xy is None or to_xy is None:
            log.warning("Cannot map squares to pixels")
            return
        time.sleep(AUTO_CLICK_DELAY_MS / 1000.0)
        click_at(*from_xy)
        time.sleep(0.08)
        click_at(*to_xy)
        log.info("Auto-played %s", move.uci())
