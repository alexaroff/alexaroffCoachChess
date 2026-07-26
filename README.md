# alexaroffCoachChess

Десктоп-приложение для macOS: шахматный **тренер** (Coach) поверх доски на экране.
Основной фокус — Duolingo Chess.

## Цель

Давать точные стрелки-подсказки в реальной партии:
- ты всегда сидишь снизу;
- можешь играть и белыми, и чёрными;
- система понимает, чей сейчас ход, и предлагает ход только за ту сторону, которой ходить;
- Stockfish ~3000 Elo используется как источник силы хода.

## Текущий статус (26 июля 2026)

**Прототип на template matching исчерпал себя.**

Мы реализовали и отладили:
- выбор области доски (two-click);
- фиксацию ориентации;
- hybrid reconcile по цвету/занятости + защиту turn;
- overlay со стрелками;
- интеграцию Stockfish;
- множество исправлений геометрии, прозрачности и сбросов позиции.

Однако template matching на стилизованной доске Duolingo **не держит позицию** после нескольких ходов.  
Это фундаментальное ограничение подхода, а не набор мелких багов.

### Принятое решение

Переходим на **Вариант A**:

> Лёгкая нейросеть (fine-tune MobileNet / EfficientNet / аналог),  
> специально обученная под фигуры и клетки Duolingo.

Вариант B (готовые YOLO chess-vision пайплайны) оставляем как запасной.

## Архитектура (на момент перехода)

```
alexaroffCoachChess/
├── main.py              # GUI (tkinter)
├── config.py
├── tools.py             # screen capture + two-click region selection
├── board_detector.py    # текущий (слабый) template-matching детектор
├── engine_manager.py    # Stockfish + auto-restart
├── coach.py             # Coach-режим + reconcile + overlay
├── overlay.py           # стрелка поверх доски
├── advisor.py
├── templates/           # старые png-шаблоны (больше не развиваем)
├── requirements.txt
└── README.md
```

## Требования

- macOS (Apple Silicon предпочтительно)
- Python 3.12 (рекомендуется)
- Stockfish (`brew install stockfish`)
- Разрешения: Screen Recording + Accessibility

## Запуск текущего прототипа

```bash
git clone https://github.com/alexaroff/alexaroffCoachChess.git
cd alexaroffCoachChess
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
brew install python-tk@3.12   # если нужно
brew install stockfish
python main.py
```

## Roadmap

- [x] Stage 1: region + orientation
- [x] Stage 2–3: prototype (templates + reconcile + overlay + Stockfish)
- [x] Решение: отказ от дальнейшего развития template matching
- [ ] **Stage NN-1**: сбор датасета клеток Duolingo (размеченные фигуры + пустые)
- [ ] **Stage NN-2**: fine-tune лёгкой модели под 13 классов (6 белых + 6 чёрных + empty)
- [ ] **Stage NN-3**: замена `board_detector.py` на нейросетевой инференс
- [ ] Stage 4: стабильный Coach (белые и чёрные, правильный turn)
- [ ] Stage 5: Auto mode (опционально)
- [ ] Stage 6: упаковка в .app

## Следующий конкретный шаг

Сбор датасета:
- скриншоты реальных партий Duolingo в разных состояниях;
- нарезка клеток 64×64 (или 96×96);
- разметка: `wP, wN, wB, wR, wQ, wK, bP, bN, bB, bR, bQ, bK, empty`.

---

**Дата решения:** 26 июля 2026  
**Направление:** Вариант A — собственная лёгкая нейросеть под Duolingo.
