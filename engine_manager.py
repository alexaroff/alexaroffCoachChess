"""
alexaroffCoachChess — Stockfish engine manager.

Thin wrapper around python-chess.engine.
Target: ~3000 Elo with 1 thread and low CPU load (short movetime).
"""

from __future__ import annotations

import logging
from typing import Optional

import chess
import chess.engine

from config import (
    STOCKFISH_PATH,
    ENGINE_THREADS,
    ENGINE_HASH_MB,
    DEFAULT_MOVETIME_MS,
    ENGINE_SKILL_LEVEL,
)

log = logging.getLogger(__name__)


class EngineManager:
    """
    Lifecycle:
        eng = EngineManager()
        eng.start()
        move = eng.get_best_move(board)
        eng.stop()
    """

    def __init__(self, path: Optional[str] = None):
        self.path = path or STOCKFISH_PATH
        self._engine: Optional[chess.engine.SimpleEngine] = None

    @property
    def is_running(self) -> bool:
        return self._engine is not None

    def start(self) -> None:
        if self._engine is not None:
            return
        log.info("Starting Stockfish at %s", self.path)
        try:
            self._engine = chess.engine.SimpleEngine.popen_uci(self.path)
        except FileNotFoundError as e:
            raise RuntimeError(
                f"Stockfish binary not found at '{self.path}'. "
                "Install via `brew install stockfish` or set STOCKFISH_PATH."
            ) from e

        # Configure for low load + high strength
        options = {
            "Threads": ENGINE_THREADS,
            "Hash": ENGINE_HASH_MB,
        }
        if ENGINE_SKILL_LEVEL is not None:
            options["Skill Level"] = ENGINE_SKILL_LEVEL

        self._engine.configure(options)
        log.info("Engine ready (Threads=%s, Hash=%s)", ENGINE_THREADS, ENGINE_HASH_MB)

    def stop(self) -> None:
        if self._engine is not None:
            try:
                self._engine.quit()
            except Exception:
                pass
            self._engine = None
            log.info("Engine stopped")

    def get_best_move(
        self,
        board: chess.Board,
        movetime_ms: Optional[int] = None,
    ) -> Optional[chess.Move]:
        """
        Return best move for the given position.
        Uses time limit to keep CPU load low and response snappy.
        """
        if self._engine is None:
            raise RuntimeError("Engine not started. Call start() first.")

        if board.is_game_over():
            return None

        limit = chess.engine.Limit(time=(movetime_ms or DEFAULT_MOVETIME_MS) / 1000.0)
        result = self._engine.play(board, limit)
        return result.move

    def analyse(
        self,
        board: chess.Board,
        movetime_ms: int = 100,
    ) -> chess.engine.InfoDict:
        """Optional deeper analysis (score, PV)."""
        if self._engine is None:
            raise RuntimeError("Engine not started")
        limit = chess.engine.Limit(time=movetime_ms / 1000.0)
        return self._engine.analyse(board, limit)

    def __enter__(self) -> "EngineManager":
        self.start()
        return self

    def __exit__(self, *args) -> None:
        self.stop()
