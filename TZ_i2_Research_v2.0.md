# ТЗ v2.0 — PyQt6 link-analysis app на основі IBM i2 Analyst's Notebook

**Версія:** v2.0  
**Дата:** 2026-05-19  
**Мова документа:** українська  
**Ціль:** довести поточний PyQt6-редактор зв'язкових схем до практичної моделі link-analysis app, схожої на IBM i2 Analyst's Notebook, без копіювання закритих IBM-ресурсів.

**Джерела для цього TZ:**

- `/tmp/i2_codex_research.txt` — витяг із дослідження IBM i2 Analyst's Notebook 9.4 docs.
- `/Users/a0000/Documents/Project/IBM/main.py` — поточна реалізація застосунку.
- `/Users/a0000/Documents/Project/IBM/TZ_i2_Research_v2.0.md` — попередній draft, який цим документом перезаписано.

---

## Ключові терміни IBM i2, які використовуємо правильно

| Неправильно / ризиковано | Правильно для TZ |
|---|---|
| `Style Cards` | Такого терміна в i2 docs немає. Використовувати: **Edit Item Properties > Style** з вкладками `Type`, `Display`, `Font`, `Frame`, `Connection`. |
| Групування = рамка | У i2 це різні речі: **Group** — група елементів, **Icon Frame** — рамка навколо іконки, **Box/Circle** — репрезентації, що можуть візуально обводити інші items. |
| `grid/radial` як назви i2 layout | Це наші MVP-алгоритми. Реальні назви i2 association layouts: **Peacock**, **Compact Peacock**, **Grouped**, **Hierarchy**, **Minimize Crossed Links**, **Organization**, **Packed**, **Circular**. |
| `line_type` як просто стиль | В i2 важлива семантика **Link Strength**: `Confirmed`, `Unconfirmed`, `Tentative`; уже з неї випливає стиль лінії. |
| Простий пошук = весь пошук i2 | В i2 окремо існують **Find Text**, **Visual Search**, **Find Path**, **Find Linked**, **Find Connecting Network**, **Find Clusters**, **SNA**. |

---

## Що вже є в поточному застосунку

Підтверджено за `main.py`:

✅ PyQt6 застосунок на `QMainWindow`, `QGraphicsView`, `QGraphicsScene`.  
✅ Модель `Node`: `uuid`, `type`, `title`, `note`, `date`, `x`, `y`, `color`, `photo_base64`, `created_at`, `updated_at`.  
✅ Модель `Link`: `uuid`, `source_uuid`, `target_uuid`, `label`, `line_type`, `direction`, `note`, `color`, `width`, `created_at`, `updated_at`.  
✅ `NodeItem`: картка вузла, фото або емодзі-іконка, кольорова рамка типу, виділення.  
✅ `LinkItem`: малювання лінії, колір/товщина, dashed/double styles, підпис на фоні, базові стрілки за `direction`.  
✅ `NodeDialog`: тип, назва, примітка, дата, колір, фото.  
✅ `LinkDialog`: підпис, тип лінії, напрямок, колір лінії, товщина, примітка.  
✅ `PropertiesPanel`: inline-редагування назви/примітки вузла, inline-редагування підпису зв'язку.  
✅ Кнопка кольору вузла в `PropertiesPanel`.  
✅ Link color/width: поля є в моделі, діалозі, серіалізації та рендері.  
✅ Link label improvements: 9pt, білий фон, відступ 4px, центр лінії.  
✅ Snap-to-grid: `toggle_snap_to_grid()`, прив'язка до сітки 30px.  
✅ Grouping: `GroupItem`, `group_selected()`, `ungroup_selected()`.  
✅ Auto-layout MVP: `auto_layout_grid()` і `auto_layout_radial()`.  
✅ Show-connected filter: контекстне меню вузла `Показати тільки пов'язані` / `Показати всі`.  
✅ Простий `SearchPanel` за вузлами.  
✅ `FilterPanel` за типом вузла.  
✅ Shape Tool: лінія, коло, прямокутник, текст.  
✅ JSON save/load, CSV import, PNG export, PDF export, print preview.  
✅ Undo/Redo через `QUndoStack` і команди `AddNodeCommand`, `EditNodeCommand`, `AddLinkCommand`, `EditLinkCommand` тощо.  
✅ Мінімапа, zoom, autosave.

Важливі технічні уточнення:

- У `LinkDialog.get_link_data()` повертаються `color` і `width`, але при створенні нового зв'язку `_on_link_creation_requested()` зараз не передає їх у `Link(...)`. Це треба виправити, щоб UI реально застосовував вибраний колір/товщину одразу.
- При редагуванні зв'язку `old_data` не містить `color` і `width`, тому undo для цих полів неповний.
- Стрілки за `direction` уже малюються, але лінія йде від центру вузла до центру вузла, тому наконечник може ховатися під карткою вузла. Для i2-подібної поведінки лінію треба обрізати до межі вузла.
- `line_type` зараз змішує семантику, напрямок і стиль: `solid_arrow`, `dashed`, `double`, `bidirectional`. Це треба розділити на `strength`, `direction`, `line_style`, `multiplicity`.

