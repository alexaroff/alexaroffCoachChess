# alexaroffCoachChess

Standalone desktop chess application (CustomTkinter).

**Концепция**

Игра «Я против бота» с собственной доской.

- Выбор цвета (белые / чёрные)
- Выбор ориентации (я снизу / я сверху) — только до начала партии
- 8 уровней силы бота (400–2600 ЭЛО)
- Тёмная тема, клик-клик, плавная анимация хода бота
- Координаты, история, съеденные фигуры, undo, promotion, ничья

---

## Статус

**31 июля 2026** — v0.7.1  
- Ничья по соглашению (бот всегда принимает)  
- Яркая подсветка последнего хода  
- Координаты, съеденные, ЭЛО 400–2600, promotion, undo

---

## Запуск

```bash
cd ~/alexaroffCoachChess
git pull origin main
source venv/bin/activate          # обязательно
pip install -r requirements.txt
# Stockfish: brew install stockfish   (или apt install stockfish)
python main.py
# если python не находится — используй python3 main.py
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

**Последнее обновление:** 31 июля 2026 (v0.7.1)
