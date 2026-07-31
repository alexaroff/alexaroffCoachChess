# alexaroffCoachChess

Настольные шахматы — **ты против бота**.  
CustomTkinter + python-chess + Stockfish.

**Версия:** 0.10.0 · **Обновлено:** 31 июля 2026

---

## Возможности (сейчас)

| Область | Что есть |
|---------|----------|
| **Режимы** | **Игра** / **Тренировка**. Режим хранится в партии и виден в статусе |
| **Подсказки** | В Тренировке — кнопка «Подсказка»: лучший ход (фиолетовая подсветка, 2 уровня) |
| **Разбор** | После партии — классификация, цвета в истории, клик → сыгранный vs лучший |
| **Игра** | Ходы клик-клик, легальные ходы, отмена (в т.ч. после мата), сдача, ничья |
| **Доска** | Координаты, ориентация, выбор цвета |
| **Визуал** | Тёмная тема, подсветка последнего хода, шах, анимация хода бота |
| **Превращение** | Диалог: ферзь / ладья / слон / конь |
| **История** | SAN + цветные метки после разбора |
| **Взятия** | Съеденные фигуры в верхней панели |
| **Сила бота** | 8 уровней ЭЛО: 400 · 600 · 800 · 1200 · 1600 · 2000 · 2400 · 2600 |
| **Движок** | Stockfish в отдельном потоке, диалог если бинарник не найден |

---

## Куда идём

1. ~~Режимы~~ ✅ · ~~Разбор~~ ✅ · ~~Подсказки (Stage 4 v1)~~ ✅  
2. **EngineService (очередь)** ← сейчас  
3. **Eval-бар**  
4. Адаптивная сила, дебютная книга, тексты/материалы  

Приоритет: безопасный движок → мгновенная обратная связь → адаптив и контент.  
Подробности — в **[ROADMAP.md](./ROADMAP.md)**.

---

## Требования

