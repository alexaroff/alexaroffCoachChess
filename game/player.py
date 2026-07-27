"""
Players: Human and Bot.
"""

from __future__ import annotations

from typing import Optional
import chess

from engine_manager import EngineManager


class HumanPlayer:
    """Human player — moves come from the UI via GameController."""

    def __init__(self, color: chess.Color):
        self.color = color

    def __repr__(self) -> str:
        return f"HumanPlayer({'White' if self.color else 'Black'})"


class BotPlayer:
    """Bot player powered by Stockfish."""

    def __init__(
        self,
        color: chess.Color,
        engine: EngineManager,
        movetime_ms: int,
    ):
        self.color = color
        self.engine = engine
        self.movetime_ms = movetime_ms

    def get_move(self, board: chess.Board) -> Optional[chess.Move]:
        return self.engine.get_best_move(board, movetime_ms=self.movetime_ms)

    def __repr__(self) -> str:
        return f"BotPlayer({'White' if self.color else 'Black'}, {self.movetime_ms}ms)"
