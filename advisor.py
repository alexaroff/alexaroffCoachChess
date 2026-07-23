"""
alexaroffCoachChess — lightweight strategic advisor.

No neural nets, no heavy computation.
Gives short Russian tips based on game phase + simple chess principles.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import chess


@dataclass
class Advice:
    phase: str          # "opening" | "middlegame" | "endgame"
    text: str           # short tip in Russian
    move_uci: Optional[str] = None


class Advisor:
    """
    Stateless helper. Call advice(board, best_move) after engine returns a move.
    """

    def advice(self, board: chess.Board, best_move: Optional[chess.Move] = None) -> Advice:
        phase = self._phase(board)
        text = self._tip(board, phase, best_move)
        return Advice(
            phase=phase,
            text=text,
            move_uci=best_move.uci() if best_move else None,
        )

    def game_over(self, board: chess.Board) -> Advice:
        if board.is_checkmate():
            winner = "белые" if board.turn == chess.BLACK else "чёрные"
            return Advice(phase="endgame", text=f"Мат! Победили {winner}.")
        if board.is_stalemate():
            return Advice(phase="endgame", text="Пат. Ничья.")
        if board.is_insufficient_material():
            return Advice(phase="endgame", text="Недостаточно материала. Ничья.")
        return Advice(phase="endgame", text="Партия окончена.")

    # ------------------------------------------------------------------

    def _phase(self, board: chess.Board) -> str:
        """Very simple phase detection by piece count + queens."""
        pieces = board.piece_map()
        total = len(pieces)
        has_queen = any(p.piece_type == chess.QUEEN for p in pieces.values())

        if total >= 28 and has_queen:
            return "opening"
        if total <= 12 or not has_queen:
            return "endgame"
        return "middlegame"

    def _tip(
        self,
        board: chess.Board,
        phase: str,
        move: Optional[chess.Move],
    ) -> str:
        # Priority checks (most important first)
        if board.is_check():
            return "Шах! Нужно защитить короля."

        if phase == "opening":
            return self._opening_tip(board, move)
        if phase == "endgame":
            return self._endgame_tip(board, move)
        return self._middlegame_tip(board, move)

    def _opening_tip(self, board: chess.Board, move: Optional[chess.Move]) -> str:
        # King still in center?
        for color, name in ((chess.WHITE, "белых"), (chess.BLACK, "чёрных")):
            king_sq = board.king(color)
            if king_sq is not None and chess.square_file(king_sq) in (3, 4) and chess.square_rank(king_sq) in (0, 7):
                # still on e1/e8-ish
                if not board.has_castling_rights(color):
                    pass  # already moved or lost rights
                else:
                    if color == board.turn:
                        return "В дебюте важна безопасность короля — подумай о рокировке."

        # Development
        undeveloped = 0
        back_rank = 0 if board.turn == chess.WHITE else 7
        for file in (1, 2, 5, 6):  # b, c, f, g — knights & bishops
            sq = chess.square(file, back_rank)
            p = board.piece_at(sq)
            if p is not None and p.color == board.turn and p.piece_type in (chess.KNIGHT, chess.BISHOP):
                undeveloped += 1
        if undeveloped >= 2:
            return "Развивай фигуры. Кони и слоны должны выйти с последней линии."

        # Early queen
        if move:
            p = board.piece_at(move.from_square)
            if p and p.piece_type == chess.QUEEN:
                return "Ранний выход ферзя часто даёт сопернику темпы. Будь осторожен."

        # Center control
        center = [chess.D4, chess.E4, chess.D5, chess.E5]
        our_center = sum(
            1 for sq in center
            if board.piece_at(sq) and board.piece_at(sq).color == board.turn
        )
        if our_center == 0:
            return "Борись за центр (d4/e4/d5/e5). Центр — ключ к преимуществу."

        return "В дебюте: центр, развитие, король. Не делай слишком много ходов одной фигурой."

    def _middlegame_tip(self, board: chess.Board, move: Optional[chess.Move]) -> str:
        if board.is_check():
            return "Шах. Ищи способы увеличить давление."

        # Hanging pieces (very rough)
        if move:
            to_sq = move.to_square
            # if we move to a square attacked more than defended — warn
            attackers = len(board.attackers(not board.turn, to_sq))
            defenders = len(board.attackers(board.turn, to_sq))
            if attackers > defenders:
                return "Клетка, куда идёт фигура, слабо защищена. Проверь тактику."

        # King safety
        king_sq = board.king(board.turn)
        if king_sq is not None:
            attackers = len(board.attackers(not board.turn, king_sq))
            if attackers >= 1:
                return "Король под давлением. Укрепи защиту или уведи его."

        return "Миттельшпиль: ищи слабости, улучшай фигуры, считай тактику."

    def _endgame_tip(self, board: chess.Board, move: Optional[chess.Move]) -> str:
        # Activate king
        king_sq = board.king(board.turn)
        if king_sq is not None:
            rank = chess.square_rank(king_sq)
            if board.turn == chess.WHITE and rank <= 1:
                return "В эндшпиле король — сильная фигура. Веди его в центр."
            if board.turn == chess.BLACK and rank >= 6:
                return "В эндшпиле король — сильная фигура. Веди его в центр."

        # Passed pawns
        if move:
            p = board.piece_at(move.from_square)
            if p and p.piece_type == chess.PAWN:
                return "Пешки в эндшпиле решают. Поддержи проходную."

        return "Эндшпиль: активируй короля, проводи пешки, не спеши."
