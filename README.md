# alexaroffCoachChess

Standalone desktop chess application (CustomTkinter).

**Концепция**

Игра «Я против бота» с собственной доской.

- Выбор цвета (белые / чёрные)
- Выбор ориентации (я снизу / я сверху) — только до начала партии
- Бот на полной силе Stockfish (Master / Master+)
- Тёмная тема, клик-клик, анимация хода бота
- Современные классические 2D-фигуры (Staunton-стиль)

---

## Статус

**30 июля 2026** — MVP работает. Фигуры обновлены. Старая концепция (оверлей поверх Duolingo) полностью заброшена.

---

## Запуск

```bash
cd ~/alexaroffCoachChess
git pull origin main
source venv/bin/activate
pip install -r requirements.txt
# Stockfish: brew install stockfish   (или apt/yum)
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
templates/          # современные фигуры
```

---

**Последнее обновление:** 30 июля 2026
