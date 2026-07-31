"""
Game analysis module — Stage 1.

Runs Stockfish deeper than play strength, classifies human moves,
returns structured review data for UI (colors, best moves, board comparison).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional, Callable

import chess
import chess.engine

from engine_manager import EngineManager

log = logging.getLogger(__name__)


# Classification thresholds in pawns (eval loss from mover's perspective)
THRESH_INACCURACY = 0.25
THRESH_MISTAKE = 0.60
THRESH_BLUNDER = 1.50


@dataclass
class MoveReview:
    """Analysis of a single half-move."""

    ply: int                      # 0-based index in move list
    move: chess.Move
    san: str
    is_human: bool
    # Scores always from White's perspective, in pawns (mate ≈ ±100)
    eval_before: float
    eval_after_played: float
    best_move: Optional[chess.Move] = None
    best_san: Optional[str] = None
    eval_after_best: float = 0.0
    loss: float = 0.0             # positive = how much worse than best for the mover
    classification: str = "ok"    # ok | inaccuracy | mistake | blunder

    @property
    def color_tag(self) -> str:
        return {
            "blunder": "blunder",
            "mistake": "mistake",
            "inaccuracy": "inaccuracy",
            "ok": "ok",
        }.get(self.classification, "ok")


def _score_to_pawns(score: chess.engine.PovScore, white_pov: bool = True) -> float:
    """Convert PovScore to float pawns from White's perspective."""
    s = score.white() if white_pov else score.black()
    if s.is_mate():
        mate = s.mate()
        return 100.0 if mate and mate > 0 else -100.0
    cp = s.score()
    if cp is None:
        return 0.0
    return cp / 100.0


def classify_loss(loss: float) -> str:
    if loss >= THRESH_BLUNDER:
        return "blunder"
    if loss >= THRESH_MISTAKE:
        return "mistake"
    if loss >= THRESH_INACCURACY:
        return "inaccuracy"
    return "ok"


class Analyzer:
    """
    Analyses a finished (or ongoing) game move-by-move.

    Only human moves get full classification + best-move suggestion.
    Bot moves are recorded with neutral data for history completeness.
    """

    def __init__(
        self,
        engine: EngineManager,
        movetime_ms: int = 600,
        on_progress: Optional[Callable[[int, int], None]] = None,
    ):
        self.engine = engine
        self.movetime_ms = movetime_ms
        self.on_progress = on_progress

    def analyse_game(
        self,
        moves: List[chess.Move],
        human_color: chess.Color,
        sans: Optional[List[str]] = None,
    ) -> List[MoveReview]:
        """
        Replay the game from the start, analyse each position before a human move.

        Returns list of MoveReview, one per half-move.
        """
        if not moves:
            return []

        board = chess.Board()
        reviews: List[MoveReview] = []
        total = len(moves)

        for ply, move in enumerate(moves):
            if self.on_progress:
                self.on_progress(ply + 1, total)

            is_human = board.turn == human_color
            san = sans[ply] if sans and ply < len(sans) else board.san(move)

            if not is_human:
                reviews.append(
                    MoveReview(
                        ply=ply,
                        move=move,
                        san=san,
                        is_human=False,
                        eval_before=0.0,
                        eval_after_played=0.0,
                        classification="ok",
                    )
                )
                board.push(move)
                continue

            try:
                info = self.engine.analyse(board, movetime_ms=self.movetime_ms)
            except Exception as e:
                log.warning("Analyse failed at ply %s: %s", ply, e)
                reviews.append(
                    MoveReview(
                        ply=ply,
                        move=move,
                        san=san,
                        is_human=True,
                        eval_before=0.0,
                        eval_after_played=0.0,
                        classification="ok",
                    )
                )
                board.push(move)
                continue

            score_before = info.get("score")
            eval_before = _score_to_pawns(score_before) if score_before else 0.0

            pv = info.get("pv") or []
            best_move = pv[0] if pv else None
            best_san = board.san(best_move) if best_move else None

            eval_after_best = eval_before

            board.push(move)
            try:
                info_after = self.engine.analyse(board, movetime_ms=max(200, self.movetime_ms // 2))
                score_after = info_after.get("score")
                eval_after_played = _score_to_pawns(score_after) if score_after else eval_before
            except Exception:
                eval_after_played = eval_before

            if human_color == chess.WHITE:
                loss = eval_after_best - eval_after_played
            else:
                loss = eval_after_played - eval_after_best
            loss = max(0.0, loss)

            classification = classify_loss(loss)

            reviews.append(
                MoveReview(
                    ply=ply,
                    move=move,
                    san=san,
                    is_human=True,
                    eval_before=eval_before,
                    eval_after_played=eval_after_played,
                    best_move=best_move,
                    best_san=best_san,
                    eval_after_best=eval_after_best,
                    loss=loss,
                    classification=classification,
                )
            )

        if self.on_progress:
            self.on_progress(total, total)

        return reviews


def summary_text(reviews: List[MoveReview]) -> str:
    """Short human-readable summary of the analysis."""
    human = [r for r in reviews if r.is_human]
    if not human:
        return "Нет ходов для разбора"
    blunders = sum(1 for r in human if r.classification == "blunder")
    mistakes = sum(1 for r in human if r.classification == "mistake")
    inacc = sum(1 for r in human if r.classification == "inaccuracy")
    parts = []
    if blunders:
        parts.append(f"зевков: {blunders}")
    if mistakes:
        parts.append(f"ошибок: {mistakes}")
    if inacc:
        parts.append(f"неточностей: {inacc}")
    if not parts:
        return "Ходов без серьёзных ошибок"
    return " · ".join(parts)
