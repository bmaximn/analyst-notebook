from __future__ import annotations
import base64
import csv
import os
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QHBoxLayout, QComboBox, QLineEdit,
    QTextEdit, QPushButton, QLabel, QCheckBox, QSpinBox, QDialogButtonBox,
    QColorDialog, QFileDialog, QMessageBox, QScrollArea, QWidget,
    QStackedWidget, QTableWidget, QTableWidgetItem,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPixmap, QImage, QFont

from models import Node, Link
from constants import (
    NODE_TYPE_LABELS, NODE_DEFAULT_COLORS, LINE_TYPE_LABELS,
    DIRECTION_LABELS, LINK_STRENGTH_LABELS,
)


class NodeDialog(QDialog):
    """Діалог для створення нового або редагування існуючого вузла."""

    def __init__(self, parent=None, node: Node = None) -> None:
        super().__init__(parent)
        self._node = node
        self._color: str = NODE_DEFAULT_COLORS.get('Person', '#4A90D9')
        self._custom_color: bool = False
        self._photo_b64: str = ''

        self.setWindowTitle('Редагувати вузол' if node else 'Новий вузол')
        self.setMinimumWidth(420)
        self._build_ui()

        if node:
            self._populate_from_node(node)

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setSpacing(10)
        root_layout.setContentsMargins(12, 12, 12, 12)

        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(8)

        self._type_combo = QComboBox()
        for key, label in NODE_TYPE_LABELS.items():
            self._type_combo.addItem(label, userData=key)
        self._type_combo.currentIndexChanged.connect(self._on_type_changed)
        form.addRow('Тип:', self._type_combo)

        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("Назва вузла (обов'язково)")
        self._title_edit.textChanged.connect(self._validate)
        form.addRow('Назва:', self._title_edit)

        self._note_edit = QTextEdit()
        self._note_edit.setPlaceholderText('Довільна примітка…')
        self._note_edit.setMaximumHeight(72)
        form.addRow('Примітка:', self._note_edit)

        self._date_edit = QLineEdit()
        self._date_edit.setPlaceholderText('дд.мм.рррр або довільно')
        form.addRow('Дата:', self._date_edit)

        self._color_btn = QPushButton()
        self._color_btn.setFixedWidth(90)
        self._color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._color_btn.clicked.connect(self._on_pick_color)
        self._refresh_color_button()
        form.addRow('Колір:', self._color_btn)

        photo_row = QHBoxLayout()
        photo_row.setSpacing(6)

        self._photo_choose_btn = QPushButton('Вибрати фото…')
        self._photo_choose_btn.clicked.connect(self._on_choose_photo)

        self._photo_remove_btn = QPushButton('Видалити фото')
        self._photo_remove_btn.setEnabled(False)
        self._photo_remove_btn.clicked.connect(self._on_remove_photo)

        self._photo_label = QLabel('(немає фото)')
        self._photo_label.setFixedSize(50, 50)
        self._photo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._photo_label.setStyleSheet(
            'border: 1px solid #ccc; border-radius: 4px; background: #f5f5f5;'
        )

        photo_row.addWidget(self._photo_choose_btn)
        photo_row.addWidget(self._photo_remove_btn)
        photo_row.addStretch()
        photo_row.addWidget(self._photo_label)
        form.addRow('Фото:', photo_row)

        self._frame_enabled_cb = QCheckBox('Увімкнути рамку')
        form.addRow('', self._frame_enabled_cb)

        self._frame_color_btn = QPushButton('#FF0000')
        self._frame_color_btn.setFixedWidth(90)
        self._frame_color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._frame_color_btn.clicked.connect(self._on_pick_frame_color)
        self._frame_color = '#FF0000'
        self._refresh_frame_color_btn()
        form.addRow('Колір рамки:', self._frame_color_btn)

        self._frame_width_spin = QSpinBox()
        self._frame_width_spin.setRange(1, 8)
        self._frame_width_spin.setValue(3)
        form.addRow('Товщина рамки:', self._frame_width_spin)

        root_layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText('OK')
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('Скасувати')
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self._ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        root_layout.addWidget(buttons)

        self._validate()

    def _populate_from_node(self, node: Node) -> None:
        for i in range(self._type_combo.count()):
            if self._type_combo.itemData(i) == node.type:
                self._type_combo.setCurrentIndex(i)
                break
        self._title_edit.setText(node.title)
        self._note_edit.setPlainText(node.note)
        self._date_edit.setText(node.date)
        self._color = node.color
        self._custom_color = True
        self._refresh_color_button()
        if node.photo_base64:
            self._photo_b64 = node.photo_base64
            self._refresh_photo_label()
        self._frame_enabled_cb.setChecked(getattr(node, 'frame_enabled', False))
        self._frame_color = getattr(node, 'frame_color', '#FF0000')
        self._frame_width_spin.setValue(getattr(node, 'frame_width', 3))
        self._refresh_frame_color_btn()

    def _on_type_changed(self, _index: int) -> None:
        if not self._custom_color:
            key = self._type_combo.currentData()
            self._color = NODE_DEFAULT_COLORS.get(key, '#4A90D9')
            self._refresh_color_button()

    def _on_pick_color(self) -> None:
        current = QColor(self._color)
        chosen = QColorDialog.getColor(current, self, 'Виберіть колір вузла')
        if chosen.isValid():
            self._color = chosen.name()
            self._custom_color = True
            self._refresh_color_button()

    def _on_choose_photo(self) -> None:
        filepath, _ = QFileDialog.getOpenFileName(
            self, 'Вибрати фото', '',
            'Зображення (*.jpg *.jpeg *.png *.bmp *.gif)',
        )
        if not filepath:
            return
        try:
            with open(filepath, 'rb') as fh:
                raw = fh.read()
            self._photo_b64 = base64.b64encode(raw).decode('utf-8')
            self._refresh_photo_label()
        except OSError:
            QMessageBox.warning(self, 'Помилка', 'Не вдалося завантажити зображення.')

    def _on_remove_photo(self) -> None:
        self._photo_b64 = ''
        self._refresh_photo_label()

    def _validate(self) -> None:
        has_title = bool(self._title_edit.text().strip())
        self._ok_btn.setEnabled(has_title)

    def _refresh_color_button(self) -> None:
        luminance = QColor(self._color).lightnessF()
        text_color = '#000000' if luminance > 0.5 else '#ffffff'
        self._color_btn.setStyleSheet(
            f'background-color: {self._color}; color: {text_color}; '
            f'border: 1px solid #888; border-radius: 4px;'
        )
        self._color_btn.setText(self._color)

    def _refresh_frame_color_btn(self) -> None:
        c = QColor(self._frame_color)
        lum = (c.red() * 299 + c.green() * 587 + c.blue() * 114) / 1000
        txt = '#ffffff' if lum < 128 else '#000000'
        self._frame_color_btn.setStyleSheet(
            f'background-color:{self._frame_color}; color:{txt}; border:1px solid #888;'
        )
        self._frame_color_btn.setText(self._frame_color)

    def _on_pick_frame_color(self) -> None:
        c = QColorDialog.getColor(QColor(self._frame_color), self, 'Колір рамки')
        if c.isValid():
            self._frame_color = c.name()
            self._refresh_frame_color_btn()

    def _refresh_photo_label(self) -> None:
        if self._photo_b64:
            try:
                raw = base64.b64decode(self._photo_b64)
                img = QImage()
                if img.loadFromData(raw) and not img.isNull():
                    pix = QPixmap.fromImage(img).scaled(
                        50, 50,
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation,
                    )
                    self._photo_label.setPixmap(pix)
                    self._photo_label.setText('')
                else:
                    self._photo_label.setText('(помилка)')
            except Exception:
                self._photo_label.setText('(помилка)')
            self._photo_remove_btn.setEnabled(True)
        else:
            self._photo_label.clear()
            self._photo_label.setText('(немає фото)')
            self._photo_remove_btn.setEnabled(False)

    def get_node_data(self) -> dict:
        title = self._title_edit.text().strip()
        if not title:
            return {}
        return {
            'type': self._type_combo.currentData(),
            'title': title,
            'note': self._note_edit.toPlainText().strip(),
            'date': self._date_edit.text().strip(),
            'color': self._color,
            'photo_base64': self._photo_b64,
            'frame_enabled': self._frame_enabled_cb.isChecked(),
            'frame_color': self._frame_color,
            'frame_width': self._frame_width_spin.value(),
        }


