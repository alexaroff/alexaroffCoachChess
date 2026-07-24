"""
alexaroffCoachChess — Stockfish engine manager.

Now with automatic restart on crash.
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

    def _restart(self) -> None:
        log.warning("Restarting Stockfish after crash...")
        self.stop()
        self.start()

    def get_best_move(
        self,
        board: chess.Board,
        movetime_ms: Optional[int] = None,
    ) -> Optional[chess.Move]:
        if self._engine is None:
            self.start()

        if board.is_game_over():
            return None

        # Safety: never send a board with too few pieces or illegal state
        if len(board.piece_map()) < 2:
            log.warning("Board has too few pieces, skipping engine call")
            return None

        limit = chess.engine.Limit(time=(movetime_ms or DEFAULT_MOVETIME_MS) / 1000.0)

        try:
            result = self._engine.play(board, limit)
            return result.move
        except (chess.engine.EngineTerminatedError, chess.engine.EngineError) as e:
            log.error("Engine error: %s — restarting", e)
            try:
                self._restart()
                # One retry after restart
                result = self._engine.play(board, limit)
                return result.move
            except Exception as e2:
                log.error("Engine still broken after restart: %s", e2)
                return None
        except Exception as e:
            log.error("Unexpected engine error: %s", e)
            return None

    def analyse(
        self,
        board: chess.Board,
        movetime_ms: int = 100,
    ) -> chess.engine.InfoDict:
        if self._engine is None:
            self.start()
        limit = chess.engine.Limit(time=movetime_ms / 1000.0)
        try:
            return self._engine.analyse(board, limit)
        except Exception:
            self._restart()
            return self._engine.analyse(board, limit)

    def __enter__(self) -> "EngineManager":
        self.start()
        return self

    def __exit__(self, *args) -> None:
        self.stop()
