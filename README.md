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

**31 июля 2026** — v0.6.0  
- Диалог превращения пешки (ферзь/ладья/слон/конь)  
- Подсветка короля при шахе  
- Последний ход в статусе (SAN)  
- Отмена последнего хода, неблокирующий бот, анимация

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

**Последнее обновление:** 31 июля 2026
