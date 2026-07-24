# alexaroffCoachChess

Десктоп-приложение для macOS: шахматный тренер / авто-игрок поверх доски на экране (в первую очередь Duolingo).

## Статус проекта (заморожен 24 июля 2026, 23:54)

**Это прототип.**

Текущая реализация (template matching + hybrid temporal reconcile + простой overlay со стрелками) **не обеспечивает стабильного распознавания** после нескольких ходов на стилизованной доске Duolingo.

### Что работает
- Выбор области доски (two-click метод)
- Надёжное определение стартовой позиции + форсирование классического FEN
- Базовый захват экрана и работа со Stockfish
- Простой overlay со стрелками (появляется, но после 2–4 ходов начинает ошибаться)
- Hybrid reconcile по цвету/занятости

### Что не работает стабильно
- Точное определение типа фигур после первого хода
- Долговременное удержание правильной позиции
- Стрелки после нескольких ходов начинают указывать не туда / не той стороне

### Принятое решение

Дальнейшая работа над стрелками **приостановлена** до выбора более сильного vision-подхода.

Будем изучать два направления:

**Вариант A** — лёгкая нейросеть (fine-tune MobileNet / EfficientNet / аналогичной модели специально под фигуры Duolingo).  
Нужен датасет из размеченных клеток.

**Вариант B** — адаптация готовых open-source chess-vision пайплайнов (YOLO-based board/piece detectors и подобные решения).

Перед продолжением разработки будет выбран лучший из этих двух вариантов.

---

## Архитектура (текущая)

```
alexaroffCoachChess/
├── main.py              # GUI
├── config.py
├── tools.py             # screen capture + two-click region selection
├── board_detector.py    # orientation + FEN (template matching, слабый)
├── engine_manager.py    # Stockfish + auto-restart
├── coach.py             # режимы + hybrid reconcile + вызов overlay
├── overlay.py           # простой transparent arrow overlay
├── advisor.py
├── templates/           # 12 png
├── requirements.txt
└── README.md
```

## Требования

- macOS (Apple Silicon предпочтительно)
- Python 3.11+
- Stockfish (`brew install stockfish`)
- Разрешения: Screen Recording + Accessibility

## Запуск

```bash
git clone https://github.com/alexaroff/alexaroffCoachChess.git
cd alexaroffCoachChess
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
brew install stockfish
python main.py
```

## Roadmap

- [x] Stage 1: region + orientation
- [~] Stage 2: FEN + templates + memory (только старт работает надёжно)
- [~] Stage 3: overlay со стрелками (прототип есть, стабильности нет)
- [ ] **Research**: выбрать между Вариантом A (лёгкая нейросеть) и Вариантом B (готовый chess-vision пайплайн)
- [ ] Stage 2.5 / 3.5: стабильное vision + надёжные стрелки
- [ ] Stage 4: Auto mode
- [ ] Stage 5: .app / полировка

---

**Дата фиксации:** 24 июля 2026  
**Следующий шаг:** исследование и сравнение Варианта A и Варианта B перед продолжением разработки.
