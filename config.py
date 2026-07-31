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
APP_VERSION = "0.10.0"
APP_ID = "com.alexaroff.coachchess"

# Game modes (Stage 0)
MODE_PLAY = "play"
MODE_TRAIN = "train"
MODE_LABELS = {
    MODE_PLAY: "Игра",
    MODE_TRAIN: "Тренировка",
}

# Live coach (Stage 4) — short analysis for hints / future eval bar
LIVE_ANALYSIS_MOVETIME_MS = 200
HINT_COLOR = "#A78BFA"  # violet — distinct from review cyan and last-move amber

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

# Elo → Stockfish settings
# skill: 0–20, movetime_ms: thinking time
# limit_strength + elo used when supported (Stockfish 11+)
ELO_LEVELS: dict[int, dict] = {
    400:  {"skill": 0,  "movetime_ms": 50,   "limit_strength": True,  "elo": 800},
    600:  {"skill": 1,  "movetime_ms": 80,   "limit_strength": True,  "elo": 1000},
    800:  {"skill": 3,  "movetime_ms": 120,  "limit_strength": True,  "elo": 1200},
    1200: {"skill": 6,  "movetime_ms": 200,  "limit_strength": True,  "elo": 1400},
    1600: {"skill": 10, "movetime_ms": 350,  "limit_strength": True,  "elo": 1600},
    2000: {"skill": 14, "movetime_ms": 500,  "limit_strength": True,  "elo": 2000},
    2400: {"skill": 17, "movetime_ms": 800,  "limit_strength": True,  "elo": 2400},
    2600: {"skill": 20, "movetime_ms": 1200, "limit_strength": False, "elo": 2800},
}

ELO_CHOICES = list(ELO_LEVELS.keys())  # [400, 600, ...]

# ---------------------------------------------------------------------------
# Board
# ---------------------------------------------------------------------------
BOARD_SQUARES = 8
SQUARE_SIZE = 72
COORD_MARGIN = 20          # space for a–h / 1–8 labels

# ---------------------------------------------------------------------------
# Colors (dark theme + modern board)
# ---------------------------------------------------------------------------
LIGHT_SQUARE = "#E8D5B5"
DARK_SQUARE = "#B58863"
HIGHLIGHT_FROM = "#7B9EFF"
HIGHLIGHT_TO = "#5CDB95"
LAST_MOVE = "#FFD54F"          # bright amber — last move
SELECT_COLOR = "#F6F669"
LEGAL_MOVE_DOT = "#4CAF50"
CHECK_COLOR = "#E74C3C"
COORD_COLOR = "#888888"

# App background
APP_BG = "#1A1A1A"
FRAME_BG = "#242424"