---

## Реальна модель даних i2

В i2 вузол — це не просто "кружечок на сцені". Реальна модель ближча до:

```text
Entity =
  representation      # Icon | Theme line | Event frame | Circle | Box | Text block | OLE object
  entity_type_id      # Person, Organization, Phone, Motor Vehicle...
  semantic_type_id    # родина/семантика для пошуку, layout, import matching
  label
  description
  date_time / start_date_time / end_date_time
  attributes[]
  cards[]
  database_identities[]
  style
  hidden / selected / selection_set
```

Для нашого PyQt6-клона треба зробити сумісну модель, а не копіювати закриті IBM bitmap-іконки чи повний стандартний template. Публічні docs підтверджують семантичні сімейства, але не дають повну 1:1 таблицю всіх стандартних типів та іконок.

### Базові semantic families для v2.x

| Semantic family | Реальні/дочірні типи з i2 docs | Семантика для нашого застосунку | Що є зараз | Що додати |
|---|---|---|---|---|
| `Person` | `Law Enforcement Officer`, `Offender`, `Person Alias` | Людина, роль, псевдонім, підозрюваний/посадовець | `Person` | `semantic_family='Person'`, aliases, рольові підтипи |
| `Organization` | `Company`, `Bank`, `Court`, `Criminal Organization`, `Government Agency`, `Law Enforcement Agency`, `Organization Name Alias` | Організація, установа, компанія, держорган, група | `Organization` | підтипи організацій, alias-type |
| `Phone` | `Cell Phone`, `Fax Machine`, `Pager` | Засіб зв'язку або телефонний ідентифікатор | `Phone` | `Cell Phone`, `Fax Machine`, `Pager` |
| `Motor Vehicle` | `Bus`, `Car`, `Police Car`, `Motorcycle`, `Truck` | Транспортний засіб | `Vehicle` | перейменувати/мігрувати до `Motor Vehicle`, додати підтипи |
| `Location` | `ATM`, `Mailing Address` | Місце, адреса, географічна точка, ATM | `Location` | `ATM`, `Mailing Address`, координати |
| `Event` | `Meeting`, `Crime` | Подія в часі, інцидент, зустріч | `Event` | `event_datetime`, `Event frame` representation |
| `Bank Account` | base type | Банківський рахунок як окремий розслідувальний об'єкт | немає | додати тип, іконку, атрибути account/IBAN/bank |

### Повна модель Link за IBM docs

Поточний `Link` треба розширити до моделі нижче. Частину полів можна додати як optional, але структура має бути стабільною вже у JSON schema v2.

```text
Link =
  id / uuid
  source_entity_id
  target_entity_id
  type_id
  semantic_type_id
  label
  description
  direction: none | source_to_target | target_to_source | bidirectional
  color
  width / line_width
  strength: Confirmed | Unconfirmed | Tentative | custom
  line_style: solid | dashed | dotted | custom
  multiplicity: Single | Directed | Multiple
  date_time
  start_date_time
  end_date_time
  time_zone
  grades / reliability / source_type / source_reference
  attributes[]
  cards[]
  database_identities[]
  weighting_value
  corners / bend_points
  hidden
  selected
  selection_set
  created_at
  updated_at
```

Мінімальна сумісна інтерпретація для v2.x:

- `strength=Confirmed` -> solid line.
- `strength=Unconfirmed` -> dashed line.
- `strength=Tentative` -> dotted line.
- `direction` керує стрілками, а не назвою line type.
- `multiplicity` керує тим, як показувати кілька зв'язків між одними вузлами: `Single`, `Directed`, `Multiple`.
- `weighting_value` потрібен для майбутньої SNA-аналітики.
- `cards[]`, `grades`, `source_reference` потрібні для provenance: звідки взято факт.

---

## ПРІОРИТЕТ 1 — Critical

### P1.1 ✅ Link color/width як частина `Edit Item Properties > Style`

**Що це в i2:** у **Edit Item Properties > Style** для link можна керувати кольором, товщиною лінії та іншими style-параметрами. Це не аналітична семантика, а візуальне оформлення.

**Що маємо зараз:** `Link.color`, `Link.width`, `LinkDialog` з кнопкою кольору і `QSpinBox`, `LinkItem.paint()` використовує ці поля, JSON їх зберігає.

**Що реалізувати:** закрити інтеграційні пропуски: передавати `color` і `width` при створенні нового `Link`; додати `color` і `width` у `old_data` для `EditLinkCommand`; оновити CSV import/export mapping.

**Технічний підхід у PyQt6:** у `MainWindow._on_link_creation_requested()` передати `color=data['color']`, `width=data['width']`; у `_on_edit_link()` збирати `old_data` з `['label', 'line_type', 'direction', 'note', 'color', 'width']`; у `import_from_csv()` приймати необов'язкові `color`, `width`.

**Критерій приймання:** користувач створює зв'язок червоного кольору товщиною 5px, одразу бачить його на схемі, зберігає JSON, відкриває файл знову і отримує той самий стиль; undo повертає попередні `color/width`.

### P1.2 ✅ Direction visual: стрілки напрямку зв'язку

