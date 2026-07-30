# alexaroffCoachChess

Standalone desktop chess application (CustomTkinter).

**Концепция**

Игра «Я против бота» с собственной доской.

- Выбор цвета (белые / чёрные)
- Выбор ориентации (я снизу / я сверху) — только до начала партии
- Бот на полной силе Stockfish (Master / Master+)
- Тёмная тема, клик-клик, плавная анимация хода бота
- Современные классические 2D-фигуры (Staunton-стиль)
- Неблокирующий UI (ход бота в отдельном потоке)

---

## Статус

**30 июля 2026** — v0.5.1  
- Неблокирующий расчёт хода бота  
- Реальная анимация перемещения фигуры  
- Отмена последнего хода (takeback)  
- Graceful обработка отсутствия Stockfish  
- Старая концепция (оверлей Duolingo) полностью заброшена

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

**Последнее обновление:** 30 июля 2026
