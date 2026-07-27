"""
BoardCanvas — draws the chess board and handles clicks.
"""

from __future__ import annotations

import tkinter as tk
from typing import Optional, Callable, Dict
from pathlib import Path

from PIL import Image, ImageTk
import chess

from config import (
    SQUARE_SIZE,
    LIGHT_SQUARE,
    DARK_SQUARE,
    HIGHLIGHT_FROM,
    HIGHLIGHT_TO,
    LAST_MOVE,
    SELECT_COLOR,
    LEGAL_MOVE_DOT,
    TEMPLATES_DIR,
)


class BoardCanvas(tk.Canvas):
    def __init__(
        self,
        master,
        controller,
        on_square_clicked: Callable[[chess.Square], None],
        **kwargs,
    ):
        size = SQUARE_SIZE * 8
        super().__init__(
            master,
            width=size,
            height=size,
            highlightthickness=0,
            bg="#1A1A1A",
            **kwargs,
        )
        self.controller = controller
        self.on_square_clicked = on_square_clicked
        self._piece_images: Dict[str, ImageTk.PhotoImage] = {}
        self._load_pieces()
        self.bind("<Button-1>", self._on_click)

        self._animating = False
        self._anim_from: Optional[chess.Square] = None
        self._anim_to: Optional[chess.Square] = None

    def _load_pieces(self) -> None:
        mapping = {
            "wP": "wP.png", "wN": "wN.png", "wB": "wB.png",
            "wR": "wR.png", "wQ": "wQ.png", "wK": "wK.png",
            "bP": "bP.png", "bN": "bN.png", "bB": "bB.png",
            "bR": "bR.png", "bQ": "bQ.png", "bK": "bK.png",
        }
        for key, filename in mapping.items():
            path = TEMPLATES_DIR / filename
            if path.exists():
                img = Image.open(path).convert("RGBA")
                img = img.resize((SQUARE_SIZE - 8, SQUARE_SIZE - 8), Image.LANCZOS)
                self._piece_images[key] = ImageTk.PhotoImage(img)

    def redraw(self) -> None:
        self.delete("all")
        self._draw_squares()
        self._draw_highlights()
        self._draw_pieces()
        self._draw_legal_dots()

    def _draw_squares(self) -> None:
        for row in range(8):
            for col in range(8):
                x1 = col * SQUARE_SIZE
                y1 = row * SQUARE_SIZE
                x2 = x1 + SQUARE_SIZE
                y2 = y1 + SQUARE_SIZE
                color = LIGHT_SQUARE if (row + col) % 2 == 0 else DARK_SQUARE
                self.create_rectangle(x1, y1, x2, y2, fill=color, outline="")

    def _draw_highlights(self) -> None:
        if self.controller.last_move:
            for sq in (self.controller.last_move.from_square, self.controller.last_move.to_square):
                self._highlight_square(sq, LAST_MOVE)

        sel = self.controller.get_selected_square()
        if sel is not None:
            self._highlight_square(sel, SELECT_COLOR)

        if self._animating:
            if self._anim_from is not None:
                self._highlight_square(self._anim_from, HIGHLIGHT_FROM)
            if self._anim_to is not None:
                self._highlight_square(self._anim_to, HIGHLIGHT_TO)

    def _highlight_square(self, square: chess.Square, color: str) -> None:
        row, col = self.controller.square_to_display(square)
        x1 = col * SQUARE_SIZE
        y1 = row * SQUARE_SIZE
        self.create_rectangle(
            x1, y1, x1 + SQUARE_SIZE, y1 + SQUARE_SIZE,
            fill=color, outline="", stipple="gray50"
        )

    def _draw_pieces(self) -> None:
        for square in chess.SQUARES:
            piece = self.controller.board.piece_at(square)
            if piece is None:
                continue
            if self._animating and square == self._anim_from:
                continue
            key = ("w" if piece.color == chess.WHITE else "b") + piece.symbol().upper()
            img = self._piece_images.get(key)
            if img is None:
                continue
            row, col = self.controller.square_to_display(square)
            x = col * SQUARE_SIZE + SQUARE_SIZE // 2
            y = row * SQUARE_SIZE + SQUARE_SIZE // 2
            self.create_image(x, y, image=img)

    def _draw_legal_dots(self) -> None:
        for sq in self.controller.get_legal_targets():
            row, col = self.controller.square_to_display(sq)
            cx = col * SQUARE_SIZE + SQUARE_SIZE // 2
            cy = row * SQUARE_SIZE + SQUARE_SIZE // 2
            r = 8
            self.create_oval(cx - r, cy - r, cx + r, cy + r, fill=LEGAL_MOVE_DOT, outline="")

    def _on_click(self, event) -> None:
        if self._animating:
            return
        col = event.x // SQUARE_SIZE
        row = event.y // SQUARE_SIZE
        if 0 <= row < 8 and 0 <= col < 8:
            square = self.controller.display_to_square(row, col)
            self.on_square_clicked(square)

    def animate_bot_move(self, move: chess.Move, on_finished: Callable[[], None]) -> None:
        self._animating = True
        self._anim_from = move.from_square
        self._anim_to = move.to_square
        self.redraw()
        self.after(280, lambda: self._finish_animation(on_finished))

    def _finish_animation(self, on_finished: Callable[[], None]) -> None:
        self._animating = False
        self._anim_from = None
        self._anim_to = None
        on_finished()
        self.redraw()
