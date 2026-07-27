# alexaroffCoachChess

Standalone desktop chess application (CustomTkinter).

**Новая концепция (с 27 июля 2026)**

Игра «Я против бота» с собственной доской.

- Выбор цвета (белые / чёрные)
- Выбор ориентации (я снизу / я сверху) — только до начала партии
- Бот на полной силе Stockfish (Master / Master+)
- Тёмная тема, клик-клик, анимация хода бота

---

## Статус

**27 июля 2026** — MVP-структура и базовый код готовы.

Старая концепция (оверлей поверх Duolingo) заархивирована в:
`archive/duolingo-overlay-2026-07`

---

## Запуск

```bash
cd ~/alexaroffCoachChess
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
# Stockfish: brew install stockfish
python main.py
```

---

## Структура

```
main.py
config.py
engine_manager.py
game/
  player.py
  game_controller.py
ui/
  setup_frame.py
  game_frame.py
  board_canvas.py
templates/
```

---

**Последнее обновление:** 27 июля 2026