**Що це в i2:** `direction` у Link описує напрямок відношення: `none`, `source_to_target`, `target_to_source`, `bidirectional`. Це окрема властивість link, а не стиль лінії.

**Що маємо зараз:** `Link.direction` є в моделі; `DIRECTION_LABELS` є; `LinkDialog` має combo "Напрямок"; `LinkItem.paint()` малює стрілки для `source_to_target`, `target_to_source`, `bidirectional`.

**Що реалізувати:** довести візуал до i2-подібної поведінки: обрізати лінію до межі `NodeItem`, щоб стрілка не ховалася під карткою; зробити однакову геометрію для solid/dashed/dotted/double; додати smoke-тест на всі 4 напрямки.

**Технічний підхід у PyQt6:** у `LinkItem.update_position()` обчислювати лінію між прямокутниками `NodeItem.boundingRect()` у scene coordinates; винести helper `_intersect_node_rect(center_a, center_b, rect)`; стрілки малювати на кінцевих точках обрізаної лінії; `shape()` залишити широким для зручного кліку.

**Критерій приймання:** для двох вузлів видно 4 різні стани: без стрілки, A->B, B->A, A<->B; наконечник стрілки не перекривається вузлом і не зникає при zoom.

### P1.3 Link Strength як семантика: `Confirmed / Unconfirmed / Tentative`

**Що це в i2:** Link Strength означає надійність/статус факту: `Confirmed` — підтверджено, `Unconfirmed` — не підтверджено, `Tentative` — попередньо/ймовірно. Візуально це зазвичай solid/dashed/dotted, але головне — семантика.

**Що маємо зараз:** є `line_type`, де змішані `solid_arrow`, `dashed`, `double`, `bidirectional`. Частково воно виглядає як strength, але назви й модель не відповідають i2.

**Що реалізувати:** додати окреме поле `strength`; зробити міграцію старого `line_type`; в UI показувати "Підтверджений / Непідтверджений / Попередній"; залишити `line_style` окремо для чисто декоративних стилів.

**Технічний підхід у PyQt6:** додати константи `LINK_STRENGTH_LABELS`; у `Link.__init__`, `to_dict()`, `from_dict()` додати `strength`; у `LinkItem.paint()` мапити `strength` на `Qt.PenStyle.SolidLine`, `DashLine`, `DotLine`; `line_type` тимчасово підтримати для backward compatibility; підняти `SCHEMA_VERSION` до 2.

**Критерій приймання:** у діалозі зв'язку користувач вибирає `Confirmed`, `Unconfirmed`, `Tentative`; JSON містить `strength`; пошук/фільтр можуть знайти всі `Unconfirmed`; старі JSON-файли відкриваються без втрати ліній.

### P1.4 Повна Link-модель і JSON schema v2

**Що це в i2:** link має не тільки source/target/label, а також semantic type, direction, strength, multiplicity, date/time, provenance, attributes, cards, weighting та стан видимості.

**Що маємо зараз:** мінімальна модель `Link` з `uuid`, `source_uuid`, `target_uuid`, `label`, `line_type`, `direction`, `note`, `color`, `width`, timestamps.

**Що реалізувати:** додати поля з блоку "Повна модель Link"; частину з них можна залишити optional/empty, але вони мають серіалізуватися, щоб не ламати майбутній імпорт і аналіз.

**Технічний підхід у PyQt6:** не обов'язково одразу робити `dataclass`, але бажано винести модель у `models.py` після стабілізації; у v2 спершу розширити `Link.__init__`, `to_dict()`, `from_dict()`; додати helper `Link.from_legacy_dict()`; у `save_to_json()` писати `schema_version=2`; у `load_from_json()` мігрувати v1.

**Критерій приймання:** новий JSON містить усі ключі Link-моделі; старий JSON v1 відкривається; відсутні optional-поля мають безпечні defaults; жоден існуючий link не втрачає `label`, `direction`, `color`, `width`.

### P1.5 Find Path: BFS між двома вузлами

**Що це в i2:** **Find Path** знаходить шлях між двома вибраними items, зазвичай найкоротший; може враховувати напрямок link, hidden items, date/time constraints, атрибути та інші умови.

**Що маємо зараз:** є ручне виділення, простий text search і фільтр за типами. Алгоритму пошуку шляху немає.

**Що реалізувати:** MVP Find Path: рівно 2 вибрані вузли -> BFS -> виділити вузли й links на найкоротшому шляху; опція "враховувати напрямок" у діалозі/панелі.

**Технічний підхід у PyQt6:** додати `DiagramCanvas.find_path_between(source_uuid, target_uuid, respect_direction=False) -> list[str]`; будувати adjacency зі `self.links`; BFS через `collections.deque`; повертати ordered nodes + links; у `MainWindow` додати action `Інструменти > Find Path`; результат виділяти через `setSelected(True)` і центрувати `fit_to_screen()` або `centerOn()`.

**Критерій приймання:** якщо вибрано 2 вузли, команда `Find Path` виділяє найкоротший шлях; якщо шляху немає, показує зрозуміле повідомлення; якщо вибрано не 2 вузли, просить вибрати рівно два.

