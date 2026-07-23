"""
alexaroffCoachChess — main entry point + GUI.

Stage 0: clean skeleton.
Uses only stdlib tkinter. No legacy Nautilus / Krevetka code.
"""

from __future__ import annotations

import logging
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from config import APP_NAME, APP_VERSION, MODE_COACH, MODE_AUTO
from tools import Region, select_region_interactive
from board_detector import BoardDetector
from engine_manager import EngineManager
from coach import Coach

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("main")


class App(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title(f"{APP_NAME}  v{APP_VERSION}")
        self.geometry("420x320")
        self.resizable(False, False)

        # Core objects
        self.detector = BoardDetector()
        self.engine = EngineManager()
        self.coach = Coach(self.detector, self.engine)

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        pad = {"padx": 12, "pady": 6}

        frm = ttk.Frame(self, padding=12)
        frm.pack(fill=tk.BOTH, expand=True)

        # Header
        ttk.Label(frm, text=APP_NAME, font=("Helvetica", 16, "bold")).pack(anchor=tk.W)
        ttk.Label(frm, text="macOS Chess Coach / Auto-player", foreground="#666").pack(anchor=tk.W, pady=(0, 12))

        # Region
        region_frm = ttk.LabelFrame(frm, text="Доска", padding=8)
        region_frm.pack(fill=tk.X, **pad)

        self.region_var = tk.StringVar(value="не выбрана")
        ttk.Label(region_frm, textvariable=self.region_var).pack(side=tk.LEFT)
        ttk.Button(region_frm, text="Выбрать область…", command=self._select_region).pack(side=tk.RIGHT)

        # Mode
        mode_frm = ttk.LabelFrame(frm, text="Режим", padding=8)
        mode_frm.pack(fill=tk.X, **pad)

        self.mode_var = tk.StringVar(value=MODE_COACH)
        ttk.Radiobutton(mode_frm, text="Coach (только подсказки)", variable=self.mode_var, value=MODE_COACH).pack(anchor=tk.W)
        ttk.Radiobutton(mode_frm, text="Auto (играет сама)", variable=self.mode_var, value=MODE_AUTO).pack(anchor=tk.W)

        # Controls
        ctrl_frm = ttk.Frame(frm)
        ctrl_frm.pack(fill=tk.X, pady=16)

        self.start_btn = ttk.Button(ctrl_frm, text="Старт", command=self._start)
        self.start_btn.pack(side=tk.LEFT, padx=4)
        self.stop_btn = ttk.Button(ctrl_frm, text="Стоп", command=self._stop, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=4)

        # Status
        self.status_var = tk.StringVar(value="Готов. Выберите область доски.")
        ttk.Label(frm, textvariable=self.status_var, foreground="#333").pack(anchor=tk.W, pady=(8, 0))

        # Footer
        ttk.Label(frm, text="Stage 0 — чистый каркас. Stage 1: region + orientation", font=("Helvetica", 9), foreground="#999").pack(side=tk.BOTTOM, anchor=tk.W)

    def _select_region(self) -> None:
        """Placeholder for Stage 1 interactive selection."""
        region = select_region_interactive()
        if region is None:
            # Temporary: allow manual hardcode for testing later
            messagebox.showinfo(
                "Stage 1",
                "Интерактивный выбор области будет реализован в Stage 1.\n"
                "Пока регион не выбран — дальше двигаться нельзя.",
            )
            return

        self.detector.set_region(region)
        self.region_var.set(str(region))
        self.status_var.set(f"Область задана: {region}")

    def _start(self) -> None:
        if self.detector.region is None:
            messagebox.showwarning("Нет области", "Сначала выберите область доски.")
            return

        mode = self.mode_var.get()
        self.coach.set_mode(mode)

        try:
            self.engine.start()
            self.coach.start()
        except Exception as e:
            messagebox.showerror("Ошибка движка", str(e))
            return

        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL)
        self.status_var.set(f"Работает · режим {mode}")
        # TODO Stage 1+: start periodic tick (after() or thread)

    def _stop(self) -> None:
        self.coach.stop()
        self.engine.stop()
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_var.set("Остановлено")

    def _on_close(self) -> None:
        self._stop()
        self.destroy()


def main() -> int:
    log.info("Starting %s v%s", APP_NAME, APP_VERSION)
    app = App()
    app.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