- Python 3.10+ (**на macOS — 3.12 из Homebrew**, системный 3.9 даёт пустое окно)
- [Stockfish](https://stockfishchess.org/)
- Пакеты из `requirements.txt`

```
python-chess>=1.10
customtkinter>=5.2
Pillow>=10.0
```

---

## Установка и запуск

### macOS с нуля (рекомендуется)

Один блок в Terminal. Каждый этап проверяется: ошибка → стоп, успех → дальше.  
Ставит Homebrew (если нет), Python **3.12**, Stockfish, клонирует репо, venv, зависимости и запускает игру.

```bash
bash << 'EOF'
set -euo pipefail

ok()   { echo "  OK: $1"; }
fail() { echo "  FAIL: $1"; exit 1; }
step() { echo; echo "=== $1 ==="; }

# --- 1. Homebrew ---
step "1/6 Homebrew"
if ! command -v brew >/dev/null 2>&1; then
  echo "Ставлю Homebrew (может запросить пароль)..."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || fail "установка Homebrew"
fi

if [ -x /opt/homebrew/bin/brew ]; then
  eval "$(/opt/homebrew/bin/brew shellenv)"
  grep -qs 'homebrew/bin/brew shellenv' ~/.zprofile 2>/dev/null || echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
elif [ -x /usr/local/bin/brew ]; then
  eval "$(/usr/local/bin/brew shellenv)"
  grep -qs 'usr/local/bin/brew shellenv' ~/.zprofile 2>/dev/null || echo 'eval "$(/usr/local/bin/brew shellenv)"' >> ~/.zprofile
else
  fail "brew не найден после установки"
fi
brew --version >/dev/null || fail "brew не работает"
ok "brew $(brew --version | head -1)"

# --- 2. Python 3.12 + Stockfish ---
step "2/6 Python 3.12 + Stockfish"
brew list python@3.12 >/dev/null 2>&1 || brew install python@3.12 || fail "python@3.12"
brew list stockfish   >/dev/null 2>&1 || brew install stockfish   || fail "stockfish"

if [ -x /opt/homebrew/bin/python3.12 ]; then
  PYTHON=/opt/homebrew/bin/python3.12
elif [ -x /usr/local/bin/python3.12 ]; then
  PYTHON=/usr/local/bin/python3.12
else
  PYTHON="$(command -v python3.12 || true)"
fi
[ -n "${PYTHON}" ] && [ -x "$PYTHON" ] || fail "python3.12 не найден"
"$PYTHON" --version | grep -q '3\.12' || fail "нужен Python 3.12, сейчас: $($PYTHON --version)"
command -v stockfish >/dev/null || fail "stockfish не в PATH"
ok "$($PYTHON --version)"
ok "stockfish → $(command -v stockfish)"

# --- 3. Клон ---
step "3/6 Клон репозитория"
PROJECT="$HOME/alexaroffCoachChess"
rm -rf "$PROJECT"
git clone https://github.com/alexaroff/alexaroffCoachChess.git "$PROJECT" || fail "git clone"
[ -f "$PROJECT/requirements.txt" ] || fail "нет requirements.txt"
[ -f "$PROJECT/main.py" ] || fail "нет main.py"
ok "клон в $PROJECT"

# --- 4. venv ---
step "4/6 Виртуальное окружение"
cd "$PROJECT"
rm -rf venv
"$PYTHON" -m venv venv || fail "создание venv"
# shellcheck disable=SC1091
source "$PROJECT/venv/bin/activate"
ok "venv активирован ($(python --version))"

# --- 5. Зависимости ---
step "5/6 pip install"
python -m pip install --upgrade pip || fail "upgrade pip"
pip install -r "$PROJECT/requirements.txt" || fail "pip install -r requirements.txt"
python -c "import chess, customtkinter, PIL" || fail "импорт chess/customtkinter/PIL"
ok "зависимости установлены"

# --- 6. Запуск ---
step "6/6 Запуск"
export TK_SILENCE_DEPRECATION=1
echo "Запускаю main.py — должно открыться окно настройки партии."
python "$PROJECT/main.py" || fail "запуск main.py"

echo
echo "=============================================="
echo "  Готово"
echo "=============================================="
echo "Папка:  $PROJECT"
echo "Снова:  cd ~/alexaroffCoachChess && source venv/bin/activate && python main.py"
echo
EOF
```

**Важно:** на macOS нужен **Python 3.12 из Homebrew**, не системный 3.9 — иначе CustomTkinter часто открывает пустое серое окно.

### Повторный запуск (уже установлено)

```bash
cd ~/alexaroffCoachChess
source venv/bin/activate
export TK_SILENCE_DEPRECATION=1
python main.py
```

Или:

```bash
cd ~/alexaroffCoachChess
./run.sh
```

### Linux (кратко)

```bash
sudo apt install stockfish python3-venv python3-tk   # или аналог
git clone https://github.com/alexaroff/alexaroffCoachChess.git
cd alexaroffCoachChess
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python main.py
```

Если Stockfish не найден — приложение покажет диалог с инструкцией, без traceback.

---

## Структура проекта

```
alexaroffCoachChess/
├── main.py                 # Точка входа, окно приложения
├── run.sh                  # Запуск с рабочего стола / терминала
├── config.py               # Цвета, таблица ЭЛО, пути, версия
├── engine_manager.py       # Обёртка над Stockfish (сила по ЭЛО)
├── ROADMAP.md              # План развития по этапам (читать перед новой сессией)
├── requirements.txt
├── game/
│   ├── player.py           # HumanPlayer / BotPlayer
│   ├── game_controller.py  # Состояние партии, ходы, undo, ничья, взятия, review
│   └── analyzer.py         # Разбор партии (Stockfish + классификация)
├── ui/
│   ├── setup_frame.py      # Цвет, ориентация, выбор ЭЛО
│   ├── game_frame.py       # Статус, история, кнопки, диалог promotion
│   └── board_canvas.py     # Отрисовка доски, координаты, подсветка, анимация
└── templates/              # Картинки фигур (wP.png … bK.png)
```

---

## Уровни силы бота (примерно)

| ЭЛО  | Уровень       | Skill Level | Время на ход |
|------|---------------|-------------|--------------|
| 400  | Новичок       | 0           | 50 мс        |
| 600  |               | 1           | 80 мс        |
| 800  |               | 3           | 120 мс       |
| 1200 | Клубный−      | 6           | 200 мс       |
| 1600 | Клубный       | 10          | 350 мс       |
| 2000 | Сильный       | 14          | 500 мс       |
| 2400 | Очень сильный | 17          | 800 мс       |
| 2600 | Мастер        | 20 (полный) | 1200 мс      |

Используются опции Stockfish `Skill Level` и `UCI_LimitStrength` / `UCI_Elo`.

---

## История изменений

**v0.10.0** — 31 июля 2026  
- Stage 4 v1: кнопка «Подсказка» в режиме Тренировка (лучший ход, 2 уровня подсветки)  
- Приоритет roadmap: подсказки → eval-бар → адаптив  

**v0.9.0** — 31 июля 2026  
- Stage 0: режимы Игра / Тренировка  
- Stage 1: разбор партии (классификация, цвета, клик → сравнение)  

**v0.7.1** — 31 июля 2026  
- Предложение ничьей (бот всегда принимает)  
- Более яркая подсветка последнего хода (янтарь + рамка)  
- Улучшенный диалог, если Stockfish не найден  
- Зафиксирован ROADMAP.md  

**v0.7.0**  
- Координаты на доске, съеденные фигуры, 8 уровней ЭЛО  

**v0.6.x**  
- Диалог превращения, подсветка шаха, история ходов, исправленный undo  

**v0.5.x**  
- Неблокирующий бот, анимация фигур, отмена хода  

---

## Заметки

- Ориентацию доски можно выбрать только до старта партии.  
- «Отменить ход» откатывает твой ход + ответ бота (или только твой, если бот ещё не ответил).  
- Ничья всегда принимается ботом.  
- «Подсказка» только в режиме Тренировка и только на твоём ходу.

---

**Репозиторий:** https://github.com/alexaroff/alexaroffCoachChess  
**План работ:** [ROADMAP.md](./ROADMAP.md)
