from __future__ import annotations
import base64
from datetime import datetime
from typing import Optional, TYPE_CHECKING

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QLineEdit,
    QPushButton, QCheckBox, QComboBox, QScrollArea, QFrame, QStackedWidget,
    QListWidget, QListWidgetItem, QTextEdit, QColorDialog, QGroupBox,
    QToolButton, QTabWidget, QGraphicsView, QGraphicsScene, QDockWidget,
)
from PyQt6.QtCore import Qt, QRectF, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor, QFont, QImage, QPixmap

from constants import NODE_TYPE_LABELS, LINE_TYPE_LABELS, DIRECTION_LABELS, LINK_STRENGTH_LABELS

if TYPE_CHECKING:
    from canvas import DiagramCanvas


class _NoteEdit(QTextEdit):
    """QTextEdit що сигналізує про завершення редагування при втраті фокусу."""
    editing_finished = pyqtSignal()

    def focusOutEvent(self, event) -> None:
        super().focusOutEvent(event)
        self.editing_finished.emit()


class PropertiesPanel(QWidget):
    """Бічна панель, що відображає властивості поточного виділеного елемента."""

    node_edit_requested = pyqtSignal(str)
    link_edit_requested = pyqtSignal(str)
    node_inline_changed = pyqtSignal(str, str, str)
    link_inline_changed = pyqtSignal(str, str, str)
    node_color_changed = pyqtSignal(str, str)

    _PAGE_EMPTY = 0
    _PAGE_MULTIPLE = 1
    _PAGE_NODE = 2
    _PAGE_LINK = 3

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedWidth(240)
        self._current_node_uuid: str = ''
        self._current_link_uuid: str = ''
        self._updating: bool = False
        self._node_title_orig: str = ''
        self._node_note_orig: str = ''
        self._link_label_orig: str = ''
        self._build_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        title_label = QLabel('Властивості')
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(11)
        title_label.setFont(title_font)
        title_label.setContentsMargins(10, 8, 10, 6)
        title_label.setStyleSheet('background: #f0f0f0; border-bottom: 1px solid #d0d0d0;')
        root.addWidget(title_label)

        self._stack = QStackedWidget()
        root.addWidget(self._stack)

        empty_page = QWidget()
        empty_layout = QVBoxLayout(empty_page)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_lbl = QLabel("Виберіть вузол або зв'язок,\nщоб переглянути властивості")
        empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_lbl.setWordWrap(True)
        empty_lbl.setStyleSheet('color: #999; font-size: 12px;')
        empty_layout.addWidget(empty_lbl)
        self._stack.addWidget(empty_page)

        multi_page = QWidget()
        multi_layout = QVBoxLayout(multi_page)
        multi_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._multi_label = QLabel('Вибрано N елементів')
        self._multi_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._multi_label.setStyleSheet('color: #555; font-size: 12px;')
        multi_layout.addWidget(self._multi_label)
        self._stack.addWidget(multi_page)

        self._stack.addWidget(self._build_node_page())
        self._stack.addWidget(self._build_link_page())
        self._stack.setCurrentIndex(self._PAGE_EMPTY)

    def _build_node_page(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        form = QFormLayout(container)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(8)
        form.setContentsMargins(10, 10, 10, 10)

        self._node_photo_label = QLabel()
        self._node_photo_label.setFixedSize(60, 60)
        self._node_photo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._node_photo_label.setStyleSheet(
            'border: 1px solid #ccc; border-radius: 4px; background: #f5f5f5;'
        )
        self._node_photo_label.hide()
        form.addRow('', self._node_photo_label)

        self._node_title_edit = QLineEdit()
        self._node_title_edit.setPlaceholderText('Введіть назву…')
        self._node_title_edit.editingFinished.connect(self._on_title_committed)
        form.addRow('Назва:', self._node_title_edit)

        self._node_type_lbl = QLabel()
        form.addRow('Тип:', self._node_type_lbl)

        self._node_note_edit = _NoteEdit()
        self._node_note_edit.setFixedHeight(70)
        self._node_note_edit.setPlaceholderText('Примітка…')
        self._node_note_edit.editing_finished.connect(self._on_note_committed)
        form.addRow('Примітка:', self._node_note_edit)

        self._node_color_btn = QPushButton()
        self._node_color_btn.setFixedWidth(100)
        self._node_color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._node_color_btn.setToolTip('Клік — змінити колір вузла')
        self._node_color_btn.clicked.connect(self._on_node_color_btn_clicked)
        form.addRow('Колір:', self._node_color_btn)

        self._node_date_lbl = QLabel()
        form.addRow('Дата:', self._node_date_lbl)

        self._node_uuid_lbl = QLabel()
        uuid_font = QFont()
        uuid_font.setPointSize(9)
        self._node_uuid_lbl.setFont(uuid_font)
        self._node_uuid_lbl.setStyleSheet('color: #999;')
        self._node_uuid_lbl.setWordWrap(True)
        self._node_uuid_lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        form.addRow('UUID:', self._node_uuid_lbl)

        self._node_edit_btn = QPushButton('Редагувати…')
        self._node_edit_btn.clicked.connect(self._on_node_edit_clicked)
        form.addRow('', self._node_edit_btn)

        scroll.setWidget(container)
        return scroll

    def _build_link_page(self) -> QScrollArea:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        form = QFormLayout(container)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(8)
        form.setContentsMargins(10, 10, 10, 10)

        self._link_label_edit = QLineEdit()
        self._link_label_edit.setPlaceholderText("Підпис зв'язку…")
        self._link_label_edit.editingFinished.connect(self._on_link_label_committed)
        form.addRow('Підпис:', self._link_label_edit)

        self._link_type_lbl = QLabel()
        form.addRow('Тип лінії:', self._link_type_lbl)

        self._link_dir_lbl = QLabel()
        form.addRow('Напрямок:', self._link_dir_lbl)

        self._link_note_lbl = QLabel()
        self._link_note_lbl.setWordWrap(True)
        form.addRow('Примітка:', self._link_note_lbl)

        self._link_uuid_lbl = QLabel()
        uuid_font = QFont()
        uuid_font.setPointSize(9)
        self._link_uuid_lbl.setFont(uuid_font)
        self._link_uuid_lbl.setStyleSheet('color: #999;')
        self._link_uuid_lbl.setWordWrap(True)
        self._link_uuid_lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse
        )
        form.addRow('UUID:', self._link_uuid_lbl)

        self._link_edit_btn = QPushButton('Редагувати…')
        self._link_edit_btn.clicked.connect(self._on_link_edit_clicked)
        form.addRow('', self._link_edit_btn)

        scroll.setWidget(container)
        return scroll

    def _on_title_committed(self) -> None:
        if self._updating or not self._current_node_uuid:
            return
        new_val = self._node_title_edit.text().strip()
        if new_val != self._node_title_orig:
            self.node_inline_changed.emit(self._current_node_uuid, 'title', new_val)
            self._node_title_orig = new_val

    def _on_note_committed(self) -> None:
        if self._updating or not self._current_node_uuid:
            return
        new_val = self._node_note_edit.toPlainText().strip()
        if new_val != self._node_note_orig:
            self.node_inline_changed.emit(self._current_node_uuid, 'note', new_val)
            self._node_note_orig = new_val

    def _on_link_label_committed(self) -> None:
        if self._updating or not self._current_link_uuid:
            return
        new_val = self._link_label_edit.text().strip()
        if new_val != self._link_label_orig:
            self.link_inline_changed.emit(self._current_link_uuid, 'label', new_val)
            self._link_label_orig = new_val

    def _on_node_edit_clicked(self) -> None:
        if self._current_node_uuid:
            self.node_edit_requested.emit(self._current_node_uuid)

    def _on_link_edit_clicked(self) -> None:
        if self._current_link_uuid:
            self.link_edit_requested.emit(self._current_link_uuid)

    def _on_node_color_btn_clicked(self) -> None:
        if not self._current_node_uuid:
            return
        current = self._node_color_btn.property('_color') or '#4A90D9'
        c = QColorDialog.getColor(QColor(current), self, 'Колір вузла')
        if c.isValid():
            self.node_color_changed.emit(self._current_node_uuid, c.name())

    def show_empty(self) -> None:
        self._stack.setCurrentIndex(self._PAGE_EMPTY)

    def show_multiple(self, count: int) -> None:
        self._multi_label.setText(f'Вибрано {count} елементів')
        self._stack.setCurrentIndex(self._PAGE_MULTIPLE)

    def show_node(self, node) -> None:
        self._current_node_uuid = node.uuid
        if node.photo_base64:
            try:
                raw = base64.b64decode(node.photo_base64)
                img = QImage()
                if img.loadFromData(raw) and not img.isNull():
                    pix = QPixmap.fromImage(img).scaled(
                        60, 60,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    self._node_photo_label.setPixmap(pix)
                    self._node_photo_label.setText('')
                    self._node_photo_label.show()
                else:
                    self._node_photo_label.hide()
            except Exception:
                self._node_photo_label.hide()
        else:
            self._node_photo_label.hide()

        self._updating = True
        self._node_title_edit.setText(node.title or '')
        self._node_note_edit.setPlainText(node.note or '')
        self._updating = False
        self._node_title_orig = node.title or ''
        self._node_note_orig = node.note or ''
        self._node_type_lbl.setText(NODE_TYPE_LABELS.get(node.type, node.type))

        color = node.color or '#4A90D9'
        c = QColor(color)
        lum = (c.red() * 299 + c.green() * 587 + c.blue() * 114) / 1000
        text_col = '#ffffff' if lum < 128 else '#000000'
        self._node_color_btn.setStyleSheet(
            f'background-color:{color}; color:{text_col}; border:1px solid #888;'
        )
        self._node_color_btn.setText(color)
        self._node_color_btn.setProperty('_color', color)

        self._node_date_lbl.setText(node.date or '—')
        self._node_uuid_lbl.setText(node.uuid)
        self._stack.setCurrentIndex(self._PAGE_NODE)

    def show_link(self, link) -> None:
        self._current_link_uuid = link.uuid
        self._updating = True
        self._link_label_edit.setText(link.label or '')
        self._updating = False
        self._link_label_orig = link.label or ''
        self._link_type_lbl.setText(LINE_TYPE_LABELS.get(link.line_type, link.line_type))
        self._link_dir_lbl.setText(DIRECTION_LABELS.get(link.direction, link.direction))
        self._link_note_lbl.setText(link.note or '—')
        self._link_uuid_lbl.setText(link.uuid)
        self._stack.setCurrentIndex(self._PAGE_LINK)


class SearchPanel(QWidget):
    """Горизонтальна панель для пошуку вузлів на схемі."""

    def __init__(self, canvas: DiagramCanvas, parent=None) -> None:
        super().__init__(parent)
        self._canvas = canvas
        self._results: list = []
        self._result_idx: int = 0
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(4)

        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText('Пошук по вузлах…')
        self._search_edit.setMinimumWidth(180)
        self._search_edit.returnPressed.connect(self._do_search)
        layout.addWidget(self._search_edit)

        find_btn = QPushButton('Знайти')
        find_btn.clicked.connect(self._do_search)
        layout.addWidget(find_btn)

        prev_btn = QPushButton('←')
        prev_btn.setFixedWidth(30)
        prev_btn.setToolTip('Попередній результат')
        prev_btn.clicked.connect(self._go_prev)
        layout.addWidget(prev_btn)

        next_btn = QPushButton('→')
        next_btn.setFixedWidth(30)
        next_btn.setToolTip('Наступний результат')
        next_btn.clicked.connect(self._go_next)
        layout.addWidget(next_btn)

        self._count_label = QLabel('')
        self._count_label.setMinimumWidth(110)
        layout.addWidget(self._count_label)

        close_btn = QPushButton('×')
        close_btn.setFixedWidth(26)
        close_btn.setToolTip('Закрити пошук')
        close_btn.clicked.connect(self._close_search)
        layout.addWidget(close_btn)

    def _do_search(self) -> None:
        query = self._search_edit.text().strip().lower()
        self._results = []
        self._result_idx = 0
        if not query:
            self._count_label.setText('')
            self._canvas.scene().clearSelection()
            return
        for node in self._canvas.nodes.values():
            haystack = ' '.join([
                node.title or '',
                NODE_TYPE_LABELS.get(node.type, ''),
                node.note or '',
                node.date or '',
            ]).lower()
            if query in haystack:
                self._results.append(node.uuid)
        if self._results:
            self._count_label.setText(f'Знайдено: {len(self._results)}')
            self._select_result(0)
        else:
            self._count_label.setText('Нічого не знайдено')
            self._canvas.scene().clearSelection()

    def _select_result(self, idx: int) -> None:
        if not self._results:
            return
        idx = idx % len(self._results)
        self._result_idx = idx
        self._canvas.scene().clearSelection()
        target_uuid = self._results[idx]
        item = self._canvas.node_items.get(target_uuid)
        if item:
            item.setSelected(True)
            self._canvas.centerOn(item)

    def _go_prev(self) -> None:
        if self._results:
            self._select_result(self._result_idx - 1)

    def _go_next(self) -> None:
        if self._results:
            self._select_result(self._result_idx + 1)

    def _close_search(self) -> None:
        self._search_edit.clear()
        self._count_label.setText('')
        self._results = []
        self._result_idx = 0
        self._canvas.scene().clearSelection()
        dock = self.parent()
        if isinstance(dock, QDockWidget):
            dock.hide()


class FilterPanel(QWidget):
    """Панель для відображення/приховування вузлів за їх типом."""

    def __init__(self, canvas: DiagramCanvas, parent=None) -> None:
        super().__init__(parent)
        self._canvas = canvas
        self._checkboxes: dict = {}
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        title = QLabel('Фільтр за типом')
        title_font = QFont()
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        for key, label in NODE_TYPE_LABELS.items():
            cb = QCheckBox(label)
            cb.setChecked(True)
            cb.stateChanged.connect(self._on_filter_changed)
            self._checkboxes[key] = cb
            layout.addWidget(cb)

        btn_row = QHBoxLayout()
        show_all_btn = QPushButton('Показати всі')
        show_all_btn.clicked.connect(self._show_all)
        hide_all_btn = QPushButton('Сховати всі')
        hide_all_btn.clicked.connect(self._hide_all)
        btn_row.addWidget(show_all_btn)
        btn_row.addWidget(hide_all_btn)
        layout.addLayout(btn_row)

        layout.addStretch()

    def _on_filter_changed(self) -> None:
        visible = [key for key, cb in self._checkboxes.items() if cb.isChecked()]
        self._canvas.set_type_filter(visible)

    def _show_all(self) -> None:
        for cb in self._checkboxes.values():
            cb.blockSignals(True)
            cb.setChecked(True)
            cb.blockSignals(False)
        self._canvas.set_type_filter(list(self._checkboxes.keys()))

    def _hide_all(self) -> None:
        for cb in self._checkboxes.values():
            cb.blockSignals(True)
            cb.setChecked(False)
            cb.blockSignals(False)
        self._canvas.set_type_filter([])


class VisualSearchPanel(QWidget):
    """Структурований пошук по елементах схеми з фільтрами типу/strength/direction/дати."""

    def __init__(self, canvas: DiagramCanvas, parent=None) -> None:
        super().__init__(parent)
        self._canvas = canvas
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        title = QLabel('Візуальний пошук')
        f = QFont()
        f.setBold(True)
        title.setFont(f)
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(5)

        self._text_edit = QLineEdit()
        self._text_edit.setPlaceholderText('Текст у заголовку вузла…')
        form.addRow('Текст:', self._text_edit)

        self._type_combo = QComboBox()
        self._type_combo.addItem('Всі типи', userData='')
        for key, label in NODE_TYPE_LABELS.items():
            self._type_combo.addItem(label, userData=key)
        form.addRow('Тип:', self._type_combo)

        self._strength_combo = QComboBox()
        self._strength_combo.addItem('Будь-яка', userData='')
        for key, label in LINK_STRENGTH_LABELS.items():
            self._strength_combo.addItem(label, userData=key)
        form.addRow("Надійність зв'язку:", self._strength_combo)

        self._direction_combo = QComboBox()
        self._direction_combo.addItem('Будь-який', userData='')
        for key, label in DIRECTION_LABELS.items():
            self._direction_combo.addItem(label, userData=key)
        form.addRow('Напрямок:', self._direction_combo)

        self._date_from = QLineEdit()
        self._date_from.setPlaceholderText('РРРР-ММ-ДД')
        self._date_to = QLineEdit()
        self._date_to.setPlaceholderText('РРРР-ММ-ДД')
        form.addRow('Дата від:', self._date_from)
        form.addRow('Дата до:', self._date_to)

        layout.addLayout(form)

        btn_row = QHBoxLayout()
        search_btn = QPushButton('Пошук')
        search_btn.clicked.connect(self._run_search)
        reset_btn = QPushButton('Скинути')
        reset_btn.clicked.connect(self._reset)
        btn_row.addWidget(search_btn)
        btn_row.addWidget(reset_btn)
        layout.addLayout(btn_row)

        self._results_label = QLabel('Результати:')
        layout.addWidget(self._results_label)

        self._results_list = QListWidget()
        self._results_list.itemClicked.connect(self._on_result_clicked)
        layout.addWidget(self._results_list)

    def _run_search(self) -> None:
        text = self._text_edit.text().strip().lower()
        node_type = self._type_combo.currentData()
        strength_filter = self._strength_combo.currentData()
        direction_filter = self._direction_combo.currentData()
        date_from = self._date_from.text().strip()
        date_to = self._date_to.text().strip()

        matched_nodes: list = []
        for uid, node in self._canvas.nodes.items():
            if text and text not in (node.title or '').lower():
                continue
            if node_type and node.type != node_type:
                continue
            if date_from and node.date and node.date < date_from:
                continue
            if date_to and node.date and node.date > date_to:
                continue
            matched_nodes.append(uid)

        if strength_filter or direction_filter:
            linked_nodes: set = set()
            for lk in self._canvas.links.values():
                if strength_filter and getattr(lk, 'strength', '') != strength_filter:
                    continue
                if direction_filter and lk.direction != direction_filter:
                    continue
                linked_nodes.add(lk.source_uuid)
                linked_nodes.add(lk.target_uuid)
            matched_nodes = [u for u in matched_nodes if u in linked_nodes]

        matched_set = set(matched_nodes)
        for uid, it in self._canvas.node_items.items():
            it.setVisible(uid in matched_set)
        for uid, li in self._canvas.link_items.items():
            lk = self._canvas.links.get(uid)
            if lk:
                visible = lk.source_uuid in matched_set and lk.target_uuid in matched_set
                li.setVisible(visible)

        self._results_list.clear()
        for uid in matched_nodes:
            node = self._canvas.nodes[uid]
            item = QListWidgetItem(f"{node.title or '(без назви)'}  [{node.type}]")
            item.setData(Qt.ItemDataRole.UserRole, uid)
            self._results_list.addItem(item)
        self._results_label.setText(f'Результати: {len(matched_nodes)} знайдено')

    def _reset(self) -> None:
        self._text_edit.clear()
        self._type_combo.setCurrentIndex(0)
        self._strength_combo.setCurrentIndex(0)
        self._direction_combo.setCurrentIndex(0)
        self._date_from.clear()
        self._date_to.clear()
        self._results_list.clear()
        self._results_label.setText('Результати:')
        self._canvas.show_all_nodes()

    def _on_result_clicked(self, item: QListWidgetItem) -> None:
        uid = item.data(Qt.ItemDataRole.UserRole)
        node_it = self._canvas.node_items.get(uid)
        if node_it:
            self._canvas.centerOn(node_it)
            self._canvas.scene().clearSelection()
            node_it.setSelected(True)


class RibbonBar(QWidget):
    """Tabbed ribbon toolbar: Home / Analyze / Style / Arrange / Publish."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._tabs = QTabWidget()
        self._tabs.setTabPosition(QTabWidget.TabPosition.North)
        self._tabs.setMaximumHeight(96)
        self._tabs.setStyleSheet('QTabWidget::pane { border: none; margin: 0; }')
        vl = QVBoxLayout(self)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.addWidget(self._tabs)

    def add_tab(self, name: str) -> QHBoxLayout:
        container = QWidget()
        lay = QHBoxLayout(container)
        lay.setContentsMargins(4, 2, 4, 2)
        lay.setSpacing(4)
        self._tabs.addTab(container, name)
        return lay

    def add_group(self, lay: QHBoxLayout, title: str, actions: list) -> None:
        box = QGroupBox(title)
        gl = QHBoxLayout(box)
        gl.setContentsMargins(4, 0, 4, 4)
        gl.setSpacing(2)
        for a in actions:
            if a is None:
                sep = QFrame()
                sep.setFrameShape(QFrame.Shape.VLine)
                gl.addWidget(sep)
            else:
                btn = QToolButton()
                btn.setDefaultAction(a)
                btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBelowIcon)
                gl.addWidget(btn)
        lay.addWidget(box)

    @staticmethod
    def finalize(lay: QHBoxLayout) -> None:
        lay.addStretch(1)


class TimelinePanel(QWidget):
    """Dock-панель: відображає вузли і зв'язки з датами на часовій шкалі."""

    _DATE_FMTS = [
        '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d',
        '%d.%m.%Y %H:%M', '%d.%m.%Y', '%d/%m/%Y', '%m/%d/%Y',
    ]

    _TYPE_COLORS = {
        'Person': '#4CAF50', 'Organization': '#2196F3', 'Phone': '#FF9800',
        'Event': '#E91E63', 'Motor Vehicle': '#9C27B0', 'Document': '#607D8B',
        'Bank Account': '#00BCD4', 'Location': '#795548', 'Link': '#F44336',
    }

    def __init__(self, canvas: DiagramCanvas, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._canvas = canvas

        self._scene = QGraphicsScene(self)
        self._view = QGraphicsView(self._scene)
        self._view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOn)
        self._view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)

        self._start_edit = QLineEdit()
        self._start_edit.setPlaceholderText('Від (РРРР-ММ-ДД)')
        self._start_edit.setMaximumWidth(140)
        self._end_edit = QLineEdit()
        self._end_edit.setPlaceholderText('До (РРРР-ММ-ДД)')
        self._end_edit.setMaximumWidth(140)
        refresh_btn = QPushButton('Оновити')
        refresh_btn.clicked.connect(self.refresh)

        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel('Від:'))
        filter_row.addWidget(self._start_edit)
        filter_row.addWidget(QLabel('До:'))
        filter_row.addWidget(self._end_edit)
        filter_row.addWidget(refresh_btn)
        filter_row.addStretch(1)

        root = QVBoxLayout(self)
        root.addLayout(filter_row)
        root.addWidget(self._view, 1)

    def _parse_date(self, s: str) -> Optional[datetime]:
        if not s:
            return None
        s = s.strip()
        for fmt in self._DATE_FMTS:
            try:
                return datetime.strptime(s, fmt)
            except ValueError:
                pass
        return None

    def refresh(self) -> None:
        self._scene.clear()

        filter_start = self._parse_date(self._start_edit.text())
        filter_end = self._parse_date(self._end_edit.text())

        items: list = []

        for node_item in self._canvas.node_items.values():
            node = node_item.node
            dt = self._parse_date(getattr(node, 'date', ''))
            if dt is None:
                continue
            if filter_start and dt < filter_start:
                continue
            if filter_end and dt > filter_end:
                continue
            items.append((dt, node.title or node.type, node.type))

        for link_item in self._canvas.link_items.values():
            link = link_item.link
            dt = self._parse_date(getattr(link, 'date_time', ''))
            if dt is None:
                dt = self._parse_date(getattr(link, 'start_date_time', ''))
            if dt is None:
                continue
            if filter_start and dt < filter_start:
                continue
            if filter_end and dt > filter_end:
                continue
            lbl = getattr(link, 'label', '') or "Зв'язок"
            items.append((dt, lbl, 'Link'))

        if not items:
            msg = self._scene.addText('Немає елементів із датами')
            msg.setDefaultTextColor(QColor('#888888'))
            self._scene.setSceneRect(0, 0, 400, 60)
            return

        items.sort(key=lambda x: x[0])
        min_dt = items[0][0]
        max_dt = items[-1][0]
        span = max(1.0, (max_dt - min_dt).total_seconds())

        MARGIN_L = 130
        MARGIN_T = 36
        TL_W = 860
        LANE_H = 44
        DOT_R = 7

        type_order = list(dict.fromkeys(t for _, _, t in items))
        lane_y = {t: MARGIN_T + i * LANE_H for i, t in enumerate(type_order)}

        axis_y = MARGIN_T - 14
        axis_pen = QPen(QColor('#444444'), 1)
        self._scene.addLine(MARGIN_L, axis_y, MARGIN_L + TL_W, axis_y, axis_pen)

        lane_pen = QPen(QColor('#e0e0e0'), 1, Qt.PenStyle.DashLine)
        for t, y in lane_y.items():
            lbl = self._scene.addText(t)
            lbl.setDefaultTextColor(QColor('#555555'))
            font = QFont()
            font.setPointSize(8)
            lbl.setFont(font)
            lbl.setPos(2, y - 11)
            self._scene.addLine(MARGIN_L, y, MARGIN_L + TL_W, y, lane_pen)

        tick_pen = QPen(QColor('#333333'), 1)
        for dt, label, etype in items:
            frac = (dt - min_dt).total_seconds() / span
            x = MARGIN_L + frac * TL_W
            y = lane_y.get(etype, MARGIN_T)
            color = QColor(self._TYPE_COLORS.get(etype, '#9E9E9E'))

            self._scene.addLine(x, axis_y - 5, x, axis_y + 5, tick_pen)
            self._scene.addEllipse(
                x - DOT_R, y - DOT_R, DOT_R * 2, DOT_R * 2,
                QPen(color.darker(130), 1), QBrush(color)
            )

            item_font = QFont()
            item_font.setPointSize(7)
            lbl_item = self._scene.addText(label[:22])
            lbl_item.setDefaultTextColor(QColor('#222222'))
            lbl_item.setFont(item_font)
            lbl_item.setPos(x - 28, y - DOT_R - 18)

            date_font = QFont()
            date_font.setPointSize(6)
            date_item = self._scene.addText(dt.strftime('%d.%m.%y'))
            date_item.setDefaultTextColor(QColor('#999999'))
            date_item.setFont(date_font)
            date_item.setPos(x - 18, axis_y + 6)

        total_h = MARGIN_T + len(type_order) * LANE_H + 30
        self._scene.setSceneRect(0, 0, MARGIN_L + TL_W + 50, total_h)
        self._view.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
