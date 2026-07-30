"""
GameController — central logic of a single game.
"""

from __future__ import annotations

import logging
from typing import Optional, Callable, Tuple
import chess

from config import MASTER_MOVETIME_MS, MASTER_PLUS_MOVETIME_MS
from engine_manager import EngineManager
from game.player import HumanPlayer, BotPlayer

log = logging.getLogger(__name__)


class GameController:
    """
    Manages one game:
    - board state
    - whose turn
    - human / bot players
    - game over detection
    """

    def __init__(
        self,
        human_color: chess.Color,
        human_at_bottom: bool,
        strength: str,                    # "master" | "master_plus"
        engine: EngineManager,
        on_bot_move_start: Optional[Callable[[chess.Move], None]] = None,
        on_bot_move_end: Optional[Callable[[chess.Move], None]] = None,
        on_game_over: Optional[Callable[[str], None]] = None,
    ):
        self.board = chess.Board()
        self.human_color = human_color
        self.human_at_bottom = human_at_bottom
        self.strength = strength
        self.engine = engine

        movetime = MASTER_PLUS_MOVETIME_MS if strength == "master_plus" else MASTER_MOVETIME_MS
        bot_color = not human_color

        self.human = HumanPlayer(human_color)
        self.bot = BotPlayer(bot_color, engine, movetime)

        self.on_bot_move_start = on_bot_move_start
        self.on_bot_move_end = on_bot_move_end
        self.on_game_over = on_game_over

        self._selected_square: Optional[chess.Square] = None
        self.last_move: Optional[chess.Move] = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------
    @property
    def is_human_turn(self) -> bool:
        return self.board.turn == self.human_color and not self.board.is_game_over()

    @property
    def is_game_over(self) -> bool:
        return self.board.is_game_over()

    def result_text(self) -> str:
        if not self.board.is_game_over():
            return ""
        outcome = self.board.outcome()
        if outcome is None:
            return "Игра окончена"
        if outcome.winner is None:
            return "Ничья"
        if outcome.winner == self.human_color:
            return "Вы победили!"
        return "Вы проиграли"

    # ------------------------------------------------------------------
    # Orientation helpers
    # ------------------------------------------------------------------
    def square_to_display(self, square: chess.Square) -> Tuple[int, int]:
        """Return (row, col) for drawing. row 0 is top of the widget."""
        rank = chess.square_rank(square)
        file = chess.square_file(square)
        if self.human_at_bottom:
            if self.human_color == chess.WHITE:
                row = 7 - rank
                col = file
            else:
                row = rank
                col = 7 - file
        else:
            if self.human_color == chess.WHITE:
                row = rank
                col = 7 - file
            else:
                row = 7 - rank
                col = file
        return row, col

    def display_to_square(self, row: int, col: int) -> chess.Square:
        """Inverse of square_to_display."""
        if self.human_at_bottom:
            if self.human_color == chess.WHITE:
                rank = 7 - row
                file = col
            else:
                rank = row
                file = 7 - col
        else:
            if self.human_color == chess.WHITE:
                rank = row
                file = 7 - col
            else:
                rank = 7 - row
                file = col
        return chess.square(file, rank)

    # ------------------------------------------------------------------
    # Move handling
    # ------------------------------------------------------------------
    def select_square(self, square: chess.Square) -> bool:
        """
        Handle a click on a square.
        Returns True if the board should be redrawn.
        Does NOT trigger the bot — UI is responsible for that.
        """
        if not self.is_human_turn:
            return False

        piece = self.board.piece_at(square)

        # First click — select own piece
        if self._selected_square is None:
            if piece and piece.color == self.human_color:
                self._selected_square = square
                return True
            return False

        # Second click
        from_sq = self._selected_square
        self._selected_square = None

        # Clicked same square → deselect
        if square == from_sq:
            return True

        # Clicked another own piece → reselect
        if piece and piece.color == self.human_color:
            self._selected_square = square
            return True

        # Try to make a move
        move = chess.Move(from_sq, square)

        # Handle promotion (always queen for simplicity in MVP)
        piece_at_from = self.board.piece_at(from_sq)
        if piece_at_from and piece_at_from.piece_type == chess.PAWN:
            if (self.human_color == chess.WHITE and chess.square_rank(square) == 7) or \
               (self.human_color == chess.BLACK and chess.square_rank(square) == 0):
                move = chess.Move(from_sq, square, promotion=chess.QUEEN)

        if move in self.board.legal_moves:
            self._make_move(move)
            return True

        return True  # deselect even on illegal

    def get_selected_square(self) -> Optional[chess.Square]:
        return self._selected_square

    def get_legal_targets(self) -> list[chess.Square]:
        if self._selected_square is None:
            return []
        return [m.to_square for m in self.board.legal_moves if m.from_square == self._selected_square]

    def _make_move(self, move: chess.Move) -> None:
        """Push human move. Does NOT request bot move — UI decides when to call request_bot_move."""
        self.board.push(move)
        self.last_move = move
        self._selected_square = None
        log.info("Human move: %s", move.uci())

        if self.board.is_game_over() and self.on_game_over:
            self.on_game_over(self.result_text())

    def request_bot_move(self) -> Optional[chess.Move]:
        """
        Compute bot's best move (blocking).
        Call this from a background thread.
        Returns the move or None if game over / no move.
        """
        if self.is_human_turn or self.is_game_over:
            return None

        move = self.bot.get_move(self.board)
        if move is None:
            return None

        if self.on_bot_move_start:
            self.on_bot_move_start(move)

        return move

    def confirm_bot_move(self, move: chess.Move) -> None:
        """Called by UI after animation finishes. Pushes the move to the board."""
        if move not in self.board.legal_moves:
            log.warning("Attempted to confirm illegal bot move: %s", move.uci())
            return

        self.board.push(move)
        self.last_move = move
        log.info("Bot move: %s", move.uci())

        if self.on_bot_move_end:
            self.on_bot_move_end(move)

        if self.board.is_game_over() and self.on_game_over:
            self.on_game_over(self.result_text())

    def resign(self) -> None:
        """Human resigns."""
        if self.on_game_over:
            self.on_game_over("Вы сдались")