---

## ПРІОРИТЕТ 2 — Important

### P2.1 ✅ Node color button як швидкий доступ до Style

**Що це в i2:** колір/заливка вузла належать до стилю item через **Edit Item Properties > Style**, а не до аналітичного типу як такого.

**Що маємо зараз:** `PropertiesPanel` має кнопку кольору вузла; зміна проходить через `ColorNodeCommand` і підтримує undo.

**Що реалізувати:** перейменувати UI-підпис на точніше "Колір вузла/заливки"; після додавання `Icon Frame` чітко відрізняти `node.color` від `frame_color`; синхронізувати цей контроль з майбутнім Style panel.

**Технічний підхід у PyQt6:** залишити `QColorDialog`; додати tooltip; у `PropertiesPanel.show_node()` показувати окремо `Колір вузла` і `Icon Frame`; при майбутньому refactor винести стиль у `NodeStyle`.

**Критерій приймання:** користувач змінює колір вузла з правої панелі в 1-2 кліки; undo/redo працює; рамка Icon Frame не змінюється випадково.

### P2.2 Icon Frame

**Що це в i2:** **Icon Frame** — кольорова рамка/обідок навколо іконки або theme-line icon. Це visual emphasis, не контейнер і не group.

**Що маємо зараз:** `NodeItem` має кольорову рамку картки (`node.color`) і selection border. Окремого `Icon Frame` немає.

**Що реалізувати:** додати `frame_enabled`, `frame_color`, `frame_width` або `frame_margin` до `Node`; малювати рамку навколо іконки/фото, не навколо всієї картки; додати controls у `NodeDialog` і `PropertiesPanel`.

**Технічний підхід у PyQt6:** у `NodeItem.paint()` після розрахунку `top_area_rect` намалювати `QPen(QColor(frame_color), frame_width)` навколо `icon_rect`; для фото і емодзі використовувати однакову рамку; у `Node.to_dict()/from_dict()` додати поля з defaults.

**Критерій приймання:** вузол може мати синю картку/тип і червоний Icon Frame навколо фото/іконки; вимкнення frame повертає звичайний вигляд; JSON зберігає frame.

### P2.3 ✅ Group / Ungroup

**Що це в i2:** **Group** — persistent grouping вибраних chart items; група має handle, її можна переміщувати разом, розгруповувати, вибирати grouped items, видаляти group.

**Що маємо зараз:** `GroupItem` створює напівпрозорий контейнер для вибраних `NodeItem`; переміщення group рухає members; є `group_selected()` і `ungroup_selected()`.

**Що реалізувати:** зберігати групи у JSON; додати команди undo/redo для group/ungroup; додати контекстне меню group: `Select Grouped Items`, `Delete Group`; уточнити, що групи flat, без nested groups.

**Технічний підхід у PyQt6:** додати модель `GroupRecord(uuid, label, member_node_uuids, rect/style)`; `GroupItem` будувати з моделі; при переміщенні оновлювати positions members; у `save_to_json()` додати `groups`.

**Критерій приймання:** група не зникає після save/load; Ctrl+G і Ctrl+Shift+G підтримують undo; можна вибрати всі елементи групи з контекстного меню.

### P2.4 ✅ Snap-to-grid

**Що це в i2:** допоміжні arrange/view controls для точного розміщення items на схемі.

**Що маємо зараз:** `DiagramCanvas.toggle_snap_to_grid()`, `get_snap_to_grid()`, прив'язка в `NodeItem.itemChange()` до 30px.

**Що реалізувати:** синхронізувати стан toolbar/menu, зберігати `snap_to_grid` у JSON, додати налаштування grid step.

**Технічний підхід у PyQt6:** у `save_to_json()` писати `snap_to_grid`; у `load_from_json()` відновлювати; створити `grid_size` у canvas; у меню `Вигляд` додати простий action/dialog для 15/30/60px.

**Критерій приймання:** після ввімкнення snap вузол стає на сітку; після save/load snap-state не губиться; toolbar/menu показують однаковий checked state.

### P2.5 ✅ Auto Layout MVP + реальні layout names i2

**Що це в i2:** association chart layouts мають реальні назви: **Peacock**, **Compact Peacock**, **Grouped**, **Hierarchy**, **Minimize Crossed Links**, **Organization**, **Packed**, **Circular**.

**Що маємо зараз:** `auto_layout_grid()` і `auto_layout_radial()`; це корисні MVP-алгоритми, але вони не є назвами i2 layout.

**Що реалізувати:** залишити Grid/Radial як internal/simple layouts, але в i2-секції меню додати справжні назви; спершу реалізувати `Circular`, `Peacock`, `Hierarchy`, `Grouped`; далі `Compact Peacock`, `Minimize Crossed Links`, `Organization`, `Packed`.

**Технічний підхід у PyQt6:** створити `LayoutEngine` з методами `apply_circular`, `apply_peacock`, `apply_hierarchy`, `apply_grouped`; за потреби використати `networkx` для connected components, degrees, shortest paths; позиції застосовувати через undo-friendly command `LayoutCommand`.