class LinkDialog(QDialog):
    """Діалог для створення нового або редагування існуючого зв'язку."""

    def __init__(self, parent=None, link: Link = None) -> None:
        super().__init__(parent)
        self._link = link
        self._link_color: str = '#555555'
        self.setWindowTitle("Редагувати зв'язок" if link else "Новий зв'язок")
        self.setMinimumWidth(380)
        self._build_ui()
        if link:
            self._populate_from_link(link)

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setSpacing(10)
        root_layout.setContentsMargins(12, 12, 12, 12)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(8)

        self._label_edit = QLineEdit()
        self._label_edit.setPlaceholderText("Підпис лінії (необов'язково)")
        form.addRow('Підпис:', self._label_edit)

        self._line_type_combo = QComboBox()
        for key, label in LINE_TYPE_LABELS.items():
            self._line_type_combo.addItem(label, userData=key)
        form.addRow('Тип лінії:', self._line_type_combo)

        self._direction_combo = QComboBox()
        for key, label in DIRECTION_LABELS.items():
            self._direction_combo.addItem(label, userData=key)
        form.addRow('Напрямок:', self._direction_combo)

        self._strength_combo = QComboBox()
        for key, label in LINK_STRENGTH_LABELS.items():
            self._strength_combo.addItem(label, userData=key)
        form.addRow('Надійність:', self._strength_combo)

        self._link_color_btn = QPushButton()
        self._link_color_btn.setFixedWidth(100)
        self._link_color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._link_color_btn.setToolTip('Клік — вибрати колір лінії')
        self._link_color_btn.clicked.connect(self._on_pick_link_color)
        self._refresh_link_color_btn()
        form.addRow('Колір лінії:', self._link_color_btn)

        self._link_width_spin = QSpinBox()
        self._link_width_spin.setRange(1, 5)
        self._link_width_spin.setValue(2)
        form.addRow('Товщина:', self._link_width_spin)

        self._note_edit = QTextEdit()
        self._note_edit.setPlaceholderText('Довільна примітка…')
        self._note_edit.setMaximumHeight(72)
        form.addRow('Примітка:', self._note_edit)

        root_layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText('OK')
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('Скасувати')
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root_layout.addWidget(buttons)

    def _refresh_link_color_btn(self) -> None:
        c = QColor(self._link_color)
        lum = (c.red() * 299 + c.green() * 587 + c.blue() * 114) / 1000
        text_color = '#ffffff' if lum < 128 else '#000000'
        self._link_color_btn.setStyleSheet(
            f'background-color:{self._link_color}; color:{text_color}; border:1px solid #888;'
        )
        self._link_color_btn.setText(self._link_color)

    def _on_pick_link_color(self) -> None:
        c = QColorDialog.getColor(QColor(self._link_color), self, 'Колір лінії')
        if c.isValid():
            self._link_color = c.name()
            self._refresh_link_color_btn()

    def _populate_from_link(self, link: Link) -> None:
        self._label_edit.setText(link.label)
        for i in range(self._line_type_combo.count()):
            if self._line_type_combo.itemData(i) == link.line_type:
                self._line_type_combo.setCurrentIndex(i)
                break
        for i in range(self._direction_combo.count()):
            if self._direction_combo.itemData(i) == link.direction:
                self._direction_combo.setCurrentIndex(i)
                break
        self._link_color = getattr(link, 'color', '#555555')
        self._refresh_link_color_btn()
        self._link_width_spin.setValue(getattr(link, 'width', 2))
        self._note_edit.setPlainText(link.note)
        strength = getattr(link, 'strength', 'Confirmed')
        for i in range(self._strength_combo.count()):
            if self._strength_combo.itemData(i) == strength:
                self._strength_combo.setCurrentIndex(i)
                break

    def get_link_data(self) -> dict:
        return {
            'label': self._label_edit.text().strip(),
            'line_type': self._line_type_combo.currentData(),
            'direction': self._direction_combo.currentData(),
            'strength': self._strength_combo.currentData(),
            'color': self._link_color,
            'width': self._link_width_spin.value(),
            'note': self._note_edit.toPlainText().strip(),
        }


