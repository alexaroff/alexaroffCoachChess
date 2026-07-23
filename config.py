"""
alexaroffCoachChess — configuration.

All constants and tunable parameters live here.
No business logic.
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Identity
# ---------------------------------------------------------------------------
APP_NAME = "alexaroffCoachChess"
APP_VERSION = "0.1.0-stage0"
APP_ID = "com.alexaroff.coachchess"

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent

# Stockfish binary. Prefer env var, then common Homebrew locations.
_STOCKFISH_CANDIDATES = [
    os.environ.get("STOCKFISH_PATH"),
    "/opt/homebrew/bin/stockfish",      # Apple Silicon
    "/usr/local/bin/stockfish",         # Intel
    str(BASE_DIR / "bin" / "stockfish"),
]
STOCKFISH_PATH = next((p for p in _STOCKFISH_CANDIDATES if p and Path(p).exists()), "stockfish")

# ---------------------------------------------------------------------------
# Engine (target ~3000 Elo, 1 thread, low CPU)
# ---------------------------------------------------------------------------
ENGINE_THREADS = 1
ENGINE_HASH_MB = 64
# Prefer time limit over skill level for consistent strength under low load.
DEFAULT_MOVETIME_MS = 150          # ~150–300 ms → strong but responsive
MAX_MOVETIME_MS = 800
ENGINE_SKILL_LEVEL = None          # None = full strength; 0–20 if want weaker

# ---------------------------------------------------------------------------
# Board / Vision (Stage 1+)
# ---------------------------------------------------------------------------
BOARD_SQUARES = 8
# Minimal expected square size in pixels (used as hint for auto-detect)
MIN_SQUARE_PX = 30
MAX_SQUARE_PX = 200

# ---------------------------------------------------------------------------
# Overlay / Visualization (Stage 3)
# ---------------------------------------------------------------------------
ARROW_COLOR = (0, 180, 255)        # RGB
ARROW_ALPHA = 0.75
HIGHLIGHT_FROM_COLOR = (255, 200, 0)
HIGHLIGHT_TO_COLOR = (0, 220, 120)
OVERLAY_LINE_WIDTH = 4

# ---------------------------------------------------------------------------
# Modes
# ---------------------------------------------------------------------------
MODE_COACH = "coach"
MODE_AUTO = "auto"

# ---------------------------------------------------------------------------
# Runtime
# ---------------------------------------------------------------------------
POLL_INTERVAL_MS = 400             # how often we re-scan the board in Coach mode
AUTO_CLICK_DELAY_MS = 250          # delay before clicking in Auto mode
