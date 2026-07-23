# alexaroffCoachChess

Десктоп-приложение для macOS: шахматный тренер и авто-игрок поверх любой шахматной доски на экране.

## Цель

1. Пользователь указывает область шахматной доски на экране.
2. Приложение автоматически определяет ориентацию доски (белые или чёрные снизу).
3. Режимы:
   - **Coach** — показывает лучший ход. Человек ходит сам.
   - **Auto** — программа играет самостоятельно (клики).
4. Целевая сила ≈ 3000 Elo (Stockfish, 1 поток, низкая нагрузка).

Приоритетная платформа: **macOS**.

## Архитектура

```
alexaroffCoachChess/
├── main.py              # GUI + lifecycle
├── config.py            # константы
├── tools.py             # screen / mouse / region
├── board_detector.py    # ориентация + FEN (templates)
├── engine_manager.py    # Stockfish
├── coach.py             # режимы + память ходов
├── advisor.py           # стратегические советы
├── templates/           # шаблоны фигур (Duolingo)
├── requirements.txt
└── README.md
```

## Требования

- macOS (Apple Silicon / Intel)
- Python 3.10+
- Stockfish: `brew install stockfish`
- Разрешения: **Screen Recording** + **Accessibility**

## Установка (Mac)

```bash
git clone https://github.com/alexaroff/alexaroffCoachChess.git
cd alexaroffCoachChess
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
brew install stockfish   # если ещё нет
```

Путь к Stockfish (если не находится автоматически):

```bash
export STOCKFISH_PATH=/opt/homebrew/bin/stockfish
```

## Запуск

```bash
source .venv/bin/activate
python main.py
```

При первом запуске macOS попросит разрешения Screen Recording и Accessibility — нужно выдать.

## Статус

**Stage 2+ / 0.3.0** — распознавание + память + advisor.

- Выбор области + ориентация
- Template matching (шаблоны из Duolingo)
- Форсирование стартовой позиции (100% на 1-м ходу)
- Память предыдущей позиции + фильтр легальных ходов
- `advisor.py` — короткие стратегические советы по фазам
- В GUI: FEN, уверенность, совет тренера

**Важно:** папка `templates/` должна лежать рядом с кодом (14 png). Без неё работает fallback-эвристика.

Следующее: Stage 3 (overlay со стрелкой).

## Roadmap

- ~~Stage 1: region + orientation~~
- ~~Stage 2: FEN + templates + memory + advisor~~
- Stage 3: Coach mode (overlay стрелки)
- Stage 4: Auto mode (клики)
- Stage 5: стабилизация, hotkeys, .app