**Критерій приймання:** меню `Вигляд/Arrange > Auto Layout` містить назви `Peacock`, `Compact Peacock`, `Grouped`, `Hierarchy`, `Minimize Crossed Links`, `Organization`, `Packed`, `Circular`; мінімум 4 алгоритми реально змінюють позиції; undo повертає старе розташування.

### P2.6 Visual Search panel

**Що це в i2:** **Visual Search** — структурований пошук за entity/link type, semantic type, identity/label, Date & Time, attributes, linked entity patterns, link direction, selected/unselected scope, hidden items.

**Що маємо зараз:** `SearchPanel` шукає текст тільки по вузлах; `FilterPanel` фільтрує тільки за `Node.type`.

**Що реалізувати:** окрему dock-панель `VisualSearchPanel` з умовами: node type/family, link strength, link direction, text, date from/to, has photo, selected only, include hidden.

**Технічний підхід у PyQt6:** зробити `QDockWidget('Visual Search')`; у панелі використати `QComboBox`, `QLineEdit`, `QCheckBox`; логіку винести в `SearchQuery` object; результат виділяти або приховувати невалідні items залежно від action mode.

**Критерій приймання:** можна знайти "усі `Person`, які мають link direction `source_to_target` до `Phone` після 2024-01-01"; результат виділяється на canvas і не ламає звичайний text search.

### P2.7 Entity Type Registry та професійні іконки

**Що це в i2:** типи entity мають semantic family, representation, standard/custom icons; screen icon і print icon можуть мати різні розміри.

**Що маємо зараз:** `NODE_TYPES`, `NODE_TYPE_LABELS`, `NODE_DEFAULT_COLORS`, `NODE_ICONS` з 7 типами й емодзі.

**Що реалізувати:** `TypeRegistry` з базовими сімействами `Person`, `Organization`, `Phone`, `Motor Vehicle`, `Location`, `Event`, `Bank Account`; SVG/PNG іконки в `assets/icons/`; підтримка custom icon path.

**Технічний підхід у PyQt6:** замінити емодзі на `QPixmap`/`QIcon`; кешувати pixmaps; у `Node` додати `semantic_family`, `entity_type_id`, optional `icon_path`; старий `Vehicle` мігрувати в `Motor Vehicle`.

**Критерій приймання:** тип вузла розпізнається без підпису; `Bank Account` доступний у `NodeDialog`; старі вузли `Vehicle` відкриваються як `Motor Vehicle` або з legacy alias.

---

## ПРІОРИТЕТ 3 — Polish

### P3.1 ✅ Link label readability

**Що це в i2:** label link має бути читабельним на chart surface і не зливатися з лінією.

**Що маємо зараз:** `_draw_label()` малює текст 9pt по центру лінії з білим фоном і padding 4px.

**Що реалізувати:** уникати перекриття label зі стрілкою; додати опцію показу/приховування label; у майбутньому підтримати displayed properties.

**Технічний підхід у PyQt6:** перенести label трохи від середини, якщо link дуже короткий; використовувати `QFontMetrics` для collision guard; додати `link.show_label: bool`.

**Критерій приймання:** підпис читається на solid/dashed/dotted lines, не перекриває наконечник стрілки і може бути прихований.

### P3.2 ✅ Show-connected filter

**Що це в i2:** близько до lightweight reveal/hide або "Find Linked" workflow: швидко залишити на екрані тільки пов'язані items.

**Що маємо зараз:** `show_only_connected(node_uuid)` приховує непов'язані вузли й links; `show_all_nodes()` повертає видимість.

**Що реалізувати:** додати depth 1/2/3, опцію direction, окремий action "Find Linked"; не перетирати стан Visual Search без підтвердження.

**Технічний підхід у PyQt6:** узагальнити у `find_linked(start_uuids, depth=1, respect_direction=False)`; обходити граф BFS; застосовувати visibility через окремий `visibility_filter_state`.

**Критерій приймання:** користувач може показати тільки сусідів depth=1 або мережу depth=2; кнопка "Показати всі" стабільно повертає всі items.

### P3.3 Timeline View

**Що це в i2:** timeline chart має time bar зліва направо; items можуть бути `Free`, `Ordered`, `Controlling`; `Theme line` показує довготривалий суб'єкт, `Event frame` — подію в часі.

**Що маємо зараз:** у `Node` є просте поле `date`, але немає time model, time bar, Theme line або Event frame.

**Що реалізувати:** окремий режим "Схема / Хронологія"; нормалізовані `date_time`, `start_date_time`, `end_date_time`; Event frame для `Event`; Theme line для Person/Phone/Bank Account.

**Технічний підхід у PyQt6:** зробити `TimelineView(QWidget або QGraphicsView)`; парсити дати через `datetime`; розкладати items по X за часом; Y-групи за entity/theme; links між theme lines позиціонувати за date_time.

**Критерій приймання:** на тестових даних із 5 подіями видно послідовність у часі; подія без дати не ламає layout; фільтр date range приховує items поза діапазоном.

### P3.4 Ribbon-like navigation / menu cleanup

**Що це в i2:** ANB 9.x використовує Office-style ribbon з вкладками `File`, `Home`, `Select`, `Analyze`, `Style`, `Arrange`, `View`, `Publish`.

