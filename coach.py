"""
alexaroffCoachChess — Coach / Auto logic.

Orchestrates BoardDetector + EngineManager + Advisor.
- Temporal consistency (previous position + legal moves)
- Best move from Stockfish
- Short strategic tips from advisor
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
    def __init__(
        self,
        detector: BoardDetector,
        engine: EngineManager,
    ):
        self.detector = detector
        self.engine = engine
        self.advisor = Advisor()
        self.mode: str = MODE_COACH
        self._running = False

        # Temporal memory
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
        """
        One iteration:
        1. Capture + recognize
        2. Reconcile with previous position (legal moves)
        3. Ask engine for best move
        4. Ask advisor for a short tip
        """
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
            return None  # nothing changed

        self._last_fen = fen
        self._last_board = board.copy()

        if board.is_game_over():
            log.info("Game over detected")
            self._last_advice = self.advisor.game_over(board)
            return None

        move = self.engine.get_best_move(board)
        if move is None:
            return None

        # Strategic tip
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
        Improve recognition using previous position + legal moves.

        If we have a previous board:
        - Generate all legal moves
        - See which resulting position best matches the newly detected board
        - Prefer a legal continuation over a noisy raw detection
        """
        if self._last_board is None:
            # First snapshot — trust detection (starting-position force already applied)
            return detected

        prev = self._last_board

        # Exact match?
        if detected.piece_map() == prev.piece_map():
            return prev

        # Try every legal move from previous position
        best_board = None
        best_score = -1

        for move in prev.legal_moves:
            b = prev.copy()
            b.push(move)
            score = self._similarity(b, detected)
            if score > best_score:
                best_score = score
                best_board = b

        # Also consider "no move happened" (score vs previous)
        no_move_score = self._similarity(prev, detected)

        # Threshold: if a legal move explains ≥ 28/32 pieces, trust it
        if best_board is not None and best_score >= 28 and best_score >= no_move_score:
            log.debug("Reconciled via legal move (score=%d)", best_score)
            return best_board

        if no_move_score >= 30:
            return prev

        # Fallback: raw detection (may contain type errors)
        log.debug("Using raw detection (best legal score=%d)", best_score)
        return detected

    @staticmethod
    def _similarity(a: chess.Board, b: chess.Board) -> int:
        """How many squares have the same piece (or both empty)."""
        score = 0
        for sq in chess.SQUARES:
            if a.piece_at(sq) == b.piece_at(sq):
                score += 1
        return score

    def _show_move(self, snapshot: BoardSnapshot, move: chess.Move) -> None:
        # Stage 3: overlay arrow
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
