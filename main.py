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
        self.geometry("640x780")
        self.minsize(600, 720)
        self.configure(fg_color="#1A1A1A")

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.engine = EngineManager()
        self.controller: GameController | None = None
        self.current_frame = None

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        try:
            self.engine.start()
        except Exception as e:
            log.error("Failed to start Stockfish: %s", e)
            self.after(200, lambda: self._show_engine_error(str(e)))

        self._show_setup()

    def _show_engine_error(self, msg: str) -> None:
        dialog = ctk.CTkToplevel(self)
        dialog.title("Stockfish не найден")
        dialog.geometry("460x260")
        dialog.resizable(False, False)
        dialog.configure(fg_color="#1A1A1A")
        dialog.transient(self)
        dialog.grab_set()

        ctk.CTkLabel(
            dialog,
            text="Stockfish не найден",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#FF6B6B",
        ).pack(pady=(20, 8))

        ctk.CTkLabel(
            dialog,
            text=(
                "Без Stockfish играть нельзя.\n\n"
                "macOS:   brew install stockfish\n"
                "Linux:   sudo apt install stockfish\n\n"
                "Или задай путь: export STOCKFISH_PATH=/path/to/stockfish"
            ),
            font=ctk.CTkFont(size=13),
            text_color="#CCCCCC",
            justify="left",
        ).pack(pady=4, padx=24)

        ctk.CTkButton(
            dialog,
            text="Понятно",
            width=120,
            command=dialog.destroy,
        ).pack(pady=16)

    def _clear(self) -> None:
        if self.current_frame is not None:
            self.current_frame.destroy()
            self.current_frame = None

    def _show_setup(self) -> None:
        self._clear()
        self.current_frame = SetupFrame(self, on_start=self._start_game)
        self.current_frame.pack(fill="both", expand=True)

    def _start_game(self, human_color: chess.Color, human_at_bottom: bool, elo: int) -> None:
        if not self.engine.is_running:
            self._show_engine_error("Движок не запущен. Установи Stockfish и перезапусти приложение.")
            return

        self._clear()

        self.controller = GameController(
            human_color=human_color,
            human_at_bottom=human_at_bottom,
            elo=elo,
            engine=self.engine,
            on_game_over=lambda text: None,
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