**Що маємо зараз:** простий toolbar і меню `Файл`, `Редагування`, `Вигляд`, `Інструменти`, `Довідка`.

**Що реалізувати:** не обов'язково повний ribbon, але треба розкласти дії по логічних секціях: `Analyze`, `Style`, `Arrange`, `Publish`; прибрати змішування layout/search/export в одному місці.

**Технічний підхід у PyQt6:** зробити кілька `QToolBar` або tabbed toolbar; actions винести в factory methods; reuse тих самих `QAction` у menu і toolbar, щоб checked state був один.

**Критерій приймання:** Find Path і Visual Search лежать в `Analyze`; layout-и в `Arrange`; style controls у `Style`; export/print у `Publish` або `File`.

### P3.5 Import/export polish

**Що це в i2:** ANB має import specs (`.ximp`, `.oimp`), CSV/TSV/Excel/XML/ANX, link direction/strength/date mapping, matching rules, optional layout after import.

**Що маємо зараз:** CSV import для `nodes.csv` і `links.csv`, JSON save/load, PNG/PDF export.

**Що реалізувати:** розширити CSV columns під v2 model; додати import preview; підтримати `strength`, `date_time`, `source_reference`, `weighting_value`; у перспективі ANX-like XML export/import.

**Технічний підхід у PyQt6:** створити `ImportWizard(QDialog)`; використовувати `csv.DictReader` і validation report; перед імпортом показувати кількість вузлів/зв'язків і помилки; після імпорту опційно запускати layout.

**Критерій приймання:** CSV з `strength,direction,date_time` імпортується без ручних правок; помилки рядків показані користувачу; валідні рядки імпортуються навіть якщо частина рядків помилкова.

### P3.6 Рефакторинг `main.py` на модулі

**Що це в i2:** не функція i2, а технічна вимога для підтримуваності нашого клона.

**Що маємо зараз:** `main.py` має понад 4000 рядків і містить моделі, commands, items, dialogs, panels, canvas, import/export, main window.

**Що реалізувати:** рознести код по модулях після стабілізації v2 model.

**Технічний підхід у PyQt6:** структура:

| Файл | Відповідальність |
|---|---|
| `models.py` | `Node`, `Link`, `GroupRecord`, type registries, schema migration |
| `commands.py` | всі `QUndoCommand` |
| `items.py` | `NodeItem`, `LinkItem`, `GroupItem`, shape helpers |
| `dialogs.py` | `NodeDialog`, `LinkDialog`, import dialogs |
| `panels.py` | `PropertiesPanel`, `SearchPanel`, `FilterPanel`, `VisualSearchPanel` |
| `canvas.py` | `DiagramCanvas`, graph traversal, layout application |
| `io_utils.py` | JSON/CSV import/export |
| `main.py` | тільки `MainWindow` і `main()` |

**Критерій приймання:** застосунок запускається без зміни UX; imports не циклічні; простий smoke-тест відкриває вікно, створює вузол, створює link, зберігає JSON.

---

## Пріоритизований план виконання

| # | Задача | Пріоритет | Статус |
|---|---|---|---|
| 1 | Link color/width: застосування при створенні + undo | P1 | ✅ базово є, треба закрити gaps |
| 2 | Direction arrows: обрізання лінії до межі вузла | P1 | ✅ базово є, треба покращити |
| 3 | Link Strength `Confirmed/Unconfirmed/Tentative` | P1 | ⏳ |
| 4 | Повна Link-модель + schema v2 migration | P1 | ⏳ |
| 5 | Find Path BFS між 2 вузлами | P1 | ⏳ |
| 6 | Node color button / Style sync | P2 | ✅ базово готово |
| 7 | Icon Frame | P2 | ⏳ |
| 8 | Group persistence + commands | P2 | ✅ базово є, треба збереження |
| 9 | Snap-to-grid persistence/settings | P2 | ✅ базово готово |
| 10 | i2 layout names + 4 перші реальні алгоритми | P2 | ✅ grid/radial MVP, i2 layouts ще ні |
| 11 | Visual Search panel | P2 | ⏳ |
| 12 | Entity Type Registry + `Bank Account` / `Motor Vehicle` | P2 | ⏳ |
| 13 | Link label show/hide/collision polish | P3 | ✅ базово готово |
| 14 | Show-connected -> Find Linked depth/direction | P3 | ✅ базово готово |
| 15 | Timeline View | P3 | ⏳ |
| 16 | Ribbon-like navigation cleanup | P3 | ⏳ |
| 17 | Import/export polish | P3 | ⏳ |
| 18 | Рефакторинг `main.py` | P3 | ⏳ |

---

## Мінімальний definition of done для v2.0 milestone

v2.0 можна вважати завершеною, коли:

