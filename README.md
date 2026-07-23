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

## Архитектура

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
| `tools.py`          | Захват экрана (mss), клики (pyautogui), интерактивный выбор региона |
| `board_detector.py` | Из региона → ориентация + FEN / chess.Board |
| `engine_manager.py` | Запуск/остановка Stockfish, get_best_move с ограничением по времени |
| `coach.py`          | Связка detector + engine + визуализация стрелки / авто-клики |
| `main.py`           | Tkinter GUI, выбор режима, start/stop |

Никакого наследия NautilusChess / Krevetka / aquatic-тематики.

## Требования

- macOS (Apple Silicon / Intel)
- Python 3.10+
- Stockfish binary (рекомендуется 16+): `brew install stockfish`
- Разрешения: **Screen Recording** + **Accessibility**

## Установка

```bash
cd alexaroffCoachChess
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Указать путь к Stockfish:

```bash
export STOCKFISH_PATH=/opt/homebrew/bin/stockfish
```

## Запуск

```bash
python main.py
```

## Статус

**Stage 2** — распознавание позиции (FEN).

- Выбор области + ориентация (Stage 1)
- Деление доски на 64 клетки
- Определение пусто / занято (по variance яркости)
- Определение цвета фигуры (белая / чёрная)
- Базовая оценка типа фигуры (без шаблонов — точность средняя)
- В GUI показывается текущий FEN + количество фигур + уверенность
- Кнопка «Сканировать сейчас» для ручной проверки

**Важно:** тип фигуры пока определяется эвристикой.  
Для высокой точности позже добавим шаблоны (template matching).

Готово к тестированию. После тестов → улучшение точности + Stage 3 (стрелки).

## Roadmap

- ~~Stage 1: region selection + orientation detection~~
- ~~Stage 2: position recognition (FEN)~~
- Stage 3: Coach mode (overlay стрелки)
- Stage 4: Auto mode (клики)
- Stage 5: стабилизация, hotkeys, настройки силы, упаковка в .app
