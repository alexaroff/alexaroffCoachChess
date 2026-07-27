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
APP_VERSION = "0.4.0-dev"
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
# Engine (full strength by default)
# ---------------------------------------------------------------------------
ENGINE_THREADS = 1
ENGINE_HASH_MB = 128
DEFAULT_MOVETIME_MS = 300          # responsive but strong
MAX_MOVETIME_MS = 2000
ENGINE_SKILL_LEVEL = None          # None = full strength (~3000+)

# ---------------------------------------------------------------------------
# Board
# ---------------------------------------------------------------------------
BOARD_SQUARES = 8
SQUARE_SIZE = 80                   # pixels per square in UI

# ---------------------------------------------------------------------------
# Colors (CustomTkinter / Canvas)
# ---------------------------------------------------------------------------
LIGHT_SQUARE = "#F0D9B5"
DARK_SQUARE = "#B58863"
HIGHLIGHT_COLOR = "#AAD4FF"
LAST_MOVE_COLOR = "#C6A664"
