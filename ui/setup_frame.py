"""
SetupFrame — start screen: color, orientation, strength.
"""

from __future__ import annotations

import customtkinter as ctk
import chess
from typing import Callable


class SetupFrame(ctk.CTkFrame):
    def __init__(
        self,
        master,
        on_start: Callable[[chess.Color, bool, str], None],
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self.on_start = on_start

        self.color_var = ctk.StringVar(value="Белыми")
        self.orient_var = ctk.StringVar(value="Я снизу")
        self.strength_var = ctk.StringVar(value="Master")

        self._build()

    def _build(self) -> None:
        self.configure(fg_color="#1A1A1A")

        title = ctk.CTkLabel(
            self,
            text="alexaroffCoachChess",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color="#FFFFFF",
        )
        title.pack(pady=(40, 8))

        subtitle = ctk.CTkLabel(
            self,
            text="Я против бота",
            font=ctk.CTkFont(size=14),
            text_color="#AAAAAA",
        )
        subtitle.pack(pady=(0, 30))

        # Color
        color_frame = ctk.CTkFrame(self, fg_color="#242424", corner_radius=12)
        color_frame.pack(fill="x", padx=40, pady=8)

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
        orient_frame.pack(fill="x", padx=40, pady=8)

        ctk.CTkLabel(orient_frame, text="Ориентация", font=ctk.CTkFont(size=13), text_color="#CCCCCC").pack(
            anchor="w", padx=16, pady=(12, 4)
        )
        ctk.CTkSegmentedButton(
            orient_frame,
            values=["Я снизу", "Я сверху"],
            variable=self.orient_var,
            width=280,
        ).pack(padx=16, pady=(0, 14))

        # Strength
        strength_frame = ctk.CTkFrame(self, fg_color="#242424", corner_radius=12)
        strength_frame.pack(fill="x", padx=40, pady=8)

        ctk.CTkLabel(strength_frame, text="Сила бота", font=ctk.CTkFont(size=13), text_color="#CCCCCC").pack(
            anchor="w", padx=16, pady=(12, 4)
        )
        ctk.CTkSegmentedButton(
            strength_frame,
            values=["Master", "Master+"],
            variable=self.strength_var,
            width=280,
        ).pack(padx=16, pady=(0, 14))

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
        start_btn.pack(pady=36, padx=40, fill="x")

    def _start(self) -> None:
        color = chess.WHITE if self.color_var.get() == "Белыми" else chess.BLACK
        at_bottom = self.orient_var.get() == "Я снизу"
        strength = "master_plus" if self.strength_var.get() == "Master+" else "master"
        self.on_start(color, at_bottom, strength)
