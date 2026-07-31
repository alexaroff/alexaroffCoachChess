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
APP_VERSION = "0.6.1"
APP_ID = "com.alexaroff.coachchess"

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = BASE_DIR / "templates"

# Stockfish binary. Prefer env var, then common Homebrew locations.
_STOCKFISH_CANDIDATES = [
    os.environ.get("STOCKFISH_PATH"),
    "/opt/homebrew/bin/stockfish",      # Apple Silicon
    "/usr/local/bin/stockfish",         # Intel
    str(BASE_DIR / "bin" / "stockfish"),
]
STOCKFISH_PATH = next((p for p in _STOCKFISH_CANDIDATES if p and Path(p).exists()), "stockfish")

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
ENGINE_THREADS = 1
ENGINE_HASH_MB = 128

# Master: fast but strong
MASTER_MOVETIME_MS = 350
# Master+: deeper search
MASTER_PLUS_MOVETIME_MS = 1200

# ---------------------------------------------------------------------------
# Board
# ---------------------------------------------------------------------------
BOARD_SQUARES = 8
SQUARE_SIZE = 72                   # pixels per square

# ---------------------------------------------------------------------------
# Colors (dark theme + modern board)
# ---------------------------------------------------------------------------
LIGHT_SQUARE = "#E8D5B5"
DARK_SQUARE = "#B58863"
HIGHLIGHT_FROM = "#7B9EFF"
HIGHLIGHT_TO = "#5CDB95"
LAST_MOVE = "#C6A664"
SELECT_COLOR = "#F6F669"
LEGAL_MOVE_DOT = "#4CAF50"
CHECK_COLOR = "#E74C3C"          # king in check

# App background
APP_BG = "#1A1A1A"
FRAME_BG = "#242424"
