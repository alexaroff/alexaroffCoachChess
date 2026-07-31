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
    ):
        self.color = color
        self.engine = engine

    def get_move(self, board: chess.Board) -> Optional[chess.Move]:
        return self.engine.get_best_move(board)

    def __repr__(self) -> str:
        return f"BotPlayer({'White' if self.color else 'Black'})"
