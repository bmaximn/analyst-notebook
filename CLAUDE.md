# analyst-notebook — Правила проекту

## Середовище

- Python 3.9.6, PyQt6 6.10.2
- `.venv` у папці проекту
- Запуск: `source .venv/bin/activate && python main.py`
- Весь код в одному файлі `main.py` (~4100+ рядків)

## Читання main.py — ЗАБОРОНЕНО читати весь файл

`main.py` > 4000 рядків. **Ніколи не читати весь файл через Read.**

Замість цього:
1. `grep -n "def ім'я\|class ім'я" main.py` — знайти номер рядка
2. `Read` з `offset` + `limit` — читати тільки потрібну секцію (~50-100 рядків)
3. Для архітектурного аналізу або пошуку по всьому файлу → **Gemini**

## Gemini для аналізу main.py

```bash
cd /Users/maksym.balaban/.claude/plugins/cc-gemini-plugin && \
PATH="/Users/maksym.balaban/.nvm/versions/node/v24.15.0/bin:$PATH" \
node scripts/gemini-bridge.js \
  --max-file-bytes 200000 \
  --files "/Users/maksym.balaban/Documents/ІБМ/analyst-notebook/main.py" \
  -- "питання або задача"
```

**ВАЖЛИВО:** `main.py` = 170 KB. Завжди додавай `--max-file-bytes 200000` інакше файл буде обрізаний до 32KB.

## Активне ТЗ

`TZ_i2_Research_v2.0.md` — єдине актуальне ТЗ. Всі попередні (`v1.md`, `Gap_Analysis`) — застарілі.

## Ключова архітектура

- `Node`, `Link` — моделі даних (рядки ~100-250)
- `NodeItem`, `LinkItem`, `GroupItem` — QGraphicsObject (рядки ~400-1000)
- `DiagramCanvas` — QGraphicsView (рядки ~1009-1815)
- `save_to_json` / `load_from_json` — (рядки ~1815-1934)
- `MainWindow` — головне вікно (рядки ~2200+)
- `LinkDialog` — діалог редагування зв'язку (~2507-2637)
- `_on_link_creation_requested` — обробник створення зв'язку (~3762)

## JSON Schema

`SCHEMA_VERSION` — зараз 1, після реалізації ТЗ v2.0 стане 2.
