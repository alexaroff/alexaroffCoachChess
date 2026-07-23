"""
alexaroffCoachChess — Coach / Auto logic.

Orchestrates BoardDetector + EngineManager.
Responsible for:
- deciding when to think
- showing the best move (Coach)
- executing the move via clicks (Auto)
"""

from __future__ import annotations

import logging
import time
from typing import Optional

import chess

from board_detector import BoardDetector, BoardSnapshot
from engine_manager import EngineManager
from tools import Region, click_at
from config import MODE_COACH, MODE_AUTO, POLL_INTERVAL_MS, AUTO_CLICK_DELAY_MS

log = logging.getLogger(__name__)


class Coach:
    """
    High-level controller for both modes.
    Stage 0: skeleton only. Real loop + overlay in later stages.
    """

    def __init__(
        self,
        detector: BoardDetector,
        engine: EngineManager,
    ):
        self.detector = detector
        self.engine = engine
        self.mode: str = MODE_COACH
        self._running = False
        self._last_fen: Optional[str] = None

    def set_mode(self, mode: str) -> None:
        if mode not in (MODE_COACH, MODE_AUTO):
            raise ValueError(f"Unknown mode: {mode}")
        self.mode = mode
        log.info("Mode set to %s", mode)

    def start(self) -> None:
        """Start the main loop (non-blocking or blocking — decide in main)."""
        if self.detector.region is None:
            raise RuntimeError("Board region not selected")
        if not self.engine.is_running:
            self.engine.start()
        self._running = True
        log.info("Coach started in %s mode", self.mode)

    def stop(self) -> None:
        self._running = False
        log.info("Coach stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    def tick(self) -> Optional[chess.Move]:
        """
        One iteration of the thinking loop.
        Called periodically from main (GUI timer or thread).

        Returns the best move if a new position was detected, else None.
        """
        if not self._running:
            return None

        snapshot = self.detector.get_snapshot()

        # Stage 2 will provide real FEN. For now we cannot proceed.
        if snapshot.fen is None or snapshot.board is None:
            # log.debug("No valid position yet")
            return None

        if snapshot.fen == self._last_fen:
            return None  # position unchanged

        self._last_fen = snapshot.fen
        board = snapshot.board

        if board.is_game_over():
            log.info("Game over detected")
            return None

        move = self.engine.get_best_move(board)
        if move is None:
            return None

        log.info("Best move: %s (orientation=%s)", move.uci(), snapshot.orientation)

        if self.mode == MODE_COACH:
            self._show_move(snapshot, move)
        elif self.mode == MODE_AUTO:
            self._execute_move(snapshot, move)

        return move

    def _show_move(self, snapshot: BoardSnapshot, move: chess.Move) -> None:
        """
        Coach mode: draw arrow / highlight on overlay.
        Stage 3 implementation.
        """
        # TODO Stage 3: update transparent overlay window
        log.debug("Would show arrow for %s", move.uci())

    def _execute_move(self, snapshot: BoardSnapshot, move: chess.Move) -> None:
        """
        Auto mode: click from-square then to-square.
        """
        from_sq = move.from_square
        to_sq = move.to_square

        from_xy = self.detector.square_to_pixel(from_sq)
        to_xy = self.detector.square_to_pixel(to_sq)

        if from_xy is None or to_xy is None:
            log.warning("Cannot map squares to pixels")
            return

        time.sleep(AUTO_CLICK_DELAY_MS / 1000.0)
        click_at(*from_xy)
        time.sleep(0.08)
        click_at(*to_xy)
        log.info("Auto-played %s", move.uci())