class ImportWizard(QDialog):
    """Wizard для імпорту nodes.csv + links.csv з маппінгом колонок і превью."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle('Імпорт CSV — майстер')
        self.setMinimumSize(680, 540)
        self.resize(740, 580)

        self._nodes_path: str = ''
        self._delimiter: str = ','
        self._node_columns: list = []
        self._link_columns: list = []
        self._node_map: dict = {}
        self._link_map: dict = {}
        self._auto_layout_cb = QCheckBox('Авто-розміщення після імпорту')

        self._stack = QStackedWidget()
        self._stack.addWidget(self._build_page_file())
        self._stack.addWidget(self._build_page_mapping())
        self._stack.addWidget(self._build_page_preview())

        self._step_label = QLabel()
        self._step_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._btn_back = QPushButton('← Назад')
        self._btn_next = QPushButton('Далі →')
        self._btn_import = QPushButton('Імпортувати')
        btn_cancel = QPushButton('Скасувати')
        self._btn_back.clicked.connect(self._go_back)
        self._btn_next.clicked.connect(self._go_next)
        self._btn_import.clicked.connect(self.accept)
        btn_cancel.clicked.connect(self.reject)

        nav = QHBoxLayout()
        nav.addStretch()
        nav.addWidget(btn_cancel)
        nav.addWidget(self._btn_back)
        nav.addWidget(self._btn_next)
        nav.addWidget(self._btn_import)

        root = QVBoxLayout(self)
        root.addWidget(self._step_label)
        root.addWidget(self._stack, 1)
        root.addLayout(nav)
        self._update_nav()

    def _build_page_file(self) -> QWidget:
        w = QWidget()
        fl = QFormLayout(w)
        fl.setSpacing(12)

        row = QHBoxLayout()
        self._nodes_edit = QLineEdit()
        self._nodes_edit.setPlaceholderText('Виберіть nodes.csv…')
        self._nodes_edit.textChanged.connect(self._on_nodes_path_changed)
        btn = QPushButton('Огляд…')
        btn.clicked.connect(self._browse_nodes)
        row.addWidget(self._nodes_edit, 1)
        row.addWidget(btn)
        fl.addRow('Файл вузлів (nodes.csv):', row)

        self._links_status = QLabel('<i>links.csv буде знайдено автоматично</i>')
        fl.addRow("Файл зв'язків:", self._links_status)

        self._delim_combo = QComboBox()
        self._delim_combo.addItems(['Кома (,)', 'Крапка з комою (;)', 'Табуляція (\\t)'])
        self._delim_combo.currentIndexChanged.connect(self._on_delimiter_changed)
        fl.addRow('Роздільник:', self._delim_combo)

        hint = QLabel(
            "Обов'язкові стовпці nodes.csv: <b>id, title</b><br>"
            "Обов'язкові стовпці links.csv: <b>source_id, target_id</b>"
        )
        hint.setWordWrap(True)
        fl.addRow(hint)
        return w

    def _build_page_mapping(self) -> QWidget:
        inner = QWidget()
        vl = QVBoxLayout(inner)

        vl.addWidget(QLabel('<b>Маппінг стовпців вузлів (nodes.csv)</b>'))
        nf = QFormLayout()
        for field, label in [
            ('id', 'Ідентифікатор *'), ('title', 'Назва *'),
            ('type', 'Тип вузла'), ('note', 'Примітка'),
            ('date', 'Дата'), ('color', 'Колір (#hex)'),
            ('x', 'X координата'), ('y', 'Y координата'),
        ]:
            cb = QComboBox()
            self._node_map[field] = cb
            nf.addRow(label + ':', cb)
        vl.addLayout(nf)

        vl.addSpacing(12)
        vl.addWidget(QLabel("<b>Маппінг стовпців зв'язків (links.csv)</b>"))
        lf = QFormLayout()
        for field, label in [
            ('source_id', 'ID джерела *'), ('target_id', 'ID цілі *'),
            ('label', 'Підпис'), ('direction', 'Напрямок'),
            ('strength', 'Міцність (Confirmed/Unconfirmed/Tentative)'),
            ('date_time', 'Дата/час'), ('source_reference', 'Джерело'),
            ('weighting_value', 'Вага'), ('note', 'Примітка'),
        ]:
            cb = QComboBox()
            self._link_map[field] = cb
            lf.addRow(label + ':', cb)
        vl.addLayout(lf)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(inner)
        page = QWidget()
        pl = QVBoxLayout(page)
        pl.addWidget(scroll)
        return page

    def _build_page_preview(self) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.addWidget(QLabel('<b>Попередній перегляд nodes.csv (перші 5 рядків)</b>'))
        self._preview_table = QTableWidget()
        self._preview_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        vl.addWidget(self._preview_table, 1)
        vl.addWidget(QLabel('<b>Статус валідації:</b>'))
        self._status_label = QLabel('—')
        self._status_label.setWordWrap(True)
        vl.addWidget(self._status_label)
        vl.addWidget(self._auto_layout_cb)
        return w

    def _go_next(self) -> None:
        page = self._stack.currentIndex()
        if page == 0:
            if not self._nodes_path:
                QMessageBox.warning(self, 'Помилка', 'Виберіть файл вузлів.')
                return
            self._update_mapping_combos()
        elif page == 1:
            self._refresh_preview()
        self._stack.setCurrentIndex(page + 1)
        self._update_nav()

    def _go_back(self) -> None:
        self._stack.setCurrentIndex(self._stack.currentIndex() - 1)
        self._update_nav()

    def _update_nav(self) -> None:
        idx = self._stack.currentIndex()
        self._btn_back.setEnabled(idx > 0)
        self._btn_next.setVisible(idx < 2)
        self._btn_import.setVisible(idx == 2)
        self._step_label.setText(f'Крок {idx + 1} з 3')

    def _browse_nodes(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, 'Відкрити nodes.csv', '', 'CSV файли (*.csv *.tsv *.txt)'
        )
        if path:
            self._nodes_edit.setText(path)

    def _on_nodes_path_changed(self, text: str) -> None:
        self._nodes_path = text
        lp = Path(text).parent / 'links.csv'
        if lp.is_file():
            self._links_status.setText(f'<i>✓ Знайдено: {lp.name}</i>')
        else:
            self._links_status.setText('<i>links.csv не знайдено — тільки вузли</i>')

    def _on_delimiter_changed(self, idx: int) -> None:
        self._delimiter = [',', ';', '\t'][idx]

    def _read_headers(self, path: str) -> list:
        try:
            with open(path, newline='', encoding='utf-8-sig') as fh:
                r = csv.DictReader(fh, delimiter=self._delimiter)
                return list(r.fieldnames or [])
        except Exception:
            return []

    def _update_mapping_combos(self) -> None:
        NONE = '(не використовувати)'
        nc = self._read_headers(self._nodes_path)
        self._node_columns = nc
        lp = str(Path(self._nodes_path).parent / 'links.csv')
        lc = self._read_headers(lp)
        self._link_columns = lc

        def fill(combos: dict, cols: list, required: set) -> None:
            for field, cb in combos.items():
                cb.clear()
                if field not in required:
                    cb.addItem(NONE)
                for col in cols:
                    cb.addItem(col)
                match = next((c for c in cols if c.lower() == field.lower()), None)
                if match:
                    cb.setCurrentText(match)

        fill(self._node_map, nc, {'id', 'title'})
        fill(self._link_map, lc, {'source_id', 'target_id'})

    def _refresh_preview(self) -> None:
        NONE = '(не використовувати)'
        try:
            rows_data: list = []
            headers: list = []
            with open(self._nodes_path, newline='', encoding='utf-8-sig') as fh:
                reader = csv.DictReader(fh, delimiter=self._delimiter)
                headers = list(reader.fieldnames or [])
                for i, row in enumerate(reader):
                    if i >= 5:
                        break
                    rows_data.append([row.get(h, '') for h in headers])

            self._preview_table.setColumnCount(len(headers))
            self._preview_table.setRowCount(len(rows_data))
            self._preview_table.setHorizontalHeaderLabels(headers)
            for r, row in enumerate(rows_data):
                for c, val in enumerate(row):
                    self._preview_table.setItem(r, c, QTableWidgetItem(val))
            self._preview_table.resizeColumnsToContents()

            issues: list = []
            id_c = self._node_map['id'].currentText()
            ti_c = self._node_map['title'].currentText()
            if not id_c or id_c == NONE:
                issues.append('⚠ Не вибрано id для вузлів')
            if not ti_c or ti_c == NONE:
                issues.append('⚠ Не вибрано title для вузлів')
            if self._link_columns:
                sc = self._link_map['source_id'].currentText()
                tc = self._link_map['target_id'].currentText()
                if not sc or sc == NONE:
                    issues.append("⚠ Не вибрано source_id для зв'язків")
                if not tc or tc == NONE:
                    issues.append("⚠ Не вибрано target_id для зв'язків")

            if issues:
                self._status_label.setText('\n'.join(issues))
                self._status_label.setStyleSheet('color: orange;')
            else:
                n = len(rows_data)
                self._status_label.setText(f'✓ Готово — показано {n} рядків')
                self._status_label.setStyleSheet('color: green;')
        except Exception as exc:
            self._status_label.setText(f'Помилка: {exc}')
            self._status_label.setStyleSheet('color: red;')

    def get_mapping(self) -> dict:
        NONE = '(не використовувати)'

        def clean(t: str) -> Optional[str]:
            return t if t and t != NONE else None

        return {
            'nodes_path': self._nodes_path,
            'delimiter': self._delimiter,
            'auto_layout': self._auto_layout_cb.isChecked(),
            'node_map': {f: clean(cb.currentText()) for f, cb in self._node_map.items()},
            'link_map': {f: clean(cb.currentText()) for f, cb in self._link_map.items()},
        }
