# alexaroffCoachChess

Десктоп-приложение для macOS: шахматный тренер и авто-игрок поверх любой шахматной доски на экране.

## Цель

1. Пользователь указывает область шахматной доски на экране.
2. Приложение автоматически определяет ориентацию доски (белые или чёрные снизу) независимо от цвета, которым играет пользователь.
3. Режимы:
   - **Coach** — показывает лучший ход (стрелка + подсветка). Человек ходит сам.
   - **Auto** — программа играет полностью самостоятельно (клики по доске).
4. Целевая сила ≈ 3000 Elo (Stockfish, 1 поток, низкая нагрузка на CPU).

Приоритетная платформа: **macOS**. Windows — позже.

## Архитектура (чистая, Stage 0)

```
alexaroffCoachChess/
├── main.py              # GUI + управление режимами + lifecycle
├── config.py            # константы, пути, настройки
├── tools.py             # screen capture, mouse, region selection (низкий уровень)
├── board_detector.py    # распознавание позиции + авто-ориентация
├── engine_manager.py    # Stockfish wrapper (python-chess)
├── coach.py             # логика Coach / Auto + визуализация ходов
├── requirements.txt
└── README.md
```

### Ответственность модулей

| Модуль              | Ответственность |
|---------------------|-----------------|
| `config.py`         | Все константы, пути к Stockfish, параметры движка, цвета overlay |
| `tools.py`          | Захват экрана (mss), клики (pyautogui/pynput), интерактивный выбор региона |
| `board_detector.py` | Из региона → FEN / chess.Board + определение, кто снизу |
| `engine_manager.py` | Запуск/остановка Stockfish, get_best_move с ограничением по времени/глубине |
| `coach.py`          | Связка detector + engine + визуализация стрелки / авто-клики |
| `main.py`           | Tkinter GUI, выбор режима, start/stop, overlay window |

Никакого наследия NautilusChess / Krevetka / aquatic-тематики.

## Требования

- macOS (протестировано на Apple Silicon / Intel)
- Python 3.10+
- Stockfish binary (рекомендуется 16+): `brew install stockfish`
- Разрешения: **Screen Recording** + **Accessibility** (для захвата экрана и кликов)

## Установка

```bash
cd alexaroffCoachChess
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Указать путь к Stockfish через переменную окружения или в `config.py`:

```bash
export STOCKFISH_PATH=/opt/homebrew/bin/stockfish
```

## Запуск

```bash
python main.py
```

## Статус

**Stage 0** — чистый каркас + ребрендинг.  
Готово к **Stage 1**: выбор области доски + авто-определение ориентации.

## Roadmap (кратко)

- Stage 1: region selection + orientation detection
- Stage 2: надёжное распознавание позиции (FEN)
- Stage 3: Coach mode (overlay стрелки)
- Stage 4: Auto mode (клики)
- Stage 5: стабилизация, hotkeys, настройки силы, упаковка в .app
