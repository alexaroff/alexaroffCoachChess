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
        self._bot_generation = 0  # increments on undo / new game start to ignore stale results

        self._build()
        self.board_canvas.redraw()

        # If bot moves first (human is black)
        if not self.controller.is_human_turn:
            self.after(350, self._trigger_bot)

    def _build(self) -> None:
        # Top bar
        top = ctk.CTkFrame(self, fg_color="#242424", height=52, corner_radius=0)
        top.pack(fill="x")
        top.pack_propagate(False)

        self.status_label = ctk.CTkLabel(
            top,
            text=self._status_text(),
            font=ctk.CTkFont(size=14),
            text_color="#EEEEEE",
        )
        self.status_label.pack(side="left", padx=16)

        # Captured pieces (right side of top bar)
        self.captured_label = ctk.CTkLabel(
            top,
            text="",
            font=ctk.CTkFont(size=16),
            text_color="#CCCCCC",
        )
        self.captured_label.pack(side="right", padx=16)

        # Board
        board_container = ctk.CTkFrame(self, fg_color="#1A1A1A")
        board_container.pack(expand=True, pady=16)

        self.board_canvas = BoardCanvas(
            board_container,
            controller=self.controller,
            on_square_clicked=self._on_square_clicked,
        )
        self.board_canvas.pack()

        # Move history
        hist_frame = ctk.CTkFrame(self, fg_color="#242424", corner_radius=8)
        hist_frame.pack(fill="x", padx=20, pady=(4, 0))

        ctk.CTkLabel(
            hist_frame,
            text="Ходы",
            font=ctk.CTkFont(size=12),
            text_color="#888888",
        ).pack(anchor="w", padx=10, pady=(6, 0))

        self.history_box = ctk.CTkTextbox(
            hist_frame,
            height=72,
            font=ctk.CTkFont(size=13),
            fg_color="#1E1E1E",
            text_color="#DDDDDD",
            activate_scrollbars=True,
            wrap="word",
        )
        self.history_box.pack(fill="x", padx=8, pady=(2, 8))
        self.history_box.configure(state="disabled")

        # Bottom buttons
        bottom = ctk.CTkFrame(self, fg_color="#1A1A1A")
        bottom.pack(fill="x", pady=12)

        ctk.CTkButton(
            bottom,
            text="Сдаться",
            width=90,
            fg_color="#4B5563",
            hover_color="#374151",
            command=self._resign,
        ).pack(side="left", padx=(12, 4))

        ctk.CTkButton(
            bottom,
            text="Ничья",
            width=80,
            fg_color="#4B5563",
            hover_color="#374151",
            command=self._offer_draw,
        ).pack(side="left", padx=4)

        ctk.CTkButton(
            bottom,
            text="Отменить",
            width=90,
            fg_color="#4B5563",
            hover_color="#374151",
            command=self._undo,
        ).pack(side="left", padx=4)

        self.analyze_btn = ctk.CTkButton(
            bottom,
            text="Разбор",
            width=90,
            fg_color="#059669",
            hover_color="#047857",
            command=self._start_analysis,
            state="disabled",
        )
        self.analyze_btn.pack(side="left", padx=4)

        ctk.CTkButton(
            bottom,
            text="Новая",
            width=90,
            fg_color="#3B82F6",
            hover_color="#2563EB",
            command=self.on_new_game,
        ).pack(side="right", padx=12)

        # Analysis progress (hidden by default)
        self.progress_label = ctk.CTkLabel(
            self,
            text="",
            font=ctk.CTkFont(size=12),
            text_color="#AAAAAA",
        )
        self.progress_label.pack(pady=(0, 4))

        self._analyzing = False
        self._analysis_generation = 0

    def _status_text(self) -> str:
        from config import MODE_LABELS
        mode_label = MODE_LABELS.get(self.controller.mode, "")
        prefix = f"{mode_label}  ·  " if mode_label else ""

        if self.controller.is_game_over:
            return prefix + self.controller.result_text()
        san = self.controller.last_san
        suffix = f"  ·  {san}" if san else ""
        if self._bot_thinking:
            return prefix + "Ход бота…" + suffix
        if self.controller.is_human_turn:
            return prefix + "Ваш ход" + suffix
        return prefix + "Ход бота…" + suffix

    def _refresh_history(self) -> None:
        self.history_box.configure(state="normal")
        self.history_box.delete("1.0", "end")
        txt = self.controller.history_text()
        if txt:
            self.history_box.insert("1.0", txt)
        self.history_box.configure(state="disabled")
        self.history_box.see("end")

    def _refresh_captured(self) -> None:
        # Show what each side has captured
        # Human's captures vs bot's captures for clarity
        if self.controller.human_color == chess.WHITE:
            you = self.controller.captured_text(for_white=True)
            bot = self.controller.captured_text(for_white=False)
        else:
            you = self.controller.captured_text(for_white=False)
            bot = self.controller.captured_text(for_white=True)
        parts = []
        if you:
            parts.append(f"Вы: {you}")
        if bot:
            parts.append(f"Бот: {bot}")
        self.captured_label.configure(text="   ".join(parts))

    def _on_square_clicked(self, square: chess.Square) -> None:

        if self._bot_thinking or self.board_canvas._animating or self._analyzing:
            return
        if self.controller.is_reviewing():
            # Any board click exits review and restores full game position
            self.controller.exit_review()
            self.board_canvas.redraw()
            self.status_label.configure(text=self._status_text())
            return

        result = self.controller.select_square(square)

        if result == "promotion":
            self.board_canvas.redraw()
            self._show_promotion_dialog()
            return

        if result:
            self.board_canvas.redraw()
            self.status_label.configure(text=self._status_text())
            self._refresh_history()
            self._refresh_captured()

            if not self.controller.is_human_turn and not self.controller.is_game_over:
                self.after(60, self._trigger_bot)

    def _trigger_bot(self) -> None:
        if self._bot_thinking or self.controller.is_game_over:
            return

        self._bot_thinking = True
        self.status_label.configure(text="Ход бота…")
        self.update_idletasks()

        gen = self._bot_generation

        def worker() -> None:
            try:
                move = self.controller.request_bot_move()
            except Exception as e:
                self.after(0, lambda: self._on_bot_error(str(e)))
                return

            self.after(0, lambda: self._on_bot_move_ready(move, gen))

        threading.Thread(target=worker, daemon=True).start()

    def _on_bot_move_ready(self, move: Optional[chess.Move], gen: int) -> None:
        # Stale result after undo — ignore
        if gen != self._bot_generation:
            self._bot_thinking = False
            return

        self._bot_thinking = False

        if move is None:
            self.status_label.configure(text=self._status_text())
            if self.controller.is_game_over:
                self._show_result()
            return

        def after_anim() -> None:
            if gen != self._bot_generation:
                return
            self.controller.confirm_bot_move(move)
            self.board_canvas.redraw()
            self.status_label.configure(text=self._status_text())
            self._refresh_history()
            self._refresh_captured()
            if self.controller.is_game_over:
                self._show_result()

        # Animate bot move
        piece = self.controller.board.piece_at(move.from_square)
        if piece:
            key = ("w" if piece.color == chess.WHITE else "b") + piece.symbol().upper()
            self.board_canvas.animate_move(move, key, callback=after_anim)
        else:
            after_anim()

    def _on_bot_error(self, msg: str) -> None:
        self._bot_thinking = False
        self.status_label.configure(text=f"Ошибка бота: {msg[:40]}")

    def _show_promotion_dialog(self) -> None:
        dialog = ctk.CTkToplevel(self)
        dialog.title("Превращение")
        dialog.geometry("320x120")
        dialog.resizable(False, False)
        dialog.configure(fg_color="#1A1A1A")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        row = ctk.CTkFrame(dialog, fg_color="#1A1A1A")
        row.pack(pady=24)

        choices = [
            ("Ферзь", chess.QUEEN),
            ("Ладья", chess.ROOK),
            ("Слон", chess.BISHOP),
            ("Конь", chess.KNIGHT),
        ]

        def choose(ptype: chess.PieceType) -> None:
            dialog.destroy()
            if self.controller.confirm_promotion(ptype):
                self.board_canvas.redraw()
                self.status_label.configure(text=self._status_text())
                self._refresh_history()
                self._refresh_captured()
                if not self.controller.is_human_turn and not self.controller.is_game_over:
                    self.after(60, self._trigger_bot)
                elif self.controller.is_game_over:
                    self._show_result()

        def on_close() -> None:
            self.controller.cancel_promotion()
            self.board_canvas.redraw()
            dialog.destroy()

        dialog.protocol("WM_DELETE_WINDOW", on_close)

        for label, ptype in choices:
            ctk.CTkButton(
                row,
                text=label,
                width=70,
                height=36,
                fg_color="#3B82F6",
                hover_color="#2563EB",
                command=lambda pt=ptype: choose(pt),
            ).pack(side="left", padx=6)

    def _undo(self) -> None:
        if self.board_canvas._animating:
            return
        # Allow undo even after game over (mate / resign / draw) —
        # user can explore alternative lines.
        # Cancel any in-flight bot calculation / analysis
        self._bot_generation += 1
        self._analysis_generation += 1
        self._bot_thinking = False
        self._analyzing = False
        if self.controller.undo():
            self.board_canvas.redraw()
            self.status_label.configure(text=self._status_text())
            self._refresh_history()
            self._refresh_captured()
            self.progress_label.configure(text="")
            self.analyze_btn.configure(
                state="normal" if self.controller.is_game_over else "disabled",
                text="Разбор",
            )

    def _offer_draw(self) -> None:
        if self._bot_thinking or self.board_canvas._animating:
            return
        if self.controller.is_game_over:
            return
        # Cancel in-flight bot if any
        self._bot_generation += 1
        self._bot_thinking = False
        self.controller.offer_draw()
        self.status_label.configure(text=self._status_text())
        self._show_result()

    def _resign(self) -> None:
        if self._bot_thinking or self.board_canvas._animating:
            return
        if self.controller.is_game_over:
            return
        self._bot_generation += 1
        self._bot_thinking = False
        self.controller.resign()
        self.status_label.configure(text=self._status_text())
        self._show_result()

    def _show_result(self) -> None:
        result = self.controller.result_text()
        self.analyze_btn.configure(state="normal")
        dialog = ctk.CTkToplevel(self)
        dialog.title("Партия окончена")
        dialog.geometry("340x210")
        dialog.resizable(False, False)
        dialog.configure(fg_color="#1A1A1A")
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text=result,
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color="#FFFFFF",
        ).pack(pady=(28, 12))

        ctk.CTkButton(
            dialog,
            text="Разбор партии",
            width=160,
            height=36,
            fg_color="#059669",
            hover_color="#047857",
            command=lambda: (dialog.destroy(), self._start_analysis()),
        ).pack(pady=4)

        ctk.CTkButton(
            dialog,
            text="Новая партия",
            width=160,
            height=36,
            fg_color="#3B82F6",
            command=lambda: (dialog.destroy(), self.on_new_game()),
        ).pack(pady=4)

    # ------------------------------------------------------------------
    # Stage 1 — Analysis
    # ------------------------------------------------------------------
    def _start_analysis(self) -> None:
        if self._analyzing or not self.controller.move_list:
            return
        if self.controller.is_reviewing():
            self.controller.exit_review()
            self.board_canvas.redraw()

        self._analyzing = True
        self._analysis_generation += 1
        gen = self._analysis_generation
        self.analyze_btn.configure(state="disabled", text="…")
        self.progress_label.configure(text="Анализ… 0%")

        from game.analyzer import Analyzer, summary_text

        def worker() -> None:
            def progress(done: int, total: int) -> None:
                if gen != self._analysis_generation:
                    return
                pct = int(100 * done / max(1, total))
                self.after(0, lambda: self.progress_label.configure(
                    text=f"Анализ… {done}/{total} ({pct}%)"
                ))

            try:
                analyzer = Analyzer(
                    self.controller.engine,
                    movetime_ms=500,
                    on_progress=progress,
                )
                reviews = analyzer.analyse_game(
                    self.controller.move_list,
                    self.controller.human_color,
                    sans=self.controller.move_sans,
                )
            except Exception as e:
                self.after(0, lambda: self._on_analysis_error(str(e), gen))
                return

            self.after(0, lambda: self._on_analysis_done(reviews, gen))

        threading.Thread(target=worker, daemon=True).start()

    def _on_analysis_error(self, msg: str, gen: int) -> None:
        if gen != self._analysis_generation:
            return
        self._analyzing = False
        self.analyze_btn.configure(state="normal", text="Разбор")
        self.progress_label.configure(text=f"Ошибка анализа: {msg[:60]}")

    def _on_analysis_done(self, reviews, gen: int) -> None:
        if gen != self._analysis_generation:
            return
        self._analyzing = False
        self.controller.set_analysis(reviews)
        self.analyze_btn.configure(state="normal", text="Разбор")

        from game.analyzer import summary_text
        summary = summary_text(reviews)
        self.progress_label.configure(text=f"Готово · {summary}")
        self._render_analysis_history()
        self.status_label.configure(text=self._status_text())

    def _render_analysis_history(self) -> None:
        """Rebuild history textbox with color tags for human moves."""
        reviews = self.controller.analysis
        if not reviews:
            return

        colors = {
            "blunder": "#EF4444",
            "mistake": "#F97316",
            "inaccuracy": "#EAB308",
            "ok": "#A3A3A3",
        }

        self.history_box.configure(state="normal")
        self.history_box.delete("1.0", "end")

        # Configure tags once
        for name, color in colors.items():
            self.history_box.tag_config(name, foreground=color)
        self.history_box.tag_config("best", foreground="#22D3EE")
        self.history_box.tag_config("num", foreground="#888888")
        self.history_box.tag_config("bot", foreground="#666666")

        for i, r in enumerate(reviews):
            if i % 2 == 0:
                self.history_box.insert("end", f"{i // 2 + 1}. ", "num")
            tag = r.color_tag if r.is_human else "bot"
            start = self.history_box.index("end-1c")
            self.history_box.insert("end", r.san)
            end = self.history_box.index("end-1c")
            self.history_box.tag_add(tag, start, end)
            # Store ply on the tag range for click lookup
            self.history_box.tag_add(f"ply_{r.ply}", start, end)

            if r.is_human and r.best_san and r.classification != "ok":
                self.history_box.insert("end", f"({r.best_san})", "best")

            self.history_box.insert("end", "  ")

        self.history_box.configure(state="disabled")
        self.history_box.see("end")

        # Bind click → enter review for that ply
        self.history_box.bind("<Button-1>", self._on_history_click)

    def _on_history_click(self, event) -> None:
        if not self.controller.analysis:
            return
        index = self.history_box.index(f"@{event.x},{event.y}")
        tags = self.history_box.tag_names(index)
        ply = None
        for t in tags:
            if t.startswith("ply_"):
                try:
                    ply = int(t.split("_", 1)[1])
                except ValueError:
                    pass
                break
        if ply is None:
            return

        if self.controller.enter_review(ply):
            self.board_canvas.redraw()
            r = next((x for x in self.controller.analysis if x.ply == ply), None)
            if r and r.is_human:
                info = f"ход {ply // 2 + 1}{'…' if ply % 2 else '.'} {r.san}"
                if r.classification != "ok":
                    info += f" · {r.classification}"
                    if r.best_san:
                        info += f" → лучше {r.best_san}"
                    if r.loss >= 0.1:
                        info += f" (−{r.loss:.1f})"
                self.status_label.configure(text=info)
            else:
                self.status_label.configure(text=self._status_text())
