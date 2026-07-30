"""
GameFrame — main game screen.
"""

from __future__ import annotations

import threading
import customtkinter as ctk
import chess
from typing import Callable, Optional

from ui.board_canvas import BoardCanvas
from game.game_controller import GameController


class GameFrame(ctk.CTkFrame):
    def __init__(
        self,
        master,
        controller: GameController,
        on_new_game: Callable[[], None],
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self.controller = controller
        self.on_new_game = on_new_game
        self.configure(fg_color="#1A1A1A")

        self._bot_thinking = False

        self._build()
        self.board_canvas.redraw()

        # If bot moves first (human is black)
        if not self.controller.is_human_turn:
            self.after(350, self._trigger_bot)

    def _build(self) -> None:
        # Top bar
        top = ctk.CTkFrame(self, fg_color="#242424", height=48, corner_radius=0)
        top.pack(fill="x")
        top.pack_propagate(False)

        self.status_label = ctk.CTkLabel(
            top,
            text=self._status_text(),
            font=ctk.CTkFont(size=14),
            text_color="#EEEEEE",
        )
        self.status_label.pack(side="left", padx=16)

        # Board
        board_container = ctk.CTkFrame(self, fg_color="#1A1A1A")
        board_container.pack(expand=True, pady=16)

        self.board_canvas = BoardCanvas(
            board_container,
            controller=self.controller,
            on_square_clicked=self._on_square_clicked,
        )
        self.board_canvas.pack()

        # Bottom buttons
        bottom = ctk.CTkFrame(self, fg_color="#1A1A1A")
        bottom.pack(fill="x", pady=12)

        ctk.CTkButton(
            bottom,
            text="Сдаться",
            width=120,
            fg_color="#4B5563",
            hover_color="#374151",
            command=self._resign,
        ).pack(side="left", padx=20)

        ctk.CTkButton(
            bottom,
            text="Новая партия",
            width=140,
            fg_color="#3B82F6",
            hover_color="#2563EB",
            command=self.on_new_game,
        ).pack(side="right", padx=20)

    def _status_text(self) -> str:
        if self.controller.is_game_over:
            return self.controller.result_text()
        if self._bot_thinking:
            return "Ход бота…"
        if self.controller.is_human_turn:
            return "Ваш ход"
        return "Ход бота…"

    def _on_square_clicked(self, square: chess.Square) -> None:
        if self._bot_thinking or self.board_canvas._animating:
            return

        changed = self.controller.select_square(square)
        if changed:
            self.board_canvas.redraw()
            self.status_label.configure(text=self._status_text())

            if not self.controller.is_human_turn and not self.controller.is_game_over:
                self.after(60, self._trigger_bot)

    def _trigger_bot(self) -> None:
        if self._bot_thinking or self.controller.is_game_over:
            return

        self._bot_thinking = True
        self.status_label.configure(text="Ход бота…")
        self.update_idletasks()

        def worker() -> None:
            try:
                move = self.controller.request_bot_move()
            except Exception as e:
                self.after(0, lambda: self._on_bot_error(str(e)))
                return

            self.after(0, lambda: self._on_bot_move_ready(move))

        threading.Thread(target=worker, daemon=True).start()

    def _on_bot_move_ready(self, move: Optional[chess.Move]) -> None:
        self._bot_thinking = False

        if move is None:
            self.status_label.configure(text=self._status_text())
            if self.controller.is_game_over:
                self._show_result()
            return

        def after_anim() -> None:
            self.controller.confirm_bot_move(move)
            self.board_canvas.redraw()
            self.status_label.configure(text=self._status_text())
            if self.controller.is_game_over:
                self._show_result()

        self.board_canvas.animate_bot_move(move, after_anim)

    def _on_bot_error(self, msg: str) -> None:
        self._bot_thinking = False
        self.status_label.configure(text="Ошибка движка")
        dialog = ctk.CTkToplevel(self)
        dialog.title("Ошибка")
        dialog.geometry("360x160")
        dialog.configure(fg_color="#1A1A1A")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()
        ctk.CTkLabel(dialog, text=f"Stockfish:\n{msg}", text_color="#FF6B6B").pack(pady=30)
        ctk.CTkButton(dialog, text="OK", command=dialog.destroy).pack()

    def _resign(self) -> None:
        if self._bot_thinking or self.board_canvas._animating:
            return
        self.controller.resign()
        self._show_result()

    def _show_result(self) -> None:
        result = self.controller.result_text()
        dialog = ctk.CTkToplevel(self)
        dialog.title("Партия окончена")
        dialog.geometry("320x180")
        dialog.resizable(False, False)
        dialog.configure(fg_color="#1A1A1A")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text=result,
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#FFFFFF",
        ).pack(pady=(36, 20))

        ctk.CTkButton(
            dialog,
            text="Новая партия",
            width=160,
            height=40,
            fg_color="#3B82F6",
            command=lambda: (dialog.destroy(), self.on_new_game()),
        ).pack()
