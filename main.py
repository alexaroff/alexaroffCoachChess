"""
alexaroffCoachChess — main entry point + GUI.

Stage 2: region + orientation + position recognition (FEN).
Uses only stdlib tkinter. No legacy Nautilus / Krevetka code.
"""

from __future__ import annotations

import logging
import sys
import tkinter as tk
from tkinter import ttk, messagebox
from typing import Optional

from config import APP_NAME, APP_VERSION, MODE_COACH, MODE_AUTO, POLL_INTERVAL_MS
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
        self.geometry("460x460")
        self.resizable(False, False)

        # Core objects
        self.detector = BoardDetector()
        self.engine = EngineManager()
        self.coach = Coach(self.detector, self.engine)

        self._tick_job: Optional[str] = None

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _build_ui(self) -> None:
        pad = {"padx": 12, "pady": 5}

        frm = ttk.Frame(self, padding=12)
        frm.pack(fill=tk.BOTH, expand=True)

        # Header
        ttk.Label(frm, text=APP_NAME, font=("Helvetica", 16, "bold")).pack(anchor=tk.W)
        ttk.Label(frm, text="macOS Chess Coach / Auto-player", foreground="#666").pack(
            anchor=tk.W, pady=(0, 10)
        )

        # Region
        region_frm = ttk.LabelFrame(frm, text="Доска", padding=8)
        region_frm.pack(fill=tk.X, **pad)

        self.region_var = tk.StringVar(value="не выбрана")
        ttk.Label(region_frm, textvariable=self.region_var).pack(side=tk.LEFT)
        ttk.Button(region_frm, text="Выбрать область…", command=self._select_region).pack(
            side=tk.RIGHT
        )

        # Orientation
        orient_frm = ttk.LabelFrame(frm, text="Ориентация", padding=8)
        orient_frm.pack(fill=tk.X, **pad)

        self.orient_var = tk.StringVar(value="—")
        ttk.Label(orient_frm, textvariable=self.orient_var).pack(side=tk.LEFT)
        ttk.Button(orient_frm, text="Переопределить", command=self._redetect_orientation).pack(
            side=tk.RIGHT
        )

        # Position (Stage 2)
        pos_frm = ttk.LabelFrame(frm, text="Позиция (FEN)", padding=8)
        pos_frm.pack(fill=tk.X, **pad)

        self.fen_var = tk.StringVar(value="—")
        fen_label = ttk.Label(pos_frm, textvariable=self.fen_var, wraplength=400)
        fen_label.pack(anchor=tk.W)

        self.pos_info_var = tk.StringVar(value="")
        ttk.Label(pos_frm, textvariable=self.pos_info_var, foreground="#666").pack(
            anchor=tk.W, pady=(4, 0)
        )

        # Mode
        mode_frm = ttk.LabelFrame(frm, text="Режим", padding=8)
        mode_frm.pack(fill=tk.X, **pad)

        self.mode_var = tk.StringVar(value=MODE_COACH)
        ttk.Radiobutton(
            mode_frm, text="Coach (только подсказки)", variable=self.mode_var, value=MODE_COACH
        ).pack(anchor=tk.W)
        ttk.Radiobutton(
            mode_frm, text="Auto (играет сама)", variable=self.mode_var, value=MODE_AUTO
        ).pack(anchor=tk.W)

        # Controls
        ctrl_frm = ttk.Frame(frm)
        ctrl_frm.pack(fill=tk.X, pady=10)

        self.start_btn = ttk.Button(ctrl_frm, text="Старт", command=self._start)
        self.start_btn.pack(side=tk.LEFT, padx=4)
        self.stop_btn = ttk.Button(ctrl_frm, text="Стоп", command=self._stop, state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT, padx=4)
        ttk.Button(ctrl_frm, text="Сканировать сейчас", command=self._scan_once).pack(
            side=tk.RIGHT, padx=4
        )

        # Status
        self.status_var = tk.StringVar(value="Готов. Выберите область доски.")
        ttk.Label(frm, textvariable=self.status_var, foreground="#333").pack(
            anchor=tk.W, pady=(6, 0)
        )

        # Footer
        ttk.Label(
            frm,
            text="Stage 2 — position recognition (FEN). Templates later for better piece types.",
            font=("Helvetica", 9),
            foreground="#999",
        ).pack(side=tk.BOTTOM, anchor=tk.W)

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _select_region(self) -> None:
        self.status_var.set("Выделите доску… (Esc — отмена)")
        self.update_idletasks()

        region = select_region_interactive()
        if region is None:
            self.status_var.set("Выбор области отменён")
            return

        self.detector.set_region(region)
        self.region_var.set(f"{region.width}×{region.height} @ ({region.left},{region.top})")

        # Immediate orientation + first scan
        try:
            orientation = self.detector.detect_orientation()
            self._update_orientation_label(orientation)
            self._scan_once()
            self.status_var.set(f"Область задана · ориентация: {orientation}")
        except Exception as e:
            self.orient_var.set("ошибка")
            self.status_var.set(f"Ошибка: {e}")
            log.exception("After region select")

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
        self.orient_var.set("белые снизу" if orientation == "white" else "чёрные снизу")

    def _scan_once(self) -> None:
        """One-shot board scan (useful for testing Stage 2)."""
        if self.detector.region is None:
            messagebox.showinfo("Нет области", "Сначала выберите область доски.")
            return
        try:
            snapshot = self.detector.get_snapshot()
            if snapshot.fen:
                # Show short FEN (just the placement part)
                placement = snapshot.fen.split(" ")[0]
                self.fen_var.set(placement)
                self.pos_info_var.set(
                    f"фигур: {snapshot.occupied_count}  ·  уверенность: {snapshot.confidence:.0%}"
                )
                log.info("Detected FEN: %s (occupied=%d, conf=%.2f)",
                         snapshot.fen, snapshot.occupied_count, snapshot.confidence)
            else:
                self.fen_var.set("не удалось распознать")
                self.pos_info_var.set("")
        except Exception as e:
            self.fen_var.set("ошибка")
            self.pos_info_var.set(str(e))
            log.exception("Scan failed")

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

        # Start periodic tick
        self._schedule_tick()

    def _stop(self) -> None:
        self.coach.stop()
        self.engine.stop()
        if self._tick_job is not None:
            self.after_cancel(self._tick_job)
            self._tick_job = None
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_var.set("Остановлено")

    def _schedule_tick(self) -> None:
        if not self.coach.is_running:
            return
        try:
            move = self.coach.tick()
            if move is not None:
                self.status_var.set(f"Лучший ход: {move.uci()}")
                # Also refresh the FEN display
                self._scan_once()
        except Exception as e:
            log.exception("Tick error")
            self.status_var.set(f"Ошибка tick: {e}")

        self._tick_job = self.after(POLL_INTERVAL_MS, self._schedule_tick)

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
