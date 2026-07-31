# alexaroffCoachChess

Standalone desktop chess — **You vs Bot**.  
CustomTkinter + python-chess + Stockfish.

**Version:** 0.7.1 · **Updated:** 31 July 2026

---

## Features

| Area | What |
|------|------|
| **Game** | Click-click moves, legal move hints, undo (full turn), resign, draw offer |
| **Board** | Coordinates a–h / 1–8, orientation (you bottom/top), color choice |
| **Visual** | Dark theme, last-move amber highlight + border, check highlight, piece animation |
| **Promotion** | Dialog: Queen / Rook / Bishop / Knight |
| **History** | Move list (SAN) under the board |
| **Captures** | Captured pieces shown in the top bar |
| **Bot strength** | 8 Elo levels: 400 · 600 · 800 · 1200 · 1600 · 2000 · 2400 · 2600 |
| **Engine** | Non-blocking Stockfish (background thread), graceful error if missing |

---

## Requirements

- Python 3.10+
- [Stockfish](https://stockfishchess.org/) binary
- Packages from `requirements.txt`

```
python-chess>=1.10
customtkinter>=5.2
Pillow>=10.0
```

---

## Install & Run

```bash
cd ~/alexaroffCoachChess
git pull origin main

python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Stockfish
#   macOS:  brew install stockfish
#   Linux:  sudo apt install stockfish
#   or:     export STOCKFISH_PATH=/path/to/stockfish

python main.py
# if needed: python3 main.py
```

If Stockfish is missing, the app shows a clear dialog (no traceback).

---

## Project layout

```
alexaroffCoachChess/
├── main.py                 # Entry point, App window
├── config.py               # Colors, Elo table, paths, version
├── engine_manager.py       # Stockfish wrapper (strength by Elo)
├── requirements.txt
├── game/
│   ├── player.py           # HumanPlayer / BotPlayer
│   └── game_controller.py  # Board state, moves, undo, draw, captures
├── ui/
│   ├── setup_frame.py      # Color, orientation, Elo selector
│   ├── game_frame.py       # Status, history, buttons, promotion dialog
│   └── board_canvas.py     # Board draw, coords, highlights, animation
└── templates/              # Piece images (wP.png … bK.png)
```

---

## Elo mapping (approx.)

| Elo  | Feel        | Skill Level | Movetime |
|------|-------------|-------------|----------|
| 400  | Beginner    | 0           | 50 ms    |
| 600  |             | 1           | 80 ms    |
| 800  |             | 3           | 120 ms   |
| 1200 | Club-ish    | 6           | 200 ms   |
| 1600 | Club        | 10          | 350 ms   |
| 2000 | Strong      | 14          | 500 ms   |
| 2400 | Very strong | 17          | 800 ms   |
| 2600 | Master      | 20 (full)   | 1200 ms  |

Uses Stockfish `Skill Level` + `UCI_LimitStrength` / `UCI_Elo` where supported.

---

## Changelog (recent)

**v0.7.1** — 31 Jul 2026  
- Draw offer (bot always accepts)  
- Brighter last-move highlight (amber + border)  
- Clearer Stockfish-missing dialog  

**v0.7.0**  
- Board coordinates, captured pieces, 8 Elo levels  

**v0.6.x**  
- Promotion dialog, check highlight, move history, fixed undo  

**v0.5.x**  
- Non-blocking bot, piece animation, takeback  

---

## Notes

- Orientation is locked at game start (by design).  
- Undo takes back your last move + bot’s reply (or only yours if bot hasn’t moved yet).  
- Draw is always accepted by the bot (simple training mode).  

---

**Repo:** https://github.com/alexaroff/alexaroffCoachChess