1. `Link` має `strength`, `direction`, `multiplicity`, date/provenance поля і міграцію зі schema v1.
2. Direction arrows видно коректно на межі вузлів.
3. `Confirmed/Unconfirmed/Tentative` працюють як семантика, а не як випадковий стиль.
4. `Find Path` знаходить BFS-шлях між двома вибраними вузлами.
5. `Visual SearchPanel` дозволяє структурований пошук хоча б за type, text, date, direction, strength.
6. `Icon Frame` окремий від кольору вузла.
7. "Що вже є" не регресує: link color/width, snap-to-grid, grouping, grid/radial layout, show-connected filter, node color button, link label improvements залишаються робочими.

---

## Джерела з research-файлу

Основні сторінки, на які спирається research: IBM i2 Analyst's Notebook docs про Entities, Links, Custom icons, Modify item appearance, Layouts, Searching your chart, Find networks, Publish a chart; IBM support notes про multiple links import, iBase timeline behavior, Visual Search date range.

Цей TZ не копіює IBM assets або закриті template-файли. Для точного 1:1 набору стандартних типів та іконок потрібен встановлений IBM i2 Analyst's Notebook і локальні файли на кшталт `Standard.ant` та shared image resources.

---

## Перевірка: що могло бути пропущено

### [GAP-1] Неповний Entity Type Registry
**Знайдено в:** research/IBM docs
**Відсутнє в TZ:** у research окремо згадані `Bank Card` (`Credit Card`, `Debit Card`), `Web Site` (`Web Page`), `Bank`, а також поширені investigation types `Email`, `Weapon/Bullet`, `Address`, `Account`, `Document`, `Telephone`. У TZ базовий registry зводиться до `Person`, `Organization`, `Phone`, `Motor Vehicle`, `Location`, `Event`, `Bank Account` і не фіксує точні розміри custom icons/attribute symbols.
**Рекомендація:** розширити таблицю semantic families і P2.7: додати `Bank Card`, `Web Site`, `Bank` та common investigation aliases; у `TypeRegistry` зберігати `screen_icon_size=32x32`, `print_icon_size=120x120`, `attribute_symbol_screen=12x8`, `attribute_symbol_print=45x30`.

### [GAP-2] Немає повної специфікації Display/Style toggles
**Знайдено в:** research/IBM docs
**Відсутнє в TZ:** research перелічує style pages `Type`, `Display`, `Font`, `Frame`, `Connection` і toggles `Label`, `Date & Time`, `Description`, `Grades`, `Source Type`, `Source Reference`, `Picture`, `Frame`, `Pin`, `Type Icon`, `Type Name`, `Link Area`. TZ описує color/width, Icon Frame і label readability, але не задає повну модель display flags.
**Рекомендація:** додати задачу `StylePanel / ItemStyle`: `display_flags`, font/shading, frame/margin, link connection options, displayed properties; acceptance: кожен toggle з IBM docs можна ввімкнути/вимкнути для entity/link і зберегти в JSON.

### [GAP-3] Conditional Formatting відсутній як окрема функція
**Знайдено в:** research/IBM docs
**Відсутнє в TZ:** research описує conditional formatting: правила можуть змінювати visibility, font style, entity/link type, enlargement, shade color, icon frame, line width і line strength; Premium має live formatting. У TZ цього немає ні в пріоритетах, ні в DoD.
**Рекомендація:** додати P2/P3 задачу `ConditionalFormattingEngine`: rule model за attributes/properties/ranges/lookup tables, preview/apply/reset, серіалізація правил; live reapply залишити як optional для майбутніх i2 Analyze/connectors.

### [GAP-4] Cards/Attributes є в моделі, але немає workflow
**Знайдено в:** research/IBM docs
**Відсутнє в TZ:** research уточнює, що cards - це unstructured provenance для entities/links, searchable, але не показується прямо на chart surface. TZ додає `cards[]` і `attributes[]` у модель, але не описує UI для Edit Data/Attributes/Cards, пошук по cards, імпорт provenance або звіти `All Cards`.
**Рекомендація:** додати `DataCardsDialog` з вкладками `Attributes`, `Cards`, `Sources`; додати cards до `Find Text`/`Visual Search` scope і до report/export pipeline; не рендерити card contents на полотні за замовчуванням.

### [GAP-5] Multiple links glossed over
**Знайдено в:** research/IBM docs
**Відсутнє в TZ:** TZ згадує `multiplicity: Single | Directed | Multiple`, але не фіксує важливу поведінку IBM: `Directed` може дати до чотирьох displayed links, бо `source_to_target`, `target_to_source`, `bidirectional` і `none` розводяться окремо; link spacing є chart property; weights можуть імпортуватися з `.xwgt`/CSV-like files.
**Рекомендація:** додати `ChartProperties.link_spacing`, renderer для offset/fan multiple links, grouping key для `Directed`, тест з 4 напрямками між тими самими двома вузлами; для weights додати імпорт `weighting_value` з CSV і future `.xwgt`.

### [GAP-6] Advanced Analyze tools тільки названі
**Знайдено в:** research/IBM docs
**Відсутнє в TZ:** у термінах згадані `Find Connecting Network`, `Find Clusters`, `SNA`, але план реалізації деталізує лише `Find Path`, `Visual Search` і базовий `Find Linked`. Не специфіковані `List Items`, `Linked Entities`, `Bar Charts/Histograms`, `Time Wheel`, `Activity View`, `Social Network Analysis`, `Merge and Combine`.
**Рекомендація:** додати окремий P2/P3 backlog для Analyze: `FindConnectingNetwork`, `ClusterAnalysis`, `SNA metrics`, `ListItemsPanel`, `Histogram/TimeWheel`, `MergeCombineDialog`; для кожного задати мінімальні inputs, outputs і критерій приймання.

