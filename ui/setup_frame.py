"""
SetupFrame — start screen: color, orientation, strength (Elo).
"""

from __future__ import annotations

import customtkinter as ctk
import chess
from typing import Callable

from config import ELO_CHOICES


class SetupFrame(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_start: Callable[[chess.Color, bool, int], None],
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self.on_start = on_start

        self.color_var = ctk.StringVar(value="Белыми")
        self.orient_var = ctk.StringVar(value="Я снизу")
        self.elo_var = ctk.StringVar(value="1600")

        self._build()

    def _build(self) -> None:
        self.configure(fg_color="#1A1A1A")

        title = ctk.CTkLabel(
            self,
            text="alexaroffCoachChess",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color="#FFFFFF",
        )
        title.pack(pady=(32, 6))

        subtitle = ctk.CTkLabel(
            self,
            text="Я против бота",
            font=ctk.CTkFont(size=14),
            text_color="#AAAAAA",
        )
        subtitle.pack(pady=(0, 24))

        # Color
        color_frame = ctk.CTkFrame(self, fg_color="#242424", corner_radius=12)
        color_frame.pack(fill="x", padx=40, pady=6)

        ctk.CTkLabel(color_frame, text="Я играю", font=ctk.CTkFont(size=13), text_color="#CCCCCC").pack(
            anchor="w", padx=16, pady=(12, 4)
        )
        ctk.CTkSegmentedButton(
            color_frame,
            values=["Белыми", "Чёрными"],
            variable=self.color_var,
            width=280,
        ).pack(padx=16, pady=(0, 14))

        # Orientation
        orient_frame = ctk.CTkFrame(self, fg_color="#242424", corner_radius=12)
        orient_frame.pack(fill="x", padx=40, pady=6)

        ctk.CTkLabel(orient_frame, text="Ориентация", font=ctk.CTkFont(size=13), text_color="#CCCCCC").pack(
            anchor="w", padx=16, pady=(12, 4)
        )
        ctk.CTkSegmentedButton(
            orient_frame,
            values=["Я снизу", "Я сверху"],
            variable=self.orient_var,
            width=280,
        ).pack(padx=16, pady=(0, 14))

        # Strength (Elo)
        strength_frame = ctk.CTkFrame(self, fg_color="#242424", corner_radius=12)
        strength_frame.pack(fill="x", padx=40, pady=6)

        ctk.CTkLabel(
            strength_frame,
            text="Сила бота (ЭЛО)",
            font=ctk.CTkFont(size=13),
            text_color="#CCCCCC",
        ).pack(anchor="w", padx=16, pady=(12, 4))

        elo_labels = [str(e) for e in ELO_CHOICES]
        self.elo_menu = ctk.CTkOptionMenu(
            strength_frame,
            values=elo_labels,
            variable=self.elo_var,
            width=280,
            fg_color="#3B82F6",
            button_color="#2563EB",
            button_hover_color="#1D4ED8",
        )
        self.elo_menu.pack(padx=16, pady=(0, 6))

        hint = ctk.CTkLabel(
            strength_frame,
            text="400 — новичок   ·   1600 — клуб   ·   2600 — мастер",
            font=ctk.CTkFont(size=11),
            text_color="#777777",
        )
        hint.pack(anchor="w", padx=16, pady=(0, 12))

        # Start button
        start_btn = ctk.CTkButton(
            self,
            text="Начать партию",
            font=ctk.CTkFont(size=16, weight="bold"),
            height=48,
            corner_radius=10,
            fg_color="#3B82F6",
            hover_color="#2563EB",
            command=self._start,
        )
        start_btn.pack(pady=28, padx=40, fill="x")

    def _start(self) -> None:
        color = chess.WHITE if self.color_var.get() == "Белыми" else chess.BLACK
        at_bottom = self.orient_var.get() == "Я снизу"
        elo = int(self.elo_var.get())
        self.on_start(color, at_bottom, elo)
