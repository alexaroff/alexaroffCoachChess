"""
alexaroffCoachChess — Coach / Auto logic + arrow overlay.
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
from overlay import ArrowOverlay

log = logging.getLogger(__name__)

# After this many consecutive weak reconciles we force a turn flip.
# Heuristic: if the pixel board keeps changing but we cannot match any legal move,
# a real move almost certainly happened and the detector just failed type matching.
WEAK_RECONCILE_FLIP_THRESHOLD = 2


class Coach:
    def __init__(self, detector: BoardDetector, engine: EngineManager):
        self.detector = detector
        self.engine = engine
        self.advisor = Advisor()
        self.overlay = ArrowOverlay()
        self.mode: str = MODE_COACH
        self._running = False

        self._last_fen: Optional[str] = None
        self._last_board: Optional[chess.Board] = None
        self._last_advice: Optional[Advice] = None
        self._weak_reconcile_streak: int = 0

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
        self._weak_reconcile_streak = 0

        # Give overlay the current region
        self.overlay.set_region(self.detector.region)
        log.info("Coach started in %s mode", self.mode)

    def stop(self) -> None:
        self._running = False
        self.overlay.hide()
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
            self.overlay.hide()
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
            self.overlay.hide()
            self._execute_move(snapshot, move)

        return move

    def _reconcile(self, detected: chess.Board) -> Optional[chess.Board]:
        if self._last_board is None:
            self._weak_reconcile_streak = 0
            return detected

        prev = self._last_board

        if detected.piece_map() == prev.piece_map():
            self._weak_reconcile_streak = 0
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

        # Good legal move found
        if best_board is not None and best_score >= 48.0 and best_score > no_move_score + 1.5:
            self._weak_reconcile_streak = 0
            log.info("Reconciled via legal move (score=%.1f)", best_score)
            return best_board

        # Position looks unchanged → keep previous (including turn)
        if no_move_score >= 50.0:
            self._weak_reconcile_streak = 0
            return prev

        # --- Weak fallback path ---
        self._weak_reconcile_streak += 1

        # Default: preserve turn (safe when the change was just noise)
        detected.turn = prev.turn
        detected.castling_rights = prev.castling_rights
        detected.ep_square = None

        if self._weak_reconcile_streak >= WEAK_RECONCILE_FLIP_THRESHOLD:
            # Pixels keep changing but we cannot match any legal move.
            # Almost certainly a real move happened and type classification failed.
            # Force the turn to flip so we do not stay stuck on the wrong side.
            detected.turn = not prev.turn
            log.warning(
                "Reconcile weak ×%d (best=%.1f, no_move=%.1f) → FORCED turn flip to %s",
                self._weak_reconcile_streak,
                best_score,
                no_move_score,
                "white" if detected.turn else "black",
            )
            # Reset streak after the forced flip so we don't flip every subsequent frame
            self._weak_reconcile_streak = 0
        else:
            log.warning(
                "Reconcile weak ×%d (best=%.1f, no_move=%.1f) → preserving turn=%s",
                self._weak_reconcile_streak,
                best_score,
                no_move_score,
                "white" if prev.turn else "black",
            )

        return detected

    @staticmethod
    def _color_similarity(a: chess.Board, b: chess.Board) -> float:
        """
        Occupancy + color match (1.0) + type match bonus (0.5).
        Max theoretical ≈ 96.
        """
        score = 0.0
        for sq in chess.SQUARES:
            pa = a.piece_at(sq)
            pb = b.piece_at(sq)
            if pa is None and pb is None:
                score += 1.0
            elif pa is not None and pb is not None and pa.color == pb.color:
                score += 1.0
                if pa.piece_type == pb.piece_type:
                    score += 0.5
        return score

    def _show_move(self, snapshot: BoardSnapshot, move: chess.Move) -> None:
        from_xy = self.detector.square_to_pixel(move.from_square)
        to_xy = self.detector.square_to_pixel(move.to_square)

        if from_xy is None or to_xy is None:
            log.warning("Cannot map squares to pixels for arrow")
            self.overlay.hide()
            return

        log.info("Showing arrow %s → %s", from_xy, to_xy)
        self.overlay.show_arrow(from_xy, to_xy)

    def _execute_move(self, snapshot: BoardSnapshot, move: chess.Move) -> None:
        from_xy = self.detector.square_to_pixel(move.from_square)
        to_xy = self.detector.square_to_pixel(move.to_square)
        if from_xy is None or to_xy is None:
            return
        time.sleep(AUTO_CLICK_DELAY_MS / 1000.0)
        click_at(*from_xy)
        time.sleep(0.08)
        click_at(*to_xy)
        log.info("Auto-played %s", move.uci())
