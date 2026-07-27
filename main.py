"""
alexaroffCoachChess — entry point.
Standalone chess app: You vs Bot.
"""

from __future__ import annotations

import logging
import sys
import customtkinter as ctk
import chess

from config import APP_NAME, APP_VERSION
from engine_manager import EngineManager
from game.game_controller import GameController
from ui.setup_frame import SetupFrame
from ui.game_frame import GameFrame

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("main")


class App(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()

        self.title(f"{APP_NAME}  v{APP_VERSION}")
        self.geometry("620x720")
        self.minsize(580, 680)
        self.configure(fg_color="#1A1A1A")

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.engine = EngineManager()
        self.engine.start()

        self.controller: GameController | None = None
        self.current_frame = None

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._show_setup()

    def _clear(self) -> None:
        if self.current_frame is not None:
            self.current_frame.destroy()
            self.current_frame = None

    def _show_setup(self) -> None:
        self._clear()
        self.current_frame = SetupFrame(self, on_start=self._start_game)
        self.current_frame.pack(fill="both", expand=True)

    def _start_game(self, human_color: chess.Color, human_at_bottom: bool, strength: str) -> None:
        self._clear()

        self.controller = GameController(
            human_color=human_color,
            human_at_bottom=human_at_bottom,
            strength=strength,
            engine=self.engine,
            on_game_over=lambda text: None,  # handled inside GameFrame
        )

        self.current_frame = GameFrame(
            self,
            controller=self.controller,
            on_new_game=self._show_setup,
        )
        self.current_frame.pack(fill="both", expand=True)

    def _on_close(self) -> None:
        try:
            self.engine.stop()
        except Exception:
            pass
        self.destroy()


def main() -> None:
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
