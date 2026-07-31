"""
BoardCanvas — draws the chess board and handles clicks + piece animation.
"""

from __future__ import annotations

import tkinter as tk
from typing import Optional, Callable, Dict
from pathlib import Path

from PIL import Image, ImageTk
import chess

from config import (
    SQUARE_SIZE,
    COORD_MARGIN,
    LIGHT_SQUARE,
    DARK_SQUARE,
    HIGHLIGHT_FROM,
    HIGHLIGHT_TO,
    LAST_MOVE,
    SELECT_COLOR,
    LEGAL_MOVE_DOT,
    CHECK_COLOR,
    COORD_COLOR,
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
        self._board_origin = COORD_MARGIN  # top-left of square a1-area in canvas coords
        size = SQUARE_SIZE * 8 + COORD_MARGIN
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

        # Animation state
        self._animating = False
        self._anim_from: Optional[chess.Square] = None
        self._anim_to: Optional[chess.Square] = None
        self._anim_item: Optional[int] = None  # canvas image id of flying piece
        self._anim_steps = 12
        self._anim_step = 0
        self._anim_start_xy: tuple[float, float] = (0.0, 0.0)
        self._anim_end_xy: tuple[float, float] = (0.0, 0.0)
        self._anim_callback: Optional[Callable[[], None]] = None
        self._anim_piece_key: Optional[str] = None

    def _load_pieces(self) -> None:
        """Load piece images from templates/."""
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
        self._draw_board()
        self._draw_coords()
        self._draw_highlights()
        self._draw_pieces()

    def _draw_board(self) -> None:
        o = self._board_origin
        for row in range(8):
            for col in range(8):
                x1 = o + col * SQUARE_SIZE
                y1 = row * SQUARE_SIZE
                x2 = x1 + SQUARE_SIZE
                y2 = y1 + SQUARE_SIZE
                color = LIGHT_SQUARE if (row + col) % 2 == 0 else DARK_SQUARE
                self.create_rectangle(x1, y1, x2, y2, fill=color, outline="")

    def _draw_coords(self) -> None:
        for col in range(8):
            label = self.controller.file_label(col)
            x = self._board_origin + col * SQUARE_SIZE + SQUARE_SIZE // 2
            y = 8 * SQUARE_SIZE + COORD_MARGIN // 2
            self.create_text(x, y, text=label, fill=COORD_COLOR, font=("Helvetica", 11))

        for row in range(8):
            label = self.controller.rank_label(row)
            x = COORD_MARGIN // 2
            y = row * SQUARE_SIZE + SQUARE_SIZE // 2
            self.create_text(x, y, text=label, fill=COORD_COLOR, font=("Helvetica", 11))

    def _draw_highlights(self) -> None:
        # Last move (played) — bright amber
        if self.controller.last_move:
            for sq in (self.controller.last_move.from_square, self.controller.last_move.to_square):
                self._highlight_square(sq, LAST_MOVE, style="last")

        # Best alternative in review mode — cyan
        best = None
        if hasattr(self.controller, "get_review_best"):
            best = self.controller.get_review_best()
        if best is not None:
            for sq in (best.from_square, best.to_square):
                self._highlight_square(sq, "#22D3EE", style="best")

        # Selected square
        sel = self.controller.get_selected_square()
        if sel is not None:
            self._highlight_square(sel, SELECT_COLOR)

        # King in check
        if self.controller.board.is_check():
            king_sq = self.controller.board.king(self.controller.board.turn)
            if king_sq is not None:
                self._highlight_square(king_sq, CHECK_COLOR, style="check")

        # Animation highlights
        if self._animating:
            if self._anim_from is not None:
                self._highlight_square(self._anim_from, HIGHLIGHT_FROM)
            if self._anim_to is not None:
                self._highlight_square(self._anim_to, HIGHLIGHT_TO)

    def _highlight_square(self, square: chess.Square, color: str, style: str = "soft") -> None:
        row, col = self.controller.square_to_display(square)
        o = self._board_origin
        x1 = o + col * SQUARE_SIZE
        y1 = row * SQUARE_SIZE
        x2 = x1 + SQUARE_SIZE
        y2 = y1 + SQUARE_SIZE

        if style == "last":
            # Strong amber wash + thick border
            self.create_rectangle(x1, y1, x2, y2, fill=color, outline="", stipple="gray25")
            self.create_rectangle(x1 + 2, y1 + 2, x2 - 2, y2 - 2, outline=color, width=3)
        elif style == "best":
            # Cyan wash for suggested best move in review
            self.create_rectangle(x1, y1, x2, y2, fill=color, outline="", stipple="gray25")
            self.create_rectangle(x1 + 2, y1 + 2, x2 - 2, y2 - 2, outline=color, width=3)
        elif style == "check":
            self.create_rectangle(x1, y1, x2, y2, fill=color, outline="", stipple="gray25")
            self.create_rectangle(x1 + 1, y1 + 1, x2 - 1, y2 - 1, outline=color, width=2)
        else:
            self.create_rectangle(x1, y1, x2, y2, fill=color, outline="", stipple="gray50")

    def _draw_pieces(self) -> None:
        for square in chess.SQUARES:
            piece = self.controller.board.piece_at(square)
            if piece is None:
                continue
            # Skip the piece that is currently flying in animation
            if self._animating and square == self._anim_from:
                continue
            key = ("w" if piece.color == chess.WHITE else "b") + piece.symbol().upper()
            img = self._piece_images.get(key)
            if img is None:
                continue
            row, col = self.controller.square_to_display(square)
            o = self._board_origin
            x = o + col * SQUARE_SIZE + SQUARE_SIZE // 2
            y = row * SQUARE_SIZE + SQUARE_SIZE // 2
            self.create_image(x, y, image=img)

        # Draw legal move dots
        if not self._animating:
            for sq in self.controller.get_legal_targets():
                row, col = self.controller.square_to_display(sq)
                o = self._board_origin
                x = o + col * SQUARE_SIZE + SQUARE_SIZE // 2
                y = row * SQUARE_SIZE + SQUARE_SIZE // 2
                r = 8
                self.create_oval(x - r, y - r, x + r, y + r, fill=LEGAL_MOVE_DOT, outline="")

    def _on_click(self, event) -> None:
        if self._animating:
            return
        o = self._board_origin
        col = (event.x - o) // SQUARE_SIZE
        row = event.y // SQUARE_SIZE
        if 0 <= row < 8 and 0 <= col < 8:
            square = self.controller.display_to_square(row, col)
            self.on_square_clicked(square)

    def animate_move(
        self,
        move: chess.Move,
        piece_key: str,
        callback: Optional[Callable[[], None]] = None,
    ) -> None:
        """Animate a piece sliding from from_square to to_square."""
        self._animating = True
        self._anim_from = move.from_square
        self._anim_to = move.to_square
        self._anim_piece_key = piece_key
        self._anim_callback = callback
        self._anim_step = 0

        img = self._piece_images.get(piece_key)
        if img is None:
            self._finish_animation()
            return

        row_f, col_f = self.controller.square_to_display(move.from_square)
        row_t, col_t = self.controller.square_to_display(move.to_square)
        o = self._board_origin
        self._anim_start_xy = (
            o + col_f * SQUARE_SIZE + SQUARE_SIZE / 2,
            row_f * SQUARE_SIZE + SQUARE_SIZE / 2,
        )
        self._anim_end_xy = (
            o + col_t * SQUARE_SIZE + SQUARE_SIZE / 2,
            row_t * SQUARE_SIZE + SQUARE_SIZE / 2,
        )

        # Initial redraw (hides the piece on from-square)
        self.redraw()

        self._anim_item = self.create_image(
            self._anim_start_xy[0], self._anim_start_xy[1], image=img
        )
        self._animate_step()

    def _animate_step(self) -> None:
        if not self._animating:
            return
        self._anim_step += 1
        t = self._anim_step / self._anim_steps
        # ease-out
        t = 1 - (1 - t) ** 2
        x = self._anim_start_xy[0] + (self._anim_end_xy[0] - self._anim_start_xy[0]) * t
        y = self._anim_start_xy[1] + (self._anim_end_xy[1] - self._anim_start_xy[1]) * t
        if self._anim_item is not None:
            self.coords(self._anim_item, x, y)
        if self._anim_step >= self._anim_steps:
            self._finish_animation()
        else:
            self.after(16, self._animate_step)

    def _finish_animation(self) -> None:
        self._animating = False
        self._anim_from = None
        self._anim_to = None
        self._anim_item = None
        callback = self._anim_callback
        self._anim_callback = None
        if callback:
            callback()
        self.redraw()
