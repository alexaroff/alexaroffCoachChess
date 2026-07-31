"""
alexaroffCoachChess — Stockfish engine manager.

Thin wrapper around python-chess.engine.
Supports Elo-based strength via Skill Level + UCI_LimitStrength.
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
    ELO_LEVELS,
)

log = logging.getLogger(__name__)


class EngineManager:
    def __init__(self, path: Optional[str] = None):
        self.path = path or STOCKFISH_PATH
        self._engine: Optional[chess.engine.SimpleEngine] = None
        self._current_elo: Optional[int] = None
        self._movetime_ms: int = 350

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
                "Install via `brew install stockfish` (macOS) / `apt install stockfish` "
                "or set STOCKFISH_PATH env var."
            ) from e
        except Exception as e:
            raise RuntimeError(f"Failed to start Stockfish: {e}") from e

        self._engine.configure({
            "Threads": ENGINE_THREADS,
            "Hash": ENGINE_HASH_MB,
        })
        log.info("Engine ready (Threads=%s, Hash=%s)", ENGINE_THREADS, ENGINE_HASH_MB)

    def stop(self) -> None:
        if self._engine is not None:
            try:
                self._engine.quit()
            except Exception:
                pass
            self._engine = None
            log.info("Engine stopped")

    def set_strength(self, elo: int) -> None:
        """Configure engine for target Elo. Call once per game."""
        if self._engine is None:
            raise RuntimeError("Engine not started")

        cfg = ELO_LEVELS.get(elo, ELO_LEVELS[1600])
        self._movetime_ms = cfg["movetime_ms"]
        self._current_elo = elo

        options: dict = {"Skill Level": cfg["skill"]}

        if cfg.get("limit_strength"):
            options["UCI_LimitStrength"] = True
            options["UCI_Elo"] = cfg.get("elo", elo)
        else:
            options["UCI_LimitStrength"] = False

        try:
            self._engine.configure(options)
            log.info(
                "Strength set: Elo~%s skill=%s movetime=%sms limit=%s",
                elo, cfg["skill"], self._movetime_ms, cfg.get("limit_strength"),
            )
        except Exception as e:
            log.warning("Could not set full strength options (%s), using Skill Level only", e)
            try:
                self._engine.configure({"Skill Level": cfg["skill"]})
            except Exception:
                pass

    def get_best_move(
        self,
        board: chess.Board,
        movetime_ms: Optional[int] = None,
    ) -> Optional[chess.Move]:
        if self._engine is None:
            raise RuntimeError("Engine not started. Call start() first.")

        if board.is_game_over():
            return None

        mt = movetime_ms if movetime_ms is not None else self._movetime_ms
        limit = chess.engine.Limit(time=mt / 1000.0)
        result = self._engine.play(board, limit)
        return result.move

    def analyse(
        self,
        board: chess.Board,
        movetime_ms: int = 100,
    ) -> chess.engine.InfoDict:
        if self._engine is None:
            raise RuntimeError("Engine not started")
        limit = chess.engine.Limit(time=movetime_ms / 1000.0)
        return self._engine.analyse(board, limit)

    def __enter__(self) -> "EngineManager":
        self.start()
        return self

    def __exit__(self, *args) -> None:
        self.stop()
