"""
alexaroffCoachChess — main entry point + GUI.

Stage 1: region selection + orientation detection.
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
        self.geometry("420x380")
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

        # Orientation (Stage 1)
        orient_frm = ttk.LabelFrame(frm, text="Ориентация", padding=8)
        orient_frm.pack(fill=tk.X, **pad)

        self.orient_var = tk.StringVar(value="—")
        ttk.Label(orient_frm, textvariable=self.orient_var).pack(side=tk.LEFT)
        ttk.Button(orient_frm, text="Переопределить", command=self._redetect_orientation).pack(side=tk.RIGHT)

        # Mode
        mode_frm = ttk.LabelFrame(frm, text="Режим", padding=8)
        mode_frm.pack(fill=tk.X, **pad)

        self.mode_var = tk.StringVar(value=MODE_COACH)
        ttk.Radiobutton(mode_frm, text="Coach (только подсказки)", variable=self.mode_var, value=MODE_COACH).pack(anchor=tk.W)
        ttk.Radiobutton(mode_frm, text="Auto (играет сама)", variable=self.mode_var, value=MODE_AUTO).pack(anchor=tk.W)

        # Controls
        ctrl_frm = ttk.Frame(frm)
        ctrl_frm.pack(fill=tk.X, pady=12)

        self.start_btn = ttk.Button(ctrl_frm, text="Старт", command=self._start)
        self.start_btn.pack(side=tk.LEFT, padx=4)
        self.stop_btn = ttk.Button(ctrl_frm, text="Стоп", command=self._stop, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=4)

        # Status
        self.status_var = tk.StringVar(value="Готов. Выберите область доски.")
        ttk.Label(frm, textvariable=self.status_var, foreground="#333").pack(anchor=tk.W, pady=(8, 0))

        # Footer
        ttk.Label(
            frm,
            text="Stage 1 — region selection + orientation detection",
            font=("Helvetica", 9),
            foreground="#999",
        ).pack(side=tk.BOTTOM, anchor=tk.W)

    def _select_region(self) -> None:
        """Interactive region selection + immediate orientation detection."""
        self.status_var.set("Выделите доску… (Esc — отмена)")
        self.update_idletasks()

        region = select_region_interactive()
        if region is None:
            self.status_var.set("Выбор области отменён")
            return

        self.detector.set_region(region)
        self.region_var.set(f"{region.width}×{region.height} @ ({region.left},{region.top})")

        # Immediately detect orientation
        try:
            orientation = self.detector.detect_orientation()
            self._update_orientation_label(orientation)
            self.status_var.set(f"Область задана · ориентация: {orientation}")
        except Exception as e:
            self.orient_var.set("ошибка")
            self.status_var.set(f"Область задана, но ориентация не определилась: {e}")
            log.exception("Orientation detection failed")

    def _redetect_orientation(self) -> None:
        if self.detector.region is None:
            messagebox.showinfo("Нет области", "Сначала выберите область доски.")
            return
        try:
            orientation = self.detector.detect_orientation()
            self._update_orientation_label(orientation)
            self.status_var.set(f"Ориентация переопределена: {orientation}")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def _update_orientation_label(self, orientation: str) -> None:
        if orientation == "white":
            self.orient_var.set("белые снизу")
        else:
            self.orient_var.set("чёрные снизу")

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
        # TODO Stage 2+: start periodic tick (after() or thread)

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
