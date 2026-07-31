"""
GameController — central logic of a single game.
"""

from __future__ import annotations

import logging
from typing import Optional, Callable, Tuple, List
import chess

from engine_manager import EngineManager
from game.player import HumanPlayer, BotPlayer

log = logging.getLogger(__name__)

_UNICODE = {
    (chess.WHITE, chess.PAWN):   "♙",
    (chess.WHITE, chess.KNIGHT): "♘",
    (chess.WHITE, chess.BISHOP): "♗",
    (chess.WHITE, chess.ROOK):   "♖",
    (chess.WHITE, chess.QUEEN):  "♕",
    (chess.BLACK, chess.PAWN):   "♟",
    (chess.BLACK, chess.KNIGHT): "♞",
    (chess.BLACK, chess.BISHOP): "♝",
    (chess.BLACK, chess.ROOK):   "♜",
    (chess.BLACK, chess.QUEEN):  "♛",
}


class GameController:
    def __init__(
        self,
        human_color: chess.Color,
        human_at_bottom: bool,
        elo: int,
        engine: EngineManager,
        on_bot_move_start: Optional[Callable[[chess.Move], None]] = None,
        on_bot_move_end: Optional[Callable[[chess.Move], None]] = None,
        on_game_over: Optional[Callable[[str], None]] = None,
    ):
        self.board = chess.Board()
        self.human_color = human_color
        self.human_at_bottom = human_at_bottom
        self.elo = elo
        self.engine = engine

        engine.set_strength(elo)

        bot_color = not human_color
        self.human = HumanPlayer(human_color)
        self.bot = BotPlayer(bot_color, engine)

        self.on_bot_move_start = on_bot_move_start
        self.on_bot_move_end = on_bot_move_end
        self.on_game_over = on_game_over

        self._selected_square: Optional[chess.Square] = None
        self.last_move: Optional[chess.Move] = None
        self.last_san: Optional[str] = None
        self.move_sans: list[str] = []
        self._pending_promotion: Optional[tuple[chess.Square, chess.Square]] = None

        self.white_captured: List[tuple[bool, chess.PieceType]] = []
        self.black_captured: List[tuple[bool, chess.PieceType]] = []
        self._draw_agreed = False
        self._resigned = False

    @property
    def is_human_turn(self) -> bool:
        return self.board.turn == self.human_color and not self.is_game_over

    @property
    def is_game_over(self) -> bool:
        return self.board.is_game_over() or self._draw_agreed or self._resigned

    def result_text(self) -> str:
        if self._draw_agreed:
            return "Ничья (по соглашению)"
        if self._resigned:
            return "Вы сдались"
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

    def square_to_display(self, square: chess.Square) -> Tuple[int, int]:
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

    def file_label(self, col: int) -> str:
        sq = self.display_to_square(7, col)
        return chess.FILE_NAMES[chess.square_file(sq)]

    def rank_label(self, row: int) -> str:
        sq = self.display_to_square(row, 0)
        return chess.RANK_NAMES[chess.square_rank(sq)]

    def _record_capture(self, move: chess.Move) -> None:
        captured = None
        if self.board.is_en_passant(move):
            cap_sq = move.to_square + (-8 if self.board.turn == chess.WHITE else 8)
            captured = self.board.piece_at(cap_sq)
        elif self.board.is_capture(move):
            captured = self.board.piece_at(move.to_square)
        if captured is None:
            return
        entry = (captured.color, captured.piece_type)
        if self.board.turn == chess.WHITE:
            self.white_captured.append(entry)
        else:
            self.black_captured.append(entry)

    def captured_text(self, for_white: bool) -> str:
        lst = self.white_captured if for_white else self.black_captured
        order = {chess.QUEEN: 0, chess.ROOK: 1, chess.BISHOP: 2, chess.KNIGHT: 3, chess.PAWN: 4}
        sorted_lst = sorted(lst, key=lambda x: order.get(x[1], 9))
        return "".join(_UNICODE.get(item, "?") for item in sorted_lst)

    def select_square(self, square: chess.Square):
        if not self.is_human_turn:
            return False
        piece = self.board.piece_at(square)
        if self._selected_square is None:
            if piece and piece.color == self.human_color:
                self._selected_square = square
                return True
            return False
        from_sq = self._selected_square
        self._selected_square = None
        if square == from_sq:
            return True
        if piece and piece.color == self.human_color:
            self._selected_square = square
            return True
        piece_at_from = self.board.piece_at(from_sq)
        needs_promo = False
        if piece_at_from and piece_at_from.piece_type == chess.PAWN:
            if (self.human_color == chess.WHITE and chess.square_rank(square) == 7) or \
               (self.human_color == chess.BLACK and chess.square_rank(square) == 0):
                needs_promo = True
        if needs_promo:
            promo_moves = [
                chess.Move(from_sq, square, promotion=p)
                for p in (chess.QUEEN, chess.ROOK, chess.BISHOP, chess.KNIGHT)
            ]
            if any(m in self.board.legal_moves for m in promo_moves):
                self._pending_promotion = (from_sq, square)
                return "promotion"
            return True
        move = chess.Move(from_sq, square)
        if move in self.board.legal_moves:
            self._make_move(move)
            return True
        return True

    def get_selected_square(self) -> Optional[chess.Square]:
        return self._selected_square

    def get_legal_targets(self) -> list[chess.Square]:
        if self._selected_square is None:
            return []
        return [m.to_square for m in self.board.legal_moves if m.from_square == self._selected_square]

    def _make_move(self, move: chess.Move) -> None:
        san = self.board.san(move)
        self._record_capture(move)
        self.board.push(move)
        self.last_move = move
        self.last_san = san
        self.move_sans.append(san)
        self._selected_square = None
        self._pending_promotion = None
        log.info("Human move: %s (%s)", move.uci(), san)
        if self.board.is_game_over() and self.on_game_over:
            self.on_game_over(self.result_text())

    def request_bot_move(self) -> Optional[chess.Move]:
        if self.is_human_turn or self.is_game_over:
            return None
        move = self.bot.get_move(self.board)
        if move is None:
            return None
        if self.on_bot_move_start:
            self.on_bot_move_start(move)
        return move

    def confirm_bot_move(self, move: chess.Move) -> None:
        if move not in self.board.legal_moves:
            log.warning("Attempted to confirm illegal bot move: %s", move.uci())
            return
        san = self.board.san(move)
        self._record_capture(move)
        self.board.push(move)
        self.last_move = move
        self.last_san = san
        self.move_sans.append(san)
        log.info("Bot move: %s (%s)", move.uci(), san)
        if self.on_bot_move_end:
            self.on_bot_move_end(move)
        if self.board.is_game_over() and self.on_game_over:
            self.on_game_over(self.result_text())

    def confirm_promotion(self, piece_type: chess.PieceType) -> bool:
        if self._pending_promotion is None:
            return False
        from_sq, to_sq = self._pending_promotion
        move = chess.Move(from_sq, to_sq, promotion=piece_type)
        if move not in self.board.legal_moves:
            self._pending_promotion = None
            return False
        self._make_move(move)
        return True

    def cancel_promotion(self) -> None:
        self._pending_promotion = None
        self._selected_square = None

    def undo(self) -> bool:
        if not self.board.move_stack:
            return False
        if self.board.turn == self.human_color:
            self.board.pop()
            if self.move_sans:
                self.move_sans.pop()
            if self.board.move_stack:
                self.board.pop()
                if self.move_sans:
                    self.move_sans.pop()
        else:
            self.board.pop()
            if self.move_sans:
                self.move_sans.pop()
        self._rebuild_captured()
        self.last_move = self.board.move_stack[-1] if self.board.move_stack else None
        self.last_san = self.move_sans[-1] if self.move_sans else None
        self._selected_square = None
        self._pending_promotion = None
        log.info("Undo → %s plies, human_to_move=%s", len(self.board.move_stack), self.is_human_turn)
        return True

    def _rebuild_captured(self) -> None:
        self.white_captured.clear()
        self.black_captured.clear()
        tmp = chess.Board()
        for move in self.board.move_stack:
            captured = None
            if tmp.is_en_passant(move):
                cap_sq = move.to_square + (-8 if tmp.turn == chess.WHITE else 8)
                captured = tmp.piece_at(cap_sq)
            elif tmp.is_capture(move):
                captured = tmp.piece_at(move.to_square)
            if captured is not None:
                entry = (captured.color, captured.piece_type)
                if tmp.turn == chess.WHITE:
                    self.white_captured.append(entry)
                else:
                    self.black_captured.append(entry)
            tmp.push(move)

    def history_text(self) -> str:
        if not self.move_sans:
            return ""
        parts: list[str] = []
        for i, san in enumerate(self.move_sans):
            if i % 2 == 0:
                parts.append(f"{i // 2 + 1}. {san}")
            else:
                parts.append(san)
        return "  ".join(parts)

    def resign(self) -> None:
        if self.is_game_over:
            return
        self._resigned = True
        if self.on_game_over:
            self.on_game_over(self.result_text())

    def offer_draw(self) -> None:
        """Human offers draw — bot always accepts."""
        if self.is_game_over:
            return
        self._draw_agreed = True
        if self.on_game_over:
            self.on_game_over(self.result_text())