### [GAP-7] Timeline та Activity View недоописані
**Знайдено в:** research/IBM docs
**Відсутнє в TZ:** P3.3 описує базову Timeline View, але пропускає bands `Interval`, `Tick`, `Marker`, copy-to-new-timeline behavior, де більшість entities стають theme lines, event-like entities лишаються event frames, groups видаляються, а також Activity View з масштабами від milliseconds до years і повторюваними scales `hour-of-day`/`day-of-week`.
**Рекомендація:** розширити P3.3: додати `TimeBar` з bands, `copy_to_timeline_chart()`, правила конвертації representations, видалення groups при timeline copy, `ActivityView` як окрему dock/panel з configurable time scales.

### [GAP-8] Import wizard не покриває деталі IBM import specs
**Знайдено в:** research/IBM docs
**Відсутнє в TZ:** P3.5 згадує CSV/TSV/Excel/XML/ANX і `.ximp/.oimp`, але не деталізує wizard behavior: delimiter/fixed width, encoding, exclude rows, column actions, mini entity-link import design, mapping columns to properties, link direction/strength, date/time formats/time zones, matching rules, blank record removal, link occurrence thresholds, apply layout after import. Також не визначено позицію щодо `.txt`, clipboard text, `.anb`, `.ant`.
**Рекомендація:** розширити `ImportWizard`: профілі import spec, preview з row-level errors, mapping screen для nodes/links/properties, date/time/timezone parser, matching/dedup rules, optional layout after import; для proprietary `.anb/.ant` явно написати "тільки якщо є легальний parser/spec, інакше не підтримуємо".

### [GAP-9] Publish/Export значно вужчий за IBM docs
**Знайдено в:** research/IBM docs
**Відсутнє в TZ:** research містить export/publish: `.anb`, redacted `.anb`, `GIF/JPEG/PNG/TIFF/BMP`, PDF security options, PowerPoint slide from snapshots, print page setup, text reports, clipboard as OLE/metafile/bitmap, chart reports for entities/links/cards/attributes. TZ фактично планує PNG/PDF/print preview і загальний import/export polish.
**Рекомендація:** додати `Publish` backlog: multi-image export formats, PDF options, snapshots, PowerPoint export, report templates (`Full Report`, `Entities and Links`, `Grades`, `Descriptions`, `All Cards`), clipboard export; redacted/proprietary `.anb` позначити як compatibility research, не як MVP.

### [GAP-10] Ribbon/navigation пропускає File/Home/Select/View деталі
**Знайдено в:** research/IBM docs
**Відсутнє в TZ:** P3.4 пропонує секції `Analyze`, `Style`, `Arrange`, `Publish`, але research має повну ribbon map: `File`, `Home`, `Select`, `Analyze`, `Style`, `Arrange`, `View`, `Publish`. Не описані selection sets `0-9`, invert selection, semantic/type selection, Chart Properties, Options, panes/reveal/hide, split view, drag chart.
**Рекомендація:** додати action map по всіх ribbon tabs; для `Select` створити `SelectionSetManager` з 10 слотами, invert/type/semantic selection; для `File/View` додати `ChartPropertiesDialog`, panes/reveal/hide state і split-view як future task.

### [GAP-11] Group описаний занадто схоже на container
**Знайдено в:** research/IBM docs
**Відсутнє в TZ:** research чітко розділяє `Group`, `Icon Frame`, `Box/Circle`: group - це persistent membership з handle, а не візуальний контейнер; Box/Circle можуть обводити items як representations. У TZ поточний `GroupItem` названо напівпрозорим контейнером, що може змішати IBM Group з Box/Circle behavior.
**Рекомендація:** у наступній редакції перейменувати поточний візуальний прямокутник на implementation detail (`GroupOverlay`), а модель зробити як `GroupRecord(uuid, member_ids, handle_pos, label)`; Box/Circle реалізувати окремо як entity representations; явно записати flat groups, no nested groups, і правила для layout tools, які ігнорують або розривають groups.

### [GAP-12] Shape Tool не серіалізується, хоча згаданий поруч із JSON save/load
**Знайдено в:** main.py
**Відсутнє в TZ:** у `main.py` Shape Tool створює `QGraphicsLineItem`, `QGraphicsEllipseItem`, `QGraphicsRectItem`, `QGraphicsSimpleTextItem`, але `save_to_json()` зберігає тільки `nodes` і `links`. У секції "Що вже є" Shape Tool і JSON save/load стоять як готові можливості, але не сказано, що намальовані фігури зникнуть після save/load.
**Рекомендація:** або додати відоме обмеження в "Що вже є", або створити `ShapeRecord` (`type`, geometry, pen, brush, text, z`) і додати `shapes[]` до JSON; acceptance: лінія/коло/прямокутник/текст виживають після save/load.
