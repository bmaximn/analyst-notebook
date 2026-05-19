import sys, os, json, csv, uuid, base64, copy
from datetime import datetime
from pathlib import Path
from typing import Optional
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene, QGraphicsObject,
    QGraphicsItem, QDialog, QDialogButtonBox, QWidget, QDockWidget, QToolBar,
    QStatusBar, QMenuBar, QMenu, QFileDialog, QMessageBox, QColorDialog, QLabel,
    QPushButton, QLineEdit, QTextEdit, QComboBox, QCheckBox, QFormLayout,
    QVBoxLayout, QHBoxLayout, QScrollArea, QSizePolicy, QStyle, QStyleFactory,
    QFrame, QSplitter, QAbstractScrollArea, QStackedWidget, QInputDialog,
    QGraphicsLineItem, QGraphicsEllipseItem, QGraphicsRectItem,
    QGraphicsSimpleTextItem, QSpinBox, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import (
    Qt, QRectF, QPointF, QSizeF, QTimer, QObject, pyqtSignal, QLineF, QSize
)
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QPixmap, QImage, QFont, QFontMetrics,
    QAction, QActionGroup, QKeySequence, QTransform, QPainterPath,
    QPainterPathStroker, QPolygonF, QCursor, QPageSize, QPageLayout,
    QUndoStack, QUndoCommand, QPdfWriter
)
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog, QPrintPreviewDialog

# ---------------------------------------------------------------------------
# Константи програми
# ---------------------------------------------------------------------------

NODE_TYPES = ['Person', 'Organization', 'Phone', 'Motor Vehicle', 'Document', 'Event', 'Location', 'Bank Account']

NODE_TYPE_LABELS = {
    'Person': 'Особа',
    'Organization': 'Організація',
    'Phone': 'Телефон',
    'Motor Vehicle': 'Транспорт',
    'Document': 'Документ',
    'Event': 'Подія',
    'Location': 'Локація',
    'Bank Account': 'Банківський рахунок',
}

NODE_DEFAULT_COLORS = {
    'Person': '#4A90D9',
    'Organization': '#7B68EE',
    'Phone': '#50C878',
    'Motor Vehicle': '#FF8C00',
    'Document': '#708090',
    'Event': '#DC143C',
    'Location': '#20B2AA',
    'Bank Account': '#2E8B57',
}

NODE_ICONS = {
    'Person': '👤',
    'Organization': '🏢',
    'Phone': '☎',
    'Motor Vehicle': '🚗',
    'Document': '📄',
    'Event': '◆',
    'Location': '📍',
    'Bank Account': '🏦',
}

LINE_TYPE_LABELS = {
    'solid_arrow': 'Суцільна зі стрілкою',
    'dashed': 'Пунктирна',
    'double': 'Подвійна',
    'bidirectional': 'Двостороння стрілка',
}

DIRECTION_LABELS = {
    'none': 'Без стрілки',
    'source_to_target': 'Від першого до другого',
    'target_to_source': 'Від другого до першого',
    'bidirectional': 'Двосторонній',
}

LINK_STRENGTH_LABELS = {
    'Confirmed': 'Підтверджений',
    'Unconfirmed': 'Непідтверджений',
    'Tentative': 'Попередній',
}

SCHEMA_VERSION = 2
AUTOSAVE_INTERVAL_MS = 5 * 60 * 1000
AUTOSAVE_PATH = str(Path.home() / '.analyst_notebook_autosave.json')
NODE_W, NODE_H = 130, 90

# ---------------------------------------------------------------------------
# Модель даних: вузол (Node)
# ---------------------------------------------------------------------------

class Node:
    """Вузол схеми зв'язків — зберігає всі поля одного об'єкта."""

    def __init__(
        self,
        type: str = 'Person',
        title: str = '',
        note: str = '',
        date: str = '',
        x: float = 0.0,
        y: float = 0.0,
        color: Optional[str] = None,
        photo_base64: str = '',
        node_uuid: Optional[str] = None,
        frame_enabled: bool = False,
        frame_color: str = '#FF0000',
        frame_width: int = 3,
    ) -> None:
        self.uuid: str = node_uuid if node_uuid else str(uuid.uuid4())
        self.type: str = type
        self.title: str = title
        self.note: str = note
        self.date: str = date
        self.x: float = float(x)
        self.y: float = float(y)
        self.color: str = color if color else NODE_DEFAULT_COLORS.get(type, '#4A90D9')
        self.photo_base64: str = photo_base64
        self.frame_enabled: bool = frame_enabled
        self.frame_color: str = frame_color
        self.frame_width: int = frame_width
        now = datetime.now().isoformat()
        self.created_at: str = now
        self.updated_at: str = now

    # ------------------------------------------------------------------
    # Серіалізація
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Повертає словник з усіма полями вузла."""
        return {
            'uuid': self.uuid,
            'type': self.type,
            'title': self.title,
            'note': self.note,
            'date': self.date,
            'x': self.x,
            'y': self.y,
            'color': self.color,
            'photo_base64': self.photo_base64,
            'frame_enabled': self.frame_enabled,
            'frame_color': self.frame_color,
            'frame_width': self.frame_width,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'Node':
        """Відновлює вузол зі словника; відсутні поля замінює значеннями за замовчуванням."""
        # v1 migration: Vehicle → Motor Vehicle
        node_type = d.get('type', 'Person')
        if node_type == 'Vehicle':
            node_type = 'Motor Vehicle'
        node = cls(
            type=node_type,
            title=d.get('title', ''),
            note=d.get('note', ''),
            date=d.get('date', ''),
            x=float(d.get('x', 0.0)),
            y=float(d.get('y', 0.0)),
            color=d.get('color', None),
            photo_base64=d.get('photo_base64', ''),
            node_uuid=d.get('uuid', None),
            frame_enabled=bool(d.get('frame_enabled', False)),
            frame_color=d.get('frame_color', '#FF0000'),
            frame_width=int(d.get('frame_width', 3)),
        )
        if 'created_at' in d:
            node.created_at = d['created_at']
        if 'updated_at' in d:
            node.updated_at = d['updated_at']
        return node

    def touch(self) -> None:
        """Оновлює updated_at до поточного моменту."""
        self.updated_at = datetime.now().isoformat()


# ---------------------------------------------------------------------------
# Модель даних: зв'язок (Link)
# ---------------------------------------------------------------------------

class Link:
    """Зв'язок між двома вузлами схеми."""

    def __init__(
        self,
        source_uuid: str,
        target_uuid: str,
        label: str = '',
        line_type: str = 'solid_arrow',
        direction: str = 'source_to_target',
        note: str = '',
        link_uuid: Optional[str] = None,
        color: str = '#555555',
        width: int = 2,
        strength: str = 'Confirmed',
        multiplicity: str = '',
        date_time: str = '',
        start_date_time: str = '',
        end_date_time: str = '',
        weighting_value: float = 0.0,
        source_reference: str = '',
    ) -> None:
        self.uuid: str = link_uuid if link_uuid else str(uuid.uuid4())
        self.source_uuid: str = source_uuid
        self.target_uuid: str = target_uuid
        self.label: str = label
        self.line_type: str = line_type
        self.direction: str = direction
        self.note: str = note
        self.color: str = color
        self.width: int = width
        self.strength: str = strength
        self.multiplicity: str = multiplicity
        self.date_time: str = date_time
        self.start_date_time: str = start_date_time
        self.end_date_time: str = end_date_time
        self.weighting_value: float = weighting_value
        self.source_reference: str = source_reference
        now = datetime.now().isoformat()
        self.created_at: str = now
        self.updated_at: str = now

    # ------------------------------------------------------------------
    # Серіалізація
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Повертає словник з усіма полями зв'язку."""
        return {
            'uuid': self.uuid,
            'source_uuid': self.source_uuid,
            'target_uuid': self.target_uuid,
            'label': self.label,
            'line_type': self.line_type,
            'direction': self.direction,
            'note': self.note,
            'color': self.color,
            'width': self.width,
            'strength': self.strength,
            'multiplicity': self.multiplicity,
            'date_time': self.date_time,
            'start_date_time': self.start_date_time,
            'end_date_time': self.end_date_time,
            'weighting_value': self.weighting_value,
            'source_reference': self.source_reference,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
        }

    @classmethod
    def from_dict(cls, d: dict) -> 'Link':
        """Відновлює зв'язок зі словника; відсутні поля замінює значеннями за замовчуванням."""
        # v1 migration: line_type mapped to strength
        raw_line_type = d.get('line_type', 'solid_arrow')
        strength = d.get('strength', 'Confirmed')
        if 'strength' not in d:
            # derive strength from legacy line_type for v1 files
            if raw_line_type == 'dashed':
                strength = 'Unconfirmed'
            elif raw_line_type in ('dotted', 'double'):
                strength = 'Tentative'
        link = cls(
            source_uuid=d.get('source_uuid', ''),
            target_uuid=d.get('target_uuid', ''),
            label=d.get('label', ''),
            line_type=raw_line_type,
            direction=d.get('direction', 'source_to_target'),
            note=d.get('note', ''),
            link_uuid=d.get('uuid', None),
            color=d.get('color', '#555555'),
            width=int(d.get('width', 2)),
            strength=strength,
            multiplicity=d.get('multiplicity', ''),
            date_time=d.get('date_time', ''),
            start_date_time=d.get('start_date_time', ''),
            end_date_time=d.get('end_date_time', ''),
            weighting_value=float(d.get('weighting_value', 0.0)),
            source_reference=d.get('source_reference', ''),
        )
        if 'created_at' in d:
            link.created_at = d['created_at']
        if 'updated_at' in d:
            link.updated_at = d['updated_at']
        return link

    def touch(self) -> None:
        """Оновлює updated_at до поточного моменту."""
        self.updated_at = datetime.now().isoformat()


# ---------------------------------------------------------------------------
# Команди скасування/повтору (QUndoCommand)
# ---------------------------------------------------------------------------

class AddNodeCommand(QUndoCommand):
    """Команда: додати один вузол на полотно."""

    def __init__(self, canvas, node: Node, text: str = 'Додати вузол') -> None:
        super().__init__(text)
        self.canvas = canvas
        self.node = node

    def redo(self) -> None:
        self.canvas.add_node(self.node)
        self.canvas.mark_modified()

    def undo(self) -> None:
        self.canvas.remove_node(self.node.uuid)
        self.canvas.mark_modified()


class DeleteNodesCommand(QUndoCommand):
    """Команда: видалити набір вузлів разом із пов'язаними зв'язками."""

    def __init__(
        self,
        canvas,
        nodes: list[Node],
        links: list[Link],
        text: str = 'Видалити елементи',
    ) -> None:
        super().__init__(text)
        self.canvas = canvas
        # Зберігаємо глибокі копії, щоб операція undo завжди відновлювала
        # точний стан незалежно від подальших змін у словниках canvas
        self.nodes: list[Node] = [copy.deepcopy(n) for n in nodes]
        self.links: list[Link] = [copy.deepcopy(lk) for lk in links]

    def redo(self) -> None:
        # Спочатку видаляємо зв'язки, щоб не залишати «сиріт»
        for lk in self.links:
            self.canvas.remove_link(lk.uuid)
        for node in self.nodes:
            self.canvas.remove_node(node.uuid)
        self.canvas.mark_modified()

    def undo(self) -> None:
        # Відновлюємо вузли, потім зв'язки
        for node in self.nodes:
            self.canvas.add_node(node)
        for lk in self.links:
            self.canvas.add_link(lk)
        self.canvas.mark_modified()


class EditNodeCommand(QUndoCommand):
    """Команда: редагувати поля існуючого вузла."""

    def __init__(
        self,
        canvas,
        node_uuid: str,
        old_data: dict,
        new_data: dict,
        text: str = 'Редагувати вузол',
    ) -> None:
        super().__init__(text)
        self.canvas = canvas
        self.node_uuid = node_uuid
        self.old_data = old_data
        self.new_data = new_data

    def _apply(self, data: dict) -> None:
        node = self.canvas.nodes.get(self.node_uuid)
        if node is None:
            return
        node.__dict__.update(data)
        node.touch()
        item = self.canvas.get_node_item(self.node_uuid)
        if item is not None:
            item.update_from_node()
        self.canvas.mark_modified()

    def redo(self) -> None:
        self._apply(self.new_data)

    def undo(self) -> None:
        self._apply(self.old_data)


class ColorNodeCommand(QUndoCommand):
    """Команда: змінити колір вузла."""

    def __init__(
        self,
        canvas,
        node_uuid: str,
        old_color: str,
        new_color: str,
        text: str = 'Змінити колір',
    ) -> None:
        super().__init__(text)
        self.canvas = canvas
        self.node_uuid = node_uuid
        self.old_color = old_color
        self.new_color = new_color

    def _apply(self, color: str) -> None:
        node = self.canvas.nodes.get(self.node_uuid)
        if node is None:
            return
        node.color = color
        node.touch()
        item = self.canvas.get_node_item(self.node_uuid)
        if item is not None:
            item.update_from_node()
        self.canvas.mark_modified()

    def redo(self) -> None:
        self._apply(self.new_color)

    def undo(self) -> None:
        self._apply(self.old_color)


class DuplicateNodeCommand(QUndoCommand):
    """Команда: дублювати вузол (створює новий вузол із тими самими даними)."""

    def __init__(
        self,
        canvas,
        new_node: Node,
        text: str = 'Дублювати вузол',
    ) -> None:
        super().__init__(text)
        self.canvas = canvas
        self.new_node = new_node

    def redo(self) -> None:
        self.canvas.add_node(self.new_node)
        self.canvas.mark_modified()

    def undo(self) -> None:
        self.canvas.remove_node(self.new_node.uuid)
        self.canvas.mark_modified()


class AddLinkCommand(QUndoCommand):
    """Команда: додати зв'язок між двома вузлами."""

    def __init__(
        self,
        canvas,
        link: Link,
        text: str = "Додати зв'язок",
    ) -> None:
        super().__init__(text)
        self.canvas = canvas
        self.link = link

    def redo(self) -> None:
        self.canvas.add_link(self.link)
        self.canvas.mark_modified()

    def undo(self) -> None:
        self.canvas.remove_link(self.link.uuid)
        self.canvas.mark_modified()


class DeleteLinksCommand(QUndoCommand):
    """Команда: видалити набір зв'язків."""

    def __init__(
        self,
        canvas,
        links: list[Link],
        text: str = "Видалити зв'язки",
    ) -> None:
        super().__init__(text)
        self.canvas = canvas
        self.links: list[Link] = [copy.deepcopy(lk) for lk in links]

    def redo(self) -> None:
        for lk in self.links:
            self.canvas.remove_link(lk.uuid)
        self.canvas.mark_modified()

    def undo(self) -> None:
        for lk in self.links:
            self.canvas.add_link(lk)
        self.canvas.mark_modified()


class EditLinkCommand(QUndoCommand):
    """Команда: редагувати поля існуючого зв'язку."""

    def __init__(
        self,
        canvas,
        link_uuid: str,
        old_data: dict,
        new_data: dict,
        text: str = "Редагувати зв'язок",
    ) -> None:
        super().__init__(text)
        self.canvas = canvas
        self.link_uuid = link_uuid
        self.old_data = old_data
        self.new_data = new_data

    def _apply(self, data: dict) -> None:
        link = self.canvas.links.get(self.link_uuid)
        if link is None:
            return
        link.__dict__.update(data)
        link.touch()
        item = self.canvas.get_link_item(self.link_uuid)
        if item is not None:
            item.update_from_link()
        self.canvas.mark_modified()

    def redo(self) -> None:
        self._apply(self.new_data)

    def undo(self) -> None:
        self._apply(self.old_data)


class AddShapeCommand(QUndoCommand):
    """Команда: додати геометричну фігуру на сцену."""

    def __init__(self, canvas: 'DiagramCanvas', item: 'QGraphicsItem') -> None:
        super().__init__('Додати фігуру')
        self._canvas = canvas
        self._item = item

    def redo(self) -> None:
        self._canvas._scene.addItem(self._item)
        if self._item not in self._canvas._shape_items:
            self._canvas._shape_items.append(self._item)

    def undo(self) -> None:
        self._canvas._scene.removeItem(self._item)
        if self._item in self._canvas._shape_items:
            self._canvas._shape_items.remove(self._item)


class DeleteShapeCommand(QUndoCommand):
    """Команда: видалити геометричні фігури зі сцени."""

    def __init__(self, canvas: 'DiagramCanvas', items: list) -> None:
        super().__init__('Видалити фігури')
        self._canvas = canvas
        self._items = list(items)

    def redo(self) -> None:
        for item in self._items:
            self._canvas._scene.removeItem(item)
            if item in self._canvas._shape_items:
                self._canvas._shape_items.remove(item)

    def undo(self) -> None:
        for item in self._items:
            self._canvas._scene.addItem(item)
            if item not in self._canvas._shape_items:
                self._canvas._shape_items.append(item)


# =============================================================================
# ЧАСТИНА 2 — Графічні елементи: NodeItem та LinkItem
# =============================================================================


class NodeItem(QGraphicsObject):
    """Графічний елемент вузла на сцені."""

    # Сигнали взаємодії з вузлом
    position_changed = pyqtSignal(str)           # node.uuid — позиція змінилась
    edit_requested = pyqtSignal(str)             # node.uuid — запит на редагування
    delete_requested = pyqtSignal(str)           # node.uuid — запит на видалення
    duplicate_requested = pyqtSignal(str)        # node.uuid — запит на дублювання
    color_change_requested = pyqtSignal(str, str)  # node.uuid, new_color_hex — зміна кольору

    def __init__(self, node: 'Node', parent=None):
        super().__init__(parent)
        self.node = node
        self._pixmap: Optional[QPixmap] = None

        # Завантажуємо фото, якщо є
        self._load_photo_pixmap()

        # Дозволяємо переміщення, виділення та надсилання змін геометрії
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

        # Встановлюємо початкову позицію з даних моделі
        self.setPos(node.x, node.y)

    # ------------------------------------------------------------------
    # Геометрія
    # ------------------------------------------------------------------

    def boundingRect(self) -> QRectF:
        """Повертає обмежувальний прямокутник вузла."""
        return QRectF(0, 0, NODE_W, NODE_H)

    # ------------------------------------------------------------------
    # Відображення
    # ------------------------------------------------------------------

    def paint(self, painter: QPainter, option, widget=None):
        """Малює картку вузла."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        selected = bool(option.state & QStyle.StateFlag.State_Selected)

        # --- Фон: заокруглений прямокутник ---
        rect = QRectF(0, 0, NODE_W, NODE_H)
        painter.setBrush(QBrush(QColor('#ffffff')))

        if selected:
            # Підсвічення при виборі — синя рамка 3px
            painter.setPen(QPen(QColor('#2196F3'), 3))
        else:
            # Звичайна рамка — колір вузла, 2px
            painter.setPen(QPen(QColor(self.node.color), 2))

        painter.drawRoundedRect(rect, 8, 8)

        # --- Icon Frame (кольорова рамка навколо вузла) ---
        if getattr(self.node, 'frame_enabled', False) and not selected:
            fw = getattr(self.node, 'frame_width', 3)
            fc = getattr(self.node, 'frame_color', '#FF0000')
            frame_pen = QPen(QColor(fc), fw)
            painter.setPen(frame_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(fw / 2, fw / 2, -fw / 2, -fw / 2), 8, 8)

        # --- Верхня область (висота 40px): фото або іконка-емодзі ---
        top_area_h = 40
        top_area_rect = QRectF(0, 0, NODE_W, top_area_h)

        if self._pixmap is not None and not self._pixmap.isNull():
            # Малюємо мініатюру 36×36 по центру верхньої зони
            thumb_w, thumb_h = 36, 36
            thumb_x = (NODE_W - thumb_w) / 2
            thumb_y = (top_area_h - thumb_h) / 2
            painter.drawPixmap(int(thumb_x), int(thumb_y), self._pixmap)
        else:
            # Малюємо емодзі-іконку типу вузла
            icon_font = QFont()
            icon_font.setPointSize(20)
            painter.setFont(icon_font)
            painter.setPen(QPen(QColor('#333333')))
            icon_text = NODE_ICONS.get(self.node.type, '?')
            painter.drawText(top_area_rect, Qt.AlignmentFlag.AlignCenter, icon_text)

        # --- Середня зона: заголовок вузла ---
        title_rect = QRectF(5, top_area_h, NODE_W - 10, NODE_H - top_area_h - 18)
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(9)
        painter.setFont(title_font)
        painter.setPen(QPen(QColor('#111111')))

        # Обрізаємо текст, якщо не вміщується
        fm = painter.fontMetrics()
        elided_title = fm.elidedText(
            self.node.title,
            Qt.TextElideMode.ElideRight,
            int(title_rect.width())
        )
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, elided_title)

        # --- Нижня зона (18px): підпис типу вузла ---
        type_rect = QRectF(0, NODE_H - 18, NODE_W, 18)
        type_font = QFont()
        type_font.setPointSize(8)
        painter.setFont(type_font)
        painter.setPen(QPen(QColor('#888888')))
        type_label = NODE_TYPE_LABELS.get(self.node.type, self.node.type)
        painter.drawText(type_rect, Qt.AlignmentFlag.AlignCenter, type_label)

    # ------------------------------------------------------------------
    # Реакція на зміни позиції
    # ------------------------------------------------------------------

    def itemChange(self, change, value):
        """Синхронізує позицію у моделі та надсилає сигнал при переміщенні."""
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            canvas = getattr(self, '_canvas', None)
            if canvas is not None and canvas.get_snap_to_grid():
                grid = 30
                return QPointF(round(value.x() / grid) * grid, round(value.y() / grid) * grid)
        elif change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.node.x = self.pos().x()
            self.node.y = self.pos().y()
            self.position_changed.emit(self.node.uuid)
        return super().itemChange(change, value)

    # ------------------------------------------------------------------
    # Оновлення з моделі
    # ------------------------------------------------------------------

    def update_from_node(self):
        """Перезавантажує дані з моделі та перемальовує елемент."""
        self.prepareGeometryChange()
        self._load_photo_pixmap()
        self.update()

    # ------------------------------------------------------------------
    # Контекстне меню
    # ------------------------------------------------------------------

    def contextMenuEvent(self, event):
        """Показує контекстне меню вузла."""
        menu = QMenu()

        action_edit = menu.addAction('Редагувати')
        action_duplicate = menu.addAction('Дублювати')
        menu.addSeparator()
        action_color = menu.addAction('Змінити колір')
        menu.addSeparator()
        action_show_connected = menu.addAction("Показати тільки пов'язані")
        action_show_all = menu.addAction('Показати всі')
        menu.addSeparator()
        action_delete = menu.addAction('Видалити')

        chosen = menu.exec(event.screenPos())

        if chosen == action_edit:
            self.edit_requested.emit(self.node.uuid)
        elif chosen == action_delete:
            self.delete_requested.emit(self.node.uuid)
        elif chosen == action_duplicate:
            self.duplicate_requested.emit(self.node.uuid)
        elif chosen == action_color:
            current_color = QColor(self.node.color)
            new_color = QColorDialog.getColor(current_color, None, 'Виберіть колір вузла')
            if new_color.isValid():
                self.color_change_requested.emit(self.node.uuid, new_color.name())
        elif chosen == action_show_connected:
            canvas = getattr(self, '_canvas', None)
            if canvas is not None:
                canvas.show_only_connected(self.node.uuid)
        elif chosen == action_show_all:
            canvas = getattr(self, '_canvas', None)
            if canvas is not None:
                canvas.show_all_nodes()

    # ------------------------------------------------------------------
    # Подвійний клік — відкрити редактор
    # ------------------------------------------------------------------

    def mouseDoubleClickEvent(self, event):
        """Відкриває редактор вузла при подвійному кліку."""
        self.edit_requested.emit(self.node.uuid)
        super().mouseDoubleClickEvent(event)

    # ------------------------------------------------------------------
    # Завантаження фото
    # ------------------------------------------------------------------

    def _load_photo_pixmap(self):
        """Декодує фото з base64 та масштабує до 36×36 пікселів."""
        if not self.node.photo_base64:
            self._pixmap = None
            return

        try:
            # Декодуємо base64 у байти
            raw_bytes = base64.b64decode(self.node.photo_base64)
            image = QImage()
            loaded = image.loadFromData(raw_bytes)
            if not loaded or image.isNull():
                self._pixmap = None
                return

            # Масштабуємо з дотриманням пропорцій
            pixmap = QPixmap.fromImage(image)
            self._pixmap = pixmap.scaled(
                36, 36,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        except Exception:
            # Якщо декодування не вдалось — без фото
            self._pixmap = None


# =============================================================================


class LinkItem(QGraphicsObject):
    """Графічний елемент зв'язку між двома вузлами."""

    # Сигнали взаємодії зі зв'язком
    edit_requested = pyqtSignal(str)    # link.uuid — запит на редагування
    delete_requested = pyqtSignal(str)  # link.uuid — запит на видалення

    def __init__(self, link: 'Link', source_item: NodeItem, target_item: NodeItem, parent=None):
        super().__init__(parent)
        self.link = link
        self.source_item = source_item
        self.target_item = target_item

        # Лінія у координатах сцени
        self._line = QLineF()

        # Зв'язки розташовані позаду вузлів
        self.setZValue(-1)

        # Дозволяємо виділення для взаємодії
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)

        # Обчислюємо початкове положення лінії
        self.update_position()

    # ------------------------------------------------------------------
    # Оновлення геометрії
    # ------------------------------------------------------------------

    @staticmethod
    def _intersect_node_rect(line: QLineF, node_pos: QPointF) -> QPointF:
        """Повертає точку перетину лінії з межею прямокутника вузла.
        Якщо перетину немає — повертає центр вузла."""
        rect = QRectF(node_pos.x(), node_pos.y(), NODE_W, NODE_H)
        edges = [
            QLineF(rect.topLeft(), rect.topRight()),
            QLineF(rect.topRight(), rect.bottomRight()),
            QLineF(rect.bottomRight(), rect.bottomLeft()),
            QLineF(rect.bottomLeft(), rect.topLeft()),
        ]
        intersection = QPointF()
        for edge in edges:
            result = line.intersects(edge, intersection)
            if result == QLineF.IntersectionType.BoundedIntersection:
                return QPointF(intersection)
        return QPointF(node_pos.x() + NODE_W / 2, node_pos.y() + NODE_H / 2)

    def update_position(self):
        """Перераховує лінію між межами вузлів (обрізає до прямокутника вузла)."""
        src_pos = self.source_item.pos()
        dst_pos = self.target_item.pos()
        src_center = src_pos + QPointF(NODE_W / 2, NODE_H / 2)
        dst_center = dst_pos + QPointF(NODE_W / 2, NODE_H / 2)
        center_line = QLineF(src_center, dst_center)

        if center_line.length() < 1:
            self._line = center_line
        else:
            src_pt = self._intersect_node_rect(QLineF(dst_center, src_center), src_pos)
            dst_pt = self._intersect_node_rect(QLineF(src_center, dst_center), dst_pos)
            self._line = QLineF(src_pt, dst_pt)

        self.prepareGeometryChange()
        self.update()

    def update_from_link(self):
        """Перемальовує зв'язок після зміни даних моделі."""
        self.update()

    # ------------------------------------------------------------------
    # Геометрія
    # ------------------------------------------------------------------

    def boundingRect(self) -> QRectF:
        """Повертає прямокутник, що охоплює лінію з відступом 20px."""
        pad = 20.0
        return QRectF(
            min(self._line.x1(), self._line.x2()) - pad,
            min(self._line.y1(), self._line.y2()) - pad,
            abs(self._line.dx()) + 2 * pad,
            abs(self._line.dy()) + 2 * pad,
        )

    def shape(self) -> QPainterPath:
        """Повертає розширений контур (10px) для легкого клацання на тонкій лінії."""
        path = QPainterPath()
        path.moveTo(self._line.p1())
        path.lineTo(self._line.p2())

        # Розширюємо контур до 10px за допомогою stroker
        stroker = QPainterPathStroker()
        stroker.setWidth(10)
        return stroker.createStroke(path)

    # ------------------------------------------------------------------
    # Відображення
    # ------------------------------------------------------------------

    def paint(self, painter: QPainter, option, widget=None):
        """Малює лінію зв'язку, стрілки та підпис."""
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        base_color = QColor(getattr(self.link, 'color', '#555555'))
        line_color = QColor('#2196F3') if selected else base_color
        lw = getattr(self.link, 'width', 2)

        line_type = self.link.line_type
        strength = getattr(self.link, 'strength', 'Confirmed')

        # Стиль пера визначається strength (семантика i2)
        if strength == 'Unconfirmed':
            pen_style = Qt.PenStyle.DashLine
        elif strength == 'Tentative':
            pen_style = Qt.PenStyle.DotLine
        else:
            pen_style = Qt.PenStyle.SolidLine

        pen = QPen(line_color, lw, pen_style)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)

        if line_type == 'double':
            self._draw_double_line(painter, pen)
        else:
            painter.setPen(pen)
            painter.drawLine(self._line)

        # --- Малюємо стрілки залежно від напрямку ---
        direction = self.link.direction

        # Кути для стрілок (в градусах)
        angle_to_target = self._line.angle()           # напрямок p1→p2
        angle_to_source = self._line.angle() + 180.0   # напрямок p2→p1

        if direction == 'source_to_target':
            self._draw_arrow(painter, pen, self._line.p2(), angle_to_target)
        elif direction == 'target_to_source':
            self._draw_arrow(painter, pen, self._line.p1(), angle_to_source)
        elif direction == 'bidirectional':
            self._draw_arrow(painter, pen, self._line.p2(), angle_to_target)
            self._draw_arrow(painter, pen, self._line.p1(), angle_to_source)
        # 'none' — стрілок нема

        # --- Малюємо підпис у середині лінії ---
        if self.link.label:
            self._draw_label(painter)

    def _draw_double_line(self, painter: QPainter, pen: QPen):
        """Малює дві паралельні лінії зі зміщенням 3px перпендикулярно до основної."""
        import math

        length = self._line.length()
        if length < 1:
            return

        # Одиничний перпендикулярний вектор
        dx = self._line.dx() / length
        dy = self._line.dy() / length
        perp_x = -dy
        perp_y = dx
        offset = 3.0

        painter.setPen(pen)

        # Перша лінія — зміщена на +3px
        p1a = QPointF(self._line.x1() + perp_x * offset, self._line.y1() + perp_y * offset)
        p2a = QPointF(self._line.x2() + perp_x * offset, self._line.y2() + perp_y * offset)
        painter.drawLine(p1a, p2a)

        # Друга лінія — зміщена на −3px
        p1b = QPointF(self._line.x1() - perp_x * offset, self._line.y1() - perp_y * offset)
        p2b = QPointF(self._line.x2() - perp_x * offset, self._line.y2() - perp_y * offset)
        painter.drawLine(p1b, p2b)

    def _draw_arrow(self, painter: QPainter, pen: QPen, tip: QPointF, angle_degrees: float):
        """Малює заповнений трикутник-стрілку у точці tip, що вказує у напрямку angle_degrees."""
        import math

        arrow_size = 10.0
        angle_rad = math.radians(angle_degrees)

        # Кут основи стрілки (±25°)
        wing_angle = math.radians(25)

        # Дві точки основи трикутника
        left_x = tip.x() - arrow_size * math.cos(angle_rad - wing_angle)
        left_y = tip.y() + arrow_size * math.sin(angle_rad - wing_angle)

        right_x = tip.x() - arrow_size * math.cos(angle_rad + wing_angle)
        right_y = tip.y() + arrow_size * math.sin(angle_rad + wing_angle)

        arrow_polygon = QPolygonF([
            tip,
            QPointF(left_x, left_y),
            QPointF(right_x, right_y),
        ])

        # Заповнюємо стрілку кольором лінії
        painter.setPen(QPen(pen.color(), 1))
        painter.setBrush(QBrush(pen.color()))
        painter.drawPolygon(arrow_polygon)

    def _draw_label(self, painter: QPainter):
        """Малює підпис зв'язку на середині лінії з фоном."""
        label_font = QFont()
        label_font.setPointSize(9)
        painter.setFont(label_font)

        fm = painter.fontMetrics()
        text_rect = fm.boundingRect(self.link.label)

        mid = self._line.pointAt(0.5)
        text_w = text_rect.width()
        text_h = text_rect.height()

        pad = 4
        bg_rect = QRectF(
            mid.x() - text_w / 2 - pad,
            mid.y() - text_h / 2 - pad,
            text_w + 2 * pad,
            text_h + 2 * pad,
        )

        # Білий фон з тонкою рамкою
        painter.setPen(QPen(QColor('#cccccc'), 1))
        painter.setBrush(QBrush(QColor('#ffffff')))
        painter.drawRoundedRect(bg_rect, 3, 3)

        painter.setPen(QPen(QColor('#222222')))
        painter.drawText(bg_rect, Qt.AlignmentFlag.AlignCenter, self.link.label)

    # ------------------------------------------------------------------
    # Контекстне меню
    # ------------------------------------------------------------------

    def contextMenuEvent(self, event):
        """Показує контекстне меню зв'язку."""
        menu = QMenu()
        action_edit = menu.addAction('Редагувати')
        action_delete = menu.addAction('Видалити')

        chosen = menu.exec(event.screenPos())

        if chosen == action_edit:
            self.edit_requested.emit(self.link.uuid)
        elif chosen == action_delete:
            self.delete_requested.emit(self.link.uuid)

    # ------------------------------------------------------------------
    # Подвійний клік — відкрити редактор
    # ------------------------------------------------------------------

    def mouseDoubleClickEvent(self, event):
        """Відкриває редактор зв'язку при подвійному кліку."""
        self.edit_requested.emit(self.link.uuid)
        super().mouseDoubleClickEvent(event)


# =============================================================================
# GroupItem — контейнер для групи вузлів
# =============================================================================

class GroupItem(QGraphicsRectItem):
    """Напівпрозорий прямокутний контейнер навколо групи вузлів.

    При переміщенні всі вузли-члени рухаються разом.
    """

    def __init__(self, member_items: list, label: str = '', parent=None):
        self._member_items: list = list(member_items)
        self._label: str = label

        pad = 20
        if member_items:
            xs = [it.pos().x() for it in member_items]
            ys = [it.pos().y() for it in member_items]
            x0 = min(xs) - pad
            y0 = min(ys) - pad - 22      # місце для підпису зверху
            x1 = max(it.pos().x() + NODE_W for it in member_items) + pad
            y1 = max(it.pos().y() + NODE_H for it in member_items) + pad
            rect = QRectF(x0, y0, x1 - x0, y1 - y0)
        else:
            rect = QRectF(0, 0, 200, 150)

        super().__init__(rect, parent)
        self._last_pos = self.pos()

        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)

        self.setBrush(QBrush(QColor(100, 150, 255, 35)))
        self.setPen(QPen(QColor(80, 120, 220), 2, Qt.PenStyle.DashLine))
        self.setZValue(-2)

    # ------------------------------------------------------------------

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            delta = value - self._last_pos
            self._last_pos = value
            for it in self._member_items:
                it.setPos(it.pos() + delta)
        return super().itemChange(change, value)

    def paint(self, painter, option, widget=None):
        super().paint(painter, option, widget)
        if self._label:
            f = QFont()
            f.setPointSize(9)
            f.setBold(True)
            painter.setFont(f)
            painter.setPen(QPen(QColor(60, 100, 200)))
            lbl_rect = QRectF(self.rect().x(), self.rect().y(), self.rect().width(), 20)
            painter.drawText(lbl_rect, Qt.AlignmentFlag.AlignCenter, self._label)

    def members(self) -> list:
        return list(self._member_items)


# =============================================================================
# ЧАСТИНА 3 — DiagramCanvas, збереження/завантаження JSON, імпорт CSV,
#              експорт PNG/PDF, автозбереження
# =============================================================================


class DiagramCanvas(QGraphicsView):
    """Основне полотно схеми зв'язків.

    Керує сценою, вузлами, зв'язками, режимами взаємодії
    та сполучає графічний шар з моделлю даних.
    """

    # ------------------------------------------------------------------
    # Сигнали
    # ------------------------------------------------------------------

    # Виділений вузол (або None, якщо нічого не вибрано)
    node_selected = pyqtSignal(object)
    # Виділений зв'язок (або None)
    link_selected = pyqtSignal(object)
    # Список усіх виділених об'єктів (Node і Link разом)
    selection_changed = pyqtSignal(list)
    # True/False — чи є незбережені зміни
    modified_changed = pyqtSignal(bool)
    # Запит на створення зв'язку між двома вузлами (source_uuid, target_uuid)
    link_creation_requested = pyqtSignal(str, str)
    # Запит на відкриття редактора вузла
    node_edit_requested = pyqtSignal(str)
    # Запит на відкриття редактора зв'язку
    link_edit_requested = pyqtSignal(str)
    # Коротке повідомлення для статусного рядка
    status_message = pyqtSignal(str)
    # Подвійний клік на порожньому місці сцени — для додавання нового вузла
    empty_space_double_clicked = pyqtSignal(QPointF)

    # ------------------------------------------------------------------
    # Ініціалізація
    # ------------------------------------------------------------------

    def __init__(self, undo_stack: QUndoStack, parent=None) -> None:
        super().__init__(parent)

        # --- Моделі даних ---
        self.nodes: dict[str, Node] = {}
        self.links: dict[str, Link] = {}

        # --- Графічні елементи сцени ---
        self.node_items: dict[str, NodeItem] = {}
        self.link_items: dict[str, LinkItem] = {}
        self._shape_items: list = []       # QGraphicsLineItem / EllipseItem / RectItem / TextItem
        self._group_items: list = []       # GroupItem

        # --- Стан файлу ---
        self.is_modified: bool = False
        self.current_file: Optional[str] = None

        # --- Режим взаємодії: 'select', 'link', або shape-режими ---
        self._mode: str = 'select'
        self._link_source_uuid: Optional[str] = None

        # --- Shape Tool стан ---
        self._shape_start: Optional[QPointF] = None
        self._shape_preview: Optional[QGraphicsItem] = None

        # --- Додаткові параметри ---
        self._grid_enabled: bool = True
        self._snap_to_grid: bool = False
        self._space_pressed: bool = False
        self._pan_start: Optional[QPointF] = None

        # --- Стек скасувань ---
        self.undo_stack = undo_stack

        # --- Налаштування сцени ---
        self._scene = QGraphicsScene(self)
        self._scene.setSceneRect(QRectF(-10000, -10000, 20000, 20000))
        self.setScene(self._scene)

        # --- Налаштування рендерингу ---
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.FullViewportUpdate
        )
        self.setBackgroundBrush(QBrush(QColor('white')))
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        # --- Підключення сигналу зміни виділення ---
        self._scene.selectionChanged.connect(self._on_selection_changed)

    # ------------------------------------------------------------------
    # Управління вузлами
    # ------------------------------------------------------------------

    def add_node(self, node: Node) -> 'NodeItem':
        """Додає вузол до моделі й до сцени; повертає створений NodeItem."""
        self.nodes[node.uuid] = node
        item = NodeItem(node)
        item._canvas = self
        self._scene.addItem(item)
        item.setPos(node.x, node.y)

        # Підключаємо сигнали елемента
        item.position_changed.connect(self._on_node_moved)
        item.edit_requested.connect(self.node_edit_requested)
        item.delete_requested.connect(self._on_delete_node_requested)
        item.duplicate_requested.connect(self._on_duplicate_node_requested)
        item.color_change_requested.connect(self._on_color_change_requested)

        self.node_items[node.uuid] = item
        return item

    def remove_node(self, node_uuid: str) -> None:
        """Видаляє вузол із сцени та моделі."""
        if node_uuid in self.node_items:
            self._scene.removeItem(self.node_items[node_uuid])
            del self.node_items[node_uuid]
        if node_uuid in self.nodes:
            del self.nodes[node_uuid]

    # ------------------------------------------------------------------
    # Управління зв'язками
    # ------------------------------------------------------------------

    def add_link(self, link: Link) -> 'LinkItem':
        """Додає зв'язок до моделі й до сцени; повертає створений LinkItem."""
        self.links[link.uuid] = link
        source_item = self.node_items[link.source_uuid]
        target_item = self.node_items[link.target_uuid]
        link_item = LinkItem(link, source_item, target_item)
        self._scene.addItem(link_item)

        # Підключаємо сигнали елемента
        link_item.edit_requested.connect(self.link_edit_requested)
        link_item.delete_requested.connect(self._on_delete_link_requested)

        self.link_items[link.uuid] = link_item
        return link_item

    def remove_link(self, link_uuid: str) -> None:
        """Видаляє зв'язок із сцени та моделі."""
        if link_uuid in self.link_items:
            self._scene.removeItem(self.link_items[link_uuid])
            del self.link_items[link_uuid]
        if link_uuid in self.links:
            del self.links[link_uuid]

    # ------------------------------------------------------------------
    # Пошук елементів
    # ------------------------------------------------------------------

    def get_node_item(self, node_uuid: str) -> Optional['NodeItem']:
        """Повертає NodeItem за UUID або None."""
        return self.node_items.get(node_uuid)

    def get_link_item(self, link_uuid: str) -> Optional['LinkItem']:
        """Повертає LinkItem за UUID або None."""
        return self.link_items.get(link_uuid)

    # ------------------------------------------------------------------
    # Очищення сцени
    # ------------------------------------------------------------------

    def clear_scene(self) -> None:
        """Повністю очищає сцену, моделі та стек скасувань."""
        self._scene.clear()
        self.nodes.clear()
        self.links.clear()
        self.node_items.clear()
        self.link_items.clear()
        self._shape_items.clear()
        self._group_items.clear()
        self.is_modified = False
        self.current_file = None
        self.undo_stack.clear()
        self.modified_changed.emit(False)

    # ------------------------------------------------------------------
    # Позначення змін
    # ------------------------------------------------------------------

    def mark_modified(self) -> None:
        """Позначає схему як змінену та надсилає відповідний сигнал."""
        self.is_modified = True
        self.modified_changed.emit(True)

    # ------------------------------------------------------------------
    # Управління видом
    # ------------------------------------------------------------------

    def fit_to_screen(self) -> None:
        """Масштабує вид так, щоб усі елементи поміщались на екрані."""
        if self.nodes:
            self.fitInView(
                self._scene.itemsBoundingRect().adjusted(-50, -50, 50, 50),
                Qt.AspectRatioMode.KeepAspectRatio,
            )
        else:
            self.resetTransform()

    def set_mode(self, mode: str) -> None:
        """Перемикає режим взаємодії."""
        # Скасовуємо поточне малювання фігури, якщо є
        if self._shape_preview is not None:
            self._scene.removeItem(self._shape_preview)
            self._shape_preview = None
        self._shape_start = None

        self._mode = mode
        self._link_source_uuid = None

        _shape_labels = {
            'line': 'Лінія', 'circle': 'Коло',
            'rect': 'Прямокутник', 'text': 'Текст',
        }
        if mode == 'select':
            self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            self.status_message.emit('Інструмент вибору')
        elif mode == 'link':
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.status_message.emit('Link Tool: виберіть перший вузол')
        elif mode in _shape_labels:
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            label = _shape_labels[mode]
            hint = 'клацніть щоб розмістити' if mode == 'text' else 'клацніть і тягніть'
            self.status_message.emit(f'{label}: {hint}')

    def toggle_grid(self) -> None:
        """Вмикає або вимикає відображення сітки."""
        self._grid_enabled = not self._grid_enabled
        self.viewport().update()

    def get_grid_enabled(self) -> bool:
        """Повертає поточний стан відображення сітки."""
        return self._grid_enabled

    def toggle_snap_to_grid(self) -> None:
        """Вмикає або вимикає прив'язку вузлів до сітки при переміщенні."""
        self._snap_to_grid = not self._snap_to_grid

    def get_snap_to_grid(self) -> bool:
        return self._snap_to_grid

    # ------------------------------------------------------------------
    # Авто-розміщення вузлів
    # ------------------------------------------------------------------

    def auto_layout_grid(self) -> None:
        """Розкладає всі вузли рівномірно по сітці."""
        import math
        nodes = list(self.nodes.values())
        if not nodes:
            return
        cols = max(1, math.ceil(math.sqrt(len(nodes))))
        spacing_x, spacing_y = 200, 150
        for i, node in enumerate(nodes):
            node.x = (i % cols) * spacing_x + 60
            node.y = (i // cols) * spacing_y + 60
            item = self.node_items.get(node.uuid)
            if item:
                item.setPos(node.x, node.y)
        for li in self.link_items.values():
            li.update_position()
        self.mark_modified()
        self.status_message.emit('Авто-розміщення (сітка) виконано')

    def auto_layout_radial(self) -> None:
        """Розкладає вузли радіально: найбільш пов'язаний — у центрі."""
        import math
        nodes = list(self.nodes.values())
        if not nodes:
            return
        if len(nodes) == 1:
            nodes[0].x, nodes[0].y = 400, 300
            item = self.node_items.get(nodes[0].uuid)
            if item:
                item.setPos(400, 300)
            for li in self.link_items.values():
                li.update_position()
            self.mark_modified()
            return
        conn = {n.uuid: 0 for n in nodes}
        for lk in self.links.values():
            conn[lk.source_uuid] = conn.get(lk.source_uuid, 0) + 1
            conn[lk.target_uuid] = conn.get(lk.target_uuid, 0) + 1
        center_uuid = max(conn, key=lambda u: conn[u])
        cx, cy = 500, 400
        radius = min(150 + len(nodes) * 12, 380)
        center_node = self.nodes[center_uuid]
        center_node.x, center_node.y = cx, cy
        item = self.node_items.get(center_uuid)
        if item:
            item.setPos(cx, cy)
        others = [n for n in nodes if n.uuid != center_uuid]
        for i, node in enumerate(others):
            angle = 2 * math.pi * i / len(others)
            node.x = cx + radius * math.cos(angle)
            node.y = cy + radius * math.sin(angle)
            it = self.node_items.get(node.uuid)
            if it:
                it.setPos(node.x, node.y)
        for li in self.link_items.values():
            li.update_position()
        self.mark_modified()
        self.status_message.emit('Авто-розміщення (радіально) виконано')

    def auto_layout_circular(self) -> None:
        """Circular (i2): всі вузли рівномірно по колу."""
        import math
        nodes = list(self.nodes.values())
        if not nodes:
            return
        cx, cy = 500, 400
        radius = max(150, len(nodes) * 30)
        for i, node in enumerate(nodes):
            angle = 2 * math.pi * i / len(nodes) - math.pi / 2
            node.x = cx + radius * math.cos(angle)
            node.y = cy + radius * math.sin(angle)
            it = self.node_items.get(node.uuid)
            if it:
                it.setPos(node.x, node.y)
        for li in self.link_items.values():
            li.update_position()
        self.mark_modified()
        self.status_message.emit('Circular layout виконано')

    def auto_layout_hierarchy(self) -> None:
        """Hierarchy (i2): BFS від найбільш пов'язаного вузла, рівнями зверху вниз."""
        from collections import deque
        nodes = list(self.nodes.values())
        if not nodes:
            return

        # Граф суміжності
        adj: dict[str, list[str]] = {n.uuid: [] for n in nodes}
        for lk in self.links.values():
            adj[lk.source_uuid].append(lk.target_uuid)
            adj[lk.target_uuid].append(lk.source_uuid)

        # Корінь — найбільш пов'язаний
        root = max(adj, key=lambda u: len(adj[u]))

        # BFS для визначення рівнів
        level: dict[str, int] = {root: 0}
        queue: deque[str] = deque([root])
        while queue:
            cur = queue.popleft()
            for nb in adj[cur]:
                if nb not in level:
                    level[nb] = level[cur] + 1
                    queue.append(nb)
        # Ізольовані вузли — на окремому рівні
        max_lvl = max(level.values(), default=0)
        for n in nodes:
            if n.uuid not in level:
                max_lvl += 1
                level[n.uuid] = max_lvl

        # Групуємо по рівнях
        levels: dict[int, list[str]] = {}
        for uid, lvl in level.items():
            levels.setdefault(lvl, []).append(uid)

        y_step = 160
        for lvl, uids in sorted(levels.items()):
            x_step = max(180, 900 // (len(uids) + 1))
            for j, uid in enumerate(uids):
                x = (j + 1) * x_step - (len(uids) * x_step) / 2 + 500
                y = lvl * y_step + 60
                node = self.nodes.get(uid)
                if node:
                    node.x, node.y = x, y
                    it = self.node_items.get(uid)
                    if it:
                        it.setPos(x, y)
        for li in self.link_items.values():
            li.update_position()
        self.mark_modified()
        self.status_message.emit('Hierarchy layout виконано')

    def auto_layout_peacock(self) -> None:
        """Peacock (i2): центральний хаб + промені-гілки для кожного сусіда."""
        import math
        nodes = list(self.nodes.values())
        if not nodes:
            return

        # Граф суміжності
        adj: dict[str, list[str]] = {n.uuid: [] for n in nodes}
        for lk in self.links.values():
            adj[lk.source_uuid].append(lk.target_uuid)
            adj[lk.target_uuid].append(lk.source_uuid)

        # Центральний вузол — найбільш пов'язаний
        hub = max(adj, key=lambda u: len(adj[u]))
        cx, cy = 500, 400
        hub_node = self.nodes[hub]
        hub_node.x, hub_node.y = cx, cy
        hub_it = self.node_items.get(hub)
        if hub_it:
            hub_it.setPos(cx, cy)

        # Розкладаємо сусідів хаба по промінях
        branches = adj[hub]
        r1 = 220
        for i, nb in enumerate(branches):
            angle = 2 * math.pi * i / max(len(branches), 1) - math.pi / 2
            nx = cx + r1 * math.cos(angle)
            ny = cy + r1 * math.sin(angle)
            nb_node = self.nodes.get(nb)
            if nb_node:
                nb_node.x, nb_node.y = nx, ny
                nb_it = self.node_items.get(nb)
                if nb_it:
                    nb_it.setPos(nx, ny)

            # Сусіди сусіда (2-й рівень)
            sub = [u for u in adj[nb] if u != hub and u not in branches]
            r2 = 140
            for k, s in enumerate(sub):
                sub_angle = angle + (k - len(sub) / 2 + 0.5) * 0.5
                sx = nx + r2 * math.cos(sub_angle)
                sy = ny + r2 * math.sin(sub_angle)
                s_node = self.nodes.get(s)
                if s_node:
                    s_node.x, s_node.y = sx, sy
                    s_it = self.node_items.get(s)
                    if s_it:
                        s_it.setPos(sx, sy)

        # Ізольовані вузли — праворуч
        placed = {hub} | set(branches)
        for br in branches:
            placed |= set(adj[br])
        isolated = [n for n in nodes if n.uuid not in placed]
        for i, node in enumerate(isolated):
            node.x = 900 + (i % 3) * 180
            node.y = 60 + (i // 3) * 150
            it = self.node_items.get(node.uuid)
            if it:
                it.setPos(node.x, node.y)

        for li in self.link_items.values():
            li.update_position()
        self.mark_modified()
        self.status_message.emit('Peacock layout виконано')

    # ------------------------------------------------------------------
    # Групування вузлів
    # ------------------------------------------------------------------

    def group_selected(self) -> Optional['GroupItem']:
        """Групує виділені вузли у напівпрозорий контейнер."""
        items = [it for it in self._scene.selectedItems() if isinstance(it, NodeItem)]
        if len(items) < 2:
            self.status_message.emit('Виберіть 2 або більше вузлів для групування')
            return None
        label, ok = QInputDialog.getText(None, 'Назва групи', 'Введіть назву (необов\'язково):')
        if not ok:
            label = ''
        group = GroupItem(items, label.strip())
        self._scene.addItem(group)
        self._group_items.append(group)
        self._scene.clearSelection()
        group.setSelected(True)
        self.mark_modified()
        self.status_message.emit(f'Групу створено ({len(items)} вузлів)')
        return group

    def ungroup_selected(self) -> None:
        """Видаляє виділені GroupItem зі сцени."""
        removed = 0
        for item in list(self._scene.selectedItems()):
            if isinstance(item, GroupItem):
                self._scene.removeItem(item)
                if item in self._group_items:
                    self._group_items.remove(item)
                removed += 1
        if removed:
            self.mark_modified()
            self.status_message.emit(f'Розгруповано {removed} групу(и)')
        else:
            self.status_message.emit('Виберіть групу для розгрупування')

    # ------------------------------------------------------------------
    # Фільтр "тільки пов'язані"
    # ------------------------------------------------------------------

    def show_only_connected(self, node_uuid: str) -> None:
        """Приховує всі вузли та зв'язки, не пов'язані з вказаним вузлом."""
        connected = {node_uuid}
        for lk in self.links.values():
            if lk.source_uuid == node_uuid:
                connected.add(lk.target_uuid)
            elif lk.target_uuid == node_uuid:
                connected.add(lk.source_uuid)
        for uid, it in self.node_items.items():
            it.setVisible(uid in connected)
        for lu, li in self.link_items.items():
            lk = self.links.get(lu)
            li.setVisible(bool(lk and lk.source_uuid in connected and lk.target_uuid in connected))
        self.status_message.emit("Показано тільки пов'язані. ПКМ → 'Показати всі' щоб скасувати.")

    def show_all_nodes(self) -> None:
        """Відновлює видимість усіх вузлів і зв'язків."""
        for it in self.node_items.values():
            it.setVisible(True)
        for li in self.link_items.values():
            li.setVisible(True)
        self.status_message.emit('Усі елементи відображено')

    # ------------------------------------------------------------------
    # Find Path — BFS між двома вузлами
    # ------------------------------------------------------------------

    def find_path_between(self, start_uuid: str, end_uuid: str) -> list:
        """BFS пошук найкоротшого шляху між двома вузлами.
        Повертає список uuid вузлів або [] якщо шляху немає."""
        from collections import deque

        if start_uuid not in self.nodes or end_uuid not in self.nodes:
            return []
        if start_uuid == end_uuid:
            return [start_uuid]

        # Будуємо граф суміжності (неорієнтований для пошуку)
        adjacency: dict[str, list[str]] = {uid: [] for uid in self.nodes}
        for link in self.links.values():
            adjacency[link.source_uuid].append(link.target_uuid)
            adjacency[link.target_uuid].append(link.source_uuid)

        visited = {start_uuid}
        queue: deque[list[str]] = deque([[start_uuid]])

        while queue:
            path = queue.popleft()
            current = path[-1]
            for neighbor in adjacency.get(current, []):
                if neighbor == end_uuid:
                    return path + [neighbor]
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(path + [neighbor])
        return []

    def highlight_path(self, path_uuids: list) -> None:
        """Виділяє вузли і зв'язки що утворюють шлях; решту ховає."""
        if not path_uuids:
            self.status_message.emit('Шлях не знайдено')
            return

        path_set = set(path_uuids)

        # Визначаємо зв'язки на шляху
        path_links: set[str] = set()
        for i in range(len(path_uuids) - 1):
            a, b = path_uuids[i], path_uuids[i + 1]
            for uid, link in self.links.items():
                if {link.source_uuid, link.target_uuid} == {a, b}:
                    path_links.add(uid)
                    break

        for uid, it in self.node_items.items():
            it.setVisible(uid in path_set)
        for uid, li in self.link_items.items():
            li.setVisible(uid in path_links)

        self.status_message.emit(f'Шлях знайдено: {len(path_uuids)} вузлів')

    # ------------------------------------------------------------------
    # Малювання фону (сітка крапок)
    # ------------------------------------------------------------------

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        """Малює білий фон і, якщо увімкнено, сітку з крапок."""
        # Завжди заливаємо фон білим кольором
        painter.fillRect(rect, QColor('white'))

        if not self._grid_enabled:
            return

        # Крок сітки в пікселях сцени
        step = 30

        # Визначаємо діапазон видимих крапок у координатах сцени
        left = int(rect.left()) - (int(rect.left()) % step)
        top = int(rect.top()) - (int(rect.top()) % step)

        dot_color = QColor('#E0E0E0')
        painter.setPen(QPen(dot_color, 1))

        x = left
        while x <= rect.right():
            y = top
            while y <= rect.bottom():
                painter.drawPoint(x, y)
                y += step
            x += step

    # ------------------------------------------------------------------
    # Масштабування
    # ------------------------------------------------------------------

    def wheelEvent(self, event) -> None:
        """Масштабує вид колесом миші з обмеженнями."""
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        current_scale = self.transform().m11()

        # Обмежуємо діапазон масштабування
        if factor > 1 and current_scale > 5:
            return
        if factor < 1 and current_scale < 0.1:
            return

        self.scale(factor, factor)

    def zoom_in(self) -> None:
        """Збільшує масштаб на 20%."""
        self.scale(1.2, 1.2)

    def zoom_out(self) -> None:
        """Зменшує масштаб на 20%."""
        self.scale(1 / 1.2, 1 / 1.2)

    # ------------------------------------------------------------------
    # Прокручування (пробіл + перетягування / середня кнопка миші)
    # ------------------------------------------------------------------

    def keyPressEvent(self, event) -> None:
        """Обробляє натискання клавіш."""
        if event.key() == Qt.Key.Key_Space:
            self._space_pressed = True
            self.setCursor(Qt.CursorShape.OpenHandCursor)
        elif event.key() == Qt.Key.Key_Escape:
            if self._mode == 'link':
                self._link_source_uuid = None
                self.status_message.emit('Link Tool: виберіть перший вузол')
            elif self._shape_preview is not None:
                self._scene.removeItem(self._shape_preview)
                self._shape_preview = None
                self._shape_start = None
            else:
                self._scene.clearSelection()
        else:
            super().keyPressEvent(event)

    def keyReleaseEvent(self, event) -> None:
        """Обробляє відпускання клавіш."""
        if event.key() == Qt.Key.Key_Space:
            self._space_pressed = False
            self._pan_start = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            # Відновлюємо режим виділення, якщо треба
            if self._mode == 'select':
                self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        else:
            super().keyReleaseEvent(event)

    def mousePressEvent(self, event) -> None:
        """Обробляє натискання кнопок миші."""
        is_pan_trigger = (
            self._space_pressed
            or event.button() == Qt.MouseButton.MiddleButton
        )

        if is_pan_trigger:
            # Починаємо режим прокручування
            self._pan_start = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            return

        if self._mode == 'link' and event.button() == Qt.MouseButton.LeftButton:
            # Режим побудови зв'язку: визначаємо, який вузол натиснутий
            item = self.itemAt(event.pos())

            # Рухаємось вгору по ієрархії, щоб знайти NodeItem
            node_item: Optional[NodeItem] = None
            candidate = item
            while candidate is not None:
                if isinstance(candidate, NodeItem):
                    node_item = candidate
                    break
                candidate = candidate.parentItem()

            if node_item is not None:
                if self._link_source_uuid is None:
                    self._link_source_uuid = node_item.node.uuid
                    self.status_message.emit('Link Tool: виберіть другий вузол')
                elif node_item.node.uuid != self._link_source_uuid:
                    self.link_creation_requested.emit(
                        self._link_source_uuid, node_item.node.uuid
                    )
                    self._link_source_uuid = None
                    self.status_message.emit('Link Tool: виберіть перший вузол')
            return

        if self._mode in ('line', 'circle', 'rect', 'text') and event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            self._shape_start = scene_pos

            if self._mode == 'text':
                text, ok = QInputDialog.getText(self, 'Текстова мітка', 'Введіть текст:')
                if ok and text.strip():
                    item = QGraphicsSimpleTextItem(text.strip())
                    font = QFont()
                    font.setPointSize(12)
                    item.setFont(font)
                    item.setPos(scene_pos)
                    item.setFlags(
                        QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
                        QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
                    )
                    item.setZValue(0.5)
                    self.undo_stack.push(AddShapeCommand(self, item))
                    self.mark_modified()
                self._shape_start = None
            else:
                pen = QPen(QColor('#555555'), 2)
                if self._mode == 'line':
                    preview = QGraphicsLineItem(QLineF(scene_pos, scene_pos))
                    preview.setPen(pen)
                elif self._mode == 'circle':
                    preview = QGraphicsEllipseItem(QRectF(scene_pos, QSizeF(0, 0)))
                    preview.setPen(pen)
                    preview.setBrush(QBrush(QColor(100, 150, 255, 50)))
                else:  # rect
                    preview = QGraphicsRectItem(QRectF(scene_pos, QSizeF(0, 0)))
                    preview.setPen(pen)
                    preview.setBrush(QBrush(QColor(100, 150, 255, 50)))
                preview.setZValue(-0.5)
                self._shape_preview = preview
                self._scene.addItem(preview)
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        """Прокручує вигляд або оновлює preview-фігуру."""
        if self._pan_start is not None:
            delta = event.pos() - self._pan_start
            self._pan_start = event.pos()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )
            return

        if self._shape_preview is not None and self._shape_start is not None:
            scene_pos = self.mapToScene(event.pos())
            if self._mode == 'line':
                self._shape_preview.setLine(QLineF(self._shape_start, scene_pos))
            elif self._mode in ('circle', 'rect'):
                rect = QRectF(self._shape_start, scene_pos).normalized()
                self._shape_preview.setRect(rect)
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        """Завершує прокручування або фіналізує малювання фігури."""
        if self._pan_start is not None:
            self._pan_start = None
            if self._space_pressed:
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            else:
                self.setCursor(Qt.CursorShape.ArrowCursor)
                if self._mode == 'select':
                    self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
            return

        if self._shape_preview is not None and self._shape_start is not None and event.button() == Qt.MouseButton.LeftButton:
            scene_pos = self.mapToScene(event.pos())
            valid = False
            if self._mode == 'line':
                line = QLineF(self._shape_start, scene_pos)
                valid = line.length() > 8
                if valid:
                    self._shape_preview.setLine(line)
            elif self._mode in ('circle', 'rect'):
                rect = QRectF(self._shape_start, scene_pos).normalized()
                valid = rect.width() > 8 or rect.height() > 8
                if valid:
                    self._shape_preview.setRect(rect)

            item = self._shape_preview
            self._shape_preview = None
            self._shape_start = None
            self._scene.removeItem(item)

            if valid:
                item.setFlags(
                    QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
                    QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
                )
                self.undo_stack.push(AddShapeCommand(self, item))
                self.mark_modified()
            return

        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        """Подвійний клік на порожньому місці — сигнал для створення вузла."""
        if (
            self._mode == 'select'
            and event.button() == Qt.MouseButton.LeftButton
        ):
            item = self.itemAt(event.pos())
            if item is None:
                # Кліки на порожньому місці — надсилаємо координати сцени
                scene_pos = self.mapToScene(event.pos())
                self.empty_space_double_clicked.emit(scene_pos)
                return

        super().mouseDoubleClickEvent(event)

    # ------------------------------------------------------------------
    # Обробник зміни виділення сцени
    # ------------------------------------------------------------------

    def _on_selection_changed(self) -> None:
        """Надсилає сигнали при зміні виділення на сцені."""
        selected = self._scene.selectedItems()

        nodes_sel = [i.node for i in selected if isinstance(i, NodeItem)]
        links_sel = [i.link for i in selected if isinstance(i, LinkItem)]

        if len(selected) == 1:
            if isinstance(selected[0], NodeItem):
                self.node_selected.emit(selected[0].node)
            elif isinstance(selected[0], LinkItem):
                self.link_selected.emit(selected[0].link)
        elif len(selected) == 0:
            self.node_selected.emit(None)

        self.selection_changed.emit(nodes_sel + links_sel)

    # ------------------------------------------------------------------
    # Обробники подій вузлів
    # ------------------------------------------------------------------

    def _on_node_moved(self, node_uuid: str) -> None:
        """Оновлює позиції всіх зв'язків, прив'язаних до переміщеного вузла."""
        for link_uuid, link in self.links.items():
            if link.source_uuid == node_uuid or link.target_uuid == node_uuid:
                if link_uuid in self.link_items:
                    self.link_items[link_uuid].update_position()

    def _on_delete_node_requested(self, node_uuid: str) -> None:
        """Створює команду видалення вузла разом із прив'язаними зв'язками."""
        node = self.nodes.get(node_uuid)
        if node is None:
            return

        # Збираємо всі зв'язки, що стосуються цього вузла
        related_links = [
            lk for lk in self.links.values()
            if lk.source_uuid == node_uuid or lk.target_uuid == node_uuid
        ]

        self.undo_stack.push(DeleteNodesCommand(self, [node], related_links))

    def _on_duplicate_node_requested(self, node_uuid: str) -> None:
        """Створює команду дублювання вузла зі зміщенням 40px."""
        original = self.nodes.get(node_uuid)
        if original is None:
            return

        new_node = copy.deepcopy(original)
        new_node.uuid = str(uuid.uuid4())
        new_node.x += 40
        new_node.y += 40

        self.undo_stack.push(DuplicateNodeCommand(self, new_node))

    def _on_color_change_requested(self, node_uuid: str, new_color: str) -> None:
        """Створює команду зміни кольору вузла."""
        node = self.nodes.get(node_uuid)
        if node is None:
            return

        old_color = node.color
        self.undo_stack.push(ColorNodeCommand(self, node_uuid, old_color, new_color))

    # ------------------------------------------------------------------
    # Обробники подій зв'язків
    # ------------------------------------------------------------------

    def _on_delete_link_requested(self, link_uuid: str) -> None:
        """Створює команду видалення зв'язку."""
        link = self.links.get(link_uuid)
        if link is None:
            return

        self.undo_stack.push(DeleteLinksCommand(self, [link]))

    # ------------------------------------------------------------------
    # Стан вигляду (для збереження у файл)
    # ------------------------------------------------------------------

    def get_viewport_state(self) -> dict:
        """Повертає словник із поточним центром і масштабом вигляду."""
        center = self.mapToScene(self.viewport().rect().center())
        return {
            'center_x': center.x(),
            'center_y': center.y(),
            'zoom': self.transform().m11(),
        }

    def set_viewport_state(self, state: dict) -> None:
        """Відновлює центр і масштаб вигляду зі словника."""
        self.resetTransform()
        zoom = state.get('zoom', 1.0)
        self.scale(zoom, zoom)
        self.centerOn(
            QPointF(state.get('center_x', 0.0), state.get('center_y', 0.0))
        )

    # ------------------------------------------------------------------
    # Фільтрація за типом вузла
    # ------------------------------------------------------------------

    def set_type_filter(self, visible_types: list[str]) -> None:
        """Показує лише вузли вказаних типів і зв'язки між ними."""
        # Оновлюємо видимість вузлів
        for node_uuid, item in self.node_items.items():
            item.setVisible(item.node.type in visible_types)

        # Оновлюємо видимість зв'язків: показуємо лише ті,
        # в яких обидва кінця видимі
        for link_uuid, item in self.link_items.items():
            link = self.links.get(link_uuid)
            if link is None:
                item.setVisible(False)
                continue

            src_visible = (
                self.node_items[link.source_uuid].isVisible()
                if link.source_uuid in self.node_items
                else False
            )
            tgt_visible = (
                self.node_items[link.target_uuid].isVisible()
                if link.target_uuid in self.node_items
                else False
            )
            item.setVisible(src_visible and tgt_visible)

    # ------------------------------------------------------------------
    # Експорт PNG
    # ------------------------------------------------------------------

    def export_png(self, filepath: str) -> bool:
        """Рендерить усю схему у PNG-файл; повертає True в разі успіху."""
        rect = self._scene.itemsBoundingRect().adjusted(-20, -20, 20, 20)

        if rect.width() <= 0 or rect.height() <= 0:
            return False

        image = QImage(
            int(rect.width()),
            int(rect.height()),
            QImage.Format.Format_RGB32,
        )
        image.fill(QColor('white'))

        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._scene.render(painter, QRectF(image.rect()), rect)
        painter.end()

        return image.save(filepath, 'PNG')

    # ------------------------------------------------------------------
    # Експорт PDF
    # ------------------------------------------------------------------

    def export_pdf(self, filepath: str) -> bool:
        """Рендерить схему у PDF-файл формату A4 landscape; повертає True в разі успіху."""
        try:
            scene_rect = self._scene.itemsBoundingRect().adjusted(-20, -20, 20, 20)
            if scene_rect.width() <= 0 or scene_rect.height() <= 0:
                return False

            # QPdfWriter — спеціальний клас для PDF, не потребує принтера
            writer = QPdfWriter(filepath)
            writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
            writer.setPageOrientation(QPageLayout.Orientation.Landscape)
            writer.setResolution(150)  # DPI: достатньо для друку A4

            painter = QPainter(writer)
            if not painter.isActive():
                return False

            # Розмір сторінки в пікселях при заданому DPI
            page_rect = QRectF(0, 0, writer.width(), writer.height())
            self._scene.render(
                painter,
                page_rect,
                scene_rect,
                Qt.AspectRatioMode.KeepAspectRatio,
            )
            painter.end()
            return True

        except Exception as e:
            print(f'[PDF Export Error] {e}')
            return False


# =============================================================================
# Збереження / Завантаження JSON (функції рівня модуля)
# =============================================================================


def _serialize_shape(item) -> Optional[dict]:
    """Серіалізує QGraphicsItem-фігуру в словник."""
    pen = item.pen() if hasattr(item, 'pen') else None
    pen_data = {}
    if pen is not None:
        pen_data = {
            'color': pen.color().name(),
            'width': pen.widthF(),
            'style': int(pen.style()),
        }
    brush_data = {}
    if hasattr(item, 'brush'):
        b = item.brush()
        brush_data = {'color': b.color().name(), 'alpha': b.color().alpha()}

    pos = item.pos()
    base = {'pos': [pos.x(), pos.y()], 'pen': pen_data, 'brush': brush_data, 'z': item.zValue()}

    if isinstance(item, QGraphicsLineItem):
        ln = item.line()
        return {**base, 'type': 'line', 'x1': ln.x1(), 'y1': ln.y1(), 'x2': ln.x2(), 'y2': ln.y2()}
    elif isinstance(item, QGraphicsEllipseItem):
        r = item.rect()
        return {**base, 'type': 'ellipse', 'x': r.x(), 'y': r.y(), 'w': r.width(), 'h': r.height()}
    elif isinstance(item, QGraphicsRectItem):
        r = item.rect()
        return {**base, 'type': 'rect', 'x': r.x(), 'y': r.y(), 'w': r.width(), 'h': r.height()}
    elif isinstance(item, QGraphicsSimpleTextItem):
        return {**base, 'type': 'text', 'text': item.text(),
                'font_size': item.font().pointSize()}
    return None


def _deserialize_shape(d: dict) -> Optional[object]:
    """Відновлює QGraphicsItem-фігуру зі словника."""
    pen_d = d.get('pen', {})
    pen = QPen(QColor(pen_d.get('color', '#555555')), pen_d.get('width', 2))
    pen.setStyle(Qt.PenStyle(pen_d.get('style', 1)))

    brush_d = d.get('brush', {})
    brush_color = QColor(brush_d.get('color', '#6496FF'))
    brush_color.setAlpha(brush_d.get('alpha', 50))
    brush = QBrush(brush_color)

    shape_type = d.get('type', '')
    item = None

    if shape_type == 'line':
        item = QGraphicsLineItem(QLineF(d['x1'], d['y1'], d['x2'], d['y2']))
        item.setPen(pen)
    elif shape_type == 'ellipse':
        item = QGraphicsEllipseItem(QRectF(d['x'], d['y'], d['w'], d['h']))
        item.setPen(pen)
        item.setBrush(brush)
    elif shape_type == 'rect':
        item = QGraphicsRectItem(QRectF(d['x'], d['y'], d['w'], d['h']))
        item.setPen(pen)
        item.setBrush(brush)
    elif shape_type == 'text':
        item = QGraphicsSimpleTextItem(d.get('text', ''))
        f = QFont()
        f.setPointSize(int(d.get('font_size', 12)))
        item.setFont(f)

    if item is not None:
        p = d.get('pos', [0, 0])
        item.setPos(QPointF(p[0], p[1]))
        item.setZValue(d.get('z', -0.5))
        item.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable |
            QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
        )
    return item


def save_to_json(canvas: DiagramCanvas, filepath: str) -> bool:
    """Зберігає поточну схему у файл JSON.

    Якщо файл існує — читає оригінальне created_at, щоб не перезаписувати.
    Повертає True при успіху, False — при будь-якій помилці.
    """
    try:
        # Читаємо оригінальну дату створення, якщо файл уже існує
        original_created_at: Optional[str] = None
        if os.path.isfile(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as fh:
                    existing = json.load(fh)
                    original_created_at = existing.get('created_at')
            except Exception:
                pass  # Не критично — просто запишемо поточний час

        now = datetime.now().isoformat()

        # Серіалізуємо фігури (line / ellipse / rect / text)
        shapes_data = []
        for sh in canvas._shape_items:
            s = _serialize_shape(sh)
            if s:
                shapes_data.append(s)

        # Серіалізуємо групи
        groups_data = []
        for grp in canvas._group_items:
            member_uuids = []
            for m in grp.members():
                if isinstance(m, NodeItem):
                    member_uuids.append(m.node.uuid)
            r = grp.rect()
            groups_data.append({
                'label': grp._label,
                'rect': [r.x(), r.y(), r.width(), r.height()],
                'pos': [grp.pos().x(), grp.pos().y()],
                'member_uuids': member_uuids,
            })

        data = {
            'schema_version': SCHEMA_VERSION,
            'created_at': original_created_at if original_created_at else now,
            'updated_at': now,
            'grid_enabled': canvas.get_grid_enabled(),
            'snap_to_grid': canvas._snap_to_grid,
            'viewport': canvas.get_viewport_state(),
            'nodes': [node.to_dict() for node in canvas.nodes.values()],
            'links': [link.to_dict() for link in canvas.links.values()],
            'groups': groups_data,
            'shapes': shapes_data,
        }

        with open(filepath, 'w', encoding='utf-8') as fh:
            json.dump(data, fh, indent=2, ensure_ascii=False)

        # Скидаємо прапор змін
        canvas.is_modified = False
        canvas.current_file = filepath
        canvas.modified_changed.emit(False)

        return True

    except Exception:
        return False


def load_from_json(canvas: DiagramCanvas, filepath: str) -> tuple[bool, str]:
    """Завантажує схему з JSON-файлу в canvas.

    Повертає (True, попередження_про_пропущені_зв'язки) або (False, текст_помилки).
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as fh:
            data = json.load(fh)

        # Базова перевірка структури файлу
        if not isinstance(data, dict) or 'nodes' not in data or 'links' not in data:
            return False, 'Невірний формат файлу: відсутні ключі "nodes" або "links".'

        # Очищаємо поточну сцену перед завантаженням
        canvas.clear_scene()

        # --- Завантажуємо вузли ---
        for node_dict in data.get('nodes', []):
            try:
                node = Node.from_dict(node_dict)
                canvas.add_node(node)
            except Exception as exc:
                # Пропускаємо пошкоджені вузли, продовжуємо завантаження
                import sys as _sys
                print(f'[load_from_json] пропущено вузол: {exc}', file=_sys.stderr)

        # --- Завантажуємо зв'язки ---
        skipped_links: list[str] = []

        for link_dict in data.get('links', []):
            try:
                link = Link.from_dict(link_dict)

                # Перевіряємо, чи існують обидва вузли
                if link.source_uuid not in canvas.nodes:
                    skipped_links.append(
                        f'{link.uuid} (невідомий source {link.source_uuid})'
                    )
                    continue
                if link.target_uuid not in canvas.nodes:
                    skipped_links.append(
                        f'{link.uuid} (невідомий target {link.target_uuid})'
                    )
                    continue

                canvas.add_link(link)

            except Exception as exc:
                skipped_links.append(f'помилка: {exc}')

        # --- Відновлюємо фігури ---
        for shape_dict in data.get('shapes', []):
            item = _deserialize_shape(shape_dict)
            if item is not None:
                canvas._scene.addItem(item)
                canvas._shape_items.append(item)

        # --- Відновлюємо групи ---
        for grp_dict in data.get('groups', []):
            member_uuids = grp_dict.get('member_uuids', [])
            member_items = [canvas.node_items[u] for u in member_uuids if u in canvas.node_items]
            if member_items:
                grp = GroupItem(member_items, grp_dict.get('label', ''))
                r = grp_dict.get('rect')
                if r and len(r) == 4:
                    grp.setRect(QRectF(*r))
                p = grp_dict.get('pos')
                if p and len(p) == 2:
                    grp.setPos(QPointF(*p))
                canvas._scene.addItem(grp)
                canvas._group_items.append(grp)

        # --- Відновлюємо стан вигляду ---
        viewport_data = data.get('viewport', {})
        if viewport_data:
            canvas.set_viewport_state(viewport_data)

        # --- Відновлюємо стан сітки та snap ---
        if 'grid_enabled' in data and not data['grid_enabled']:
            canvas._grid_enabled = False
            canvas.viewport().update()
        canvas._snap_to_grid = bool(data.get('snap_to_grid', False))

        # --- Скидаємо прапор змін ---
        canvas.is_modified = False
        canvas.current_file = filepath
        canvas.modified_changed.emit(False)

        # Формуємо попередження, якщо частину зв'язків пропущено
        warning = ''
        if skipped_links:
            warning = (
                f'Пропущено {len(skipped_links)} зв\'язок(ів) '
                f'через відсутні вузли:\n' + '\n'.join(skipped_links)
            )

        return True, warning

    except Exception as exc:
        return False, str(exc)


# =============================================================================
# Імпорт CSV
# =============================================================================


def import_from_csv(
    canvas: DiagramCanvas,
    nodes_filepath: str,
) -> tuple[int, int, str]:
    """Імпортує вузли з nodes.csv та (якщо є) зв'язки з links.csv.

    nodes.csv: id, type, title, note, date, color, x, y
    links.csv: source_id, target_id, label, line_type, direction, note

    Повертає (кількість_вузлів, кількість_зв'язків, рядок_помилки_або_порожній).
    """
    nodes_path = Path(nodes_filepath)
    links_path = nodes_path.parent / 'links.csv'

    # --- Перевіряємо обов'язковий файл вузлів ---
    if not nodes_path.is_file():
        return 0, 0, f'Файл не знайдено: {nodes_filepath}'

    # Відображення: id з CSV → UUID нового вузла
    id_to_uuid: dict[str, str] = {}
    nodes_count = 0
    errors: list[str] = []

    # Лічильник для авторозміщення в сітку (використовується, якщо x/y порожні)
    auto_col = 0
    auto_row = 0
    auto_cols_per_row = 8
    auto_step = 150

    # --- Читаємо вузли ---
    try:
        with open(nodes_path, newline='', encoding='utf-8-sig') as fh:
            reader = csv.DictReader(fh)

            # Перевіряємо наявність обов'язкових стовпців
            if reader.fieldnames is None:
                return 0, 0, 'nodes.csv: порожній файл або відсутні заголовки.'

            required_node_cols = {'id', 'title'}
            missing = required_node_cols - set(reader.fieldnames)
            if missing:
                return 0, 0, f'nodes.csv: відсутні стовпці: {", ".join(sorted(missing))}'

            for row_num, row in enumerate(reader, start=2):
                row_id = row.get('id', '').strip()
                if not row_id:
                    errors.append(f'nodes.csv рядок {row_num}: порожній id — пропущено')
                    continue

                # Визначаємо тип; якщо невідомий — використовуємо 'Document'
                raw_type = row.get('type', '').strip()
                node_type = raw_type if raw_type in NODE_TYPES else 'Document'

                # Колір: зі стовпця або стандартний для типу
                raw_color = row.get('color', '').strip()
                node_color = raw_color if raw_color else None

                # Координати: з CSV або авторозміщення
                raw_x = row.get('x', '').strip()
                raw_y = row.get('y', '').strip()

                if raw_x and raw_y:
                    try:
                        node_x = float(raw_x)
                        node_y = float(raw_y)
                    except ValueError:
                        # Якщо не вдалось — авторозміщення
                        node_x = auto_col * auto_step
                        node_y = auto_row * auto_step
                        auto_col += 1
                        if auto_col >= auto_cols_per_row:
                            auto_col = 0
                            auto_row += 1
                else:
                    node_x = auto_col * auto_step
                    node_y = auto_row * auto_step
                    auto_col += 1
                    if auto_col >= auto_cols_per_row:
                        auto_col = 0
                        auto_row += 1

                node = Node(
                    type=node_type,
                    title=row.get('title', '').strip(),
                    note=row.get('note', '').strip(),
                    date=row.get('date', '').strip(),
                    x=node_x,
                    y=node_y,
                    color=node_color,
                )

                id_to_uuid[row_id] = node.uuid
                canvas.add_node(node)
                nodes_count += 1

    except Exception as exc:
        return 0, 0, f'Помилка читання nodes.csv: {exc}'

    # --- Читаємо зв'язки (якщо файл існує) ---
    links_count = 0

    if links_path.is_file():
        try:
            with open(links_path, newline='', encoding='utf-8-sig') as fh:
                reader = csv.DictReader(fh)

                if reader.fieldnames is not None:
                    required_link_cols = {'source_id', 'target_id'}
                    missing_link = required_link_cols - set(reader.fieldnames)

                    if missing_link:
                        errors.append(
                            f'links.csv: відсутні стовпці '
                            f'{", ".join(sorted(missing_link))} — зв\'язки не завантажено'
                        )
                    else:
                        for row_num, row in enumerate(reader, start=2):
                            src_id = row.get('source_id', '').strip()
                            tgt_id = row.get('target_id', '').strip()

                            if not src_id or not tgt_id:
                                errors.append(
                                    f'links.csv рядок {row_num}: '
                                    f'порожній source_id або target_id — пропущено'
                                )
                                continue

                            if src_id not in id_to_uuid:
                                errors.append(
                                    f'links.csv рядок {row_num}: '
                                    f'невідомий source_id "{src_id}" — пропущено'
                                )
                                continue

                            if tgt_id not in id_to_uuid:
                                errors.append(
                                    f'links.csv рядок {row_num}: '
                                    f'невідомий target_id "{tgt_id}" — пропущено'
                                )
                                continue

                            # Визначаємо тип лінії (з валідацією)
                            raw_line_type = row.get('line_type', '').strip()
                            line_type = (
                                raw_line_type
                                if raw_line_type in LINE_TYPE_LABELS
                                else 'solid_arrow'
                            )

                            # Визначаємо напрямок (з валідацією)
                            raw_direction = row.get('direction', '').strip()
                            direction = (
                                raw_direction
                                if raw_direction in DIRECTION_LABELS
                                else 'source_to_target'
                            )

                            link = Link(
                                source_uuid=id_to_uuid[src_id],
                                target_uuid=id_to_uuid[tgt_id],
                                label=row.get('label', '').strip(),
                                line_type=line_type,
                                direction=direction,
                                note=row.get('note', '').strip(),
                            )

                            canvas.add_link(link)
                            links_count += 1

        except Exception as exc:
            errors.append(f'Помилка читання links.csv: {exc}')

    canvas.mark_modified()

    error_string = '\n'.join(errors) if errors else ''
    return nodes_count, links_count, error_string


# =============================================================================
# MinimapView — мінімапа (зменшений огляд всієї сцени)
# =============================================================================


class MinimapView(QGraphicsView):
    """Мінімапа: зменшений вид сцени з позначкою поточного viewport."""

    def __init__(self, scene: QGraphicsScene, main_view: 'DiagramCanvas', parent=None) -> None:
        super().__init__(scene, parent)
        self._main_view = main_view
        self.setFixedSize(240, 170)
        self.setInteractive(False)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setStyleSheet('border: 1px solid #bbb; background: #f8f8f8;')

        # Оновлюємо коли прокручується або масштабується головний вид
        main_view.horizontalScrollBar().valueChanged.connect(self._refresh)
        main_view.verticalScrollBar().valueChanged.connect(self._refresh)

        # Таймер для оновлення при змінах сцени (обмежуємо до 5 разів/сек)
        self._timer = QTimer(self)
        self._timer.setInterval(200)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._do_fit)
        scene.changed.connect(lambda _: self._timer.start())

        self._do_fit()

    def _refresh(self) -> None:
        self.viewport().update()

    def _do_fit(self) -> None:
        bounds = self._main_view._scene.itemsBoundingRect()
        if bounds.isEmpty():
            bounds = QRectF(-200, -200, 400, 400)
        self.fitInView(bounds.adjusted(-80, -80, 80, 80), Qt.AspectRatioMode.KeepAspectRatio)
        self.viewport().update()

    def drawForeground(self, painter: QPainter, rect: QRectF) -> None:
        """Малює прямокутник видимої зони головного вигляду."""
        super().drawForeground(painter, rect)
        visible = self._main_view.mapToScene(
            self._main_view.viewport().rect()
        ).boundingRect()
        pen = QPen(QColor('#E74C3C'), 2)
        pen.setCosmetic(True)  # Товщина лінії не масштабується разом з вмістом
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor(231, 76, 60, 35)))
        painter.drawRect(visible)


# =============================================================================
# AutosaveManager — автоматичне фонове збереження
# =============================================================================


class AutosaveManager(QObject):
    """Менеджер автозбереження: зберігає схему у фоновому режимі кожні N хвилин."""

    def __init__(self, canvas: DiagramCanvas, parent=None) -> None:
        super().__init__(parent)
        self.canvas = canvas

        # Таймер спрацьовує раз на AUTOSAVE_INTERVAL_MS
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._do_autosave)

    # ------------------------------------------------------------------
    # Керування таймером
    # ------------------------------------------------------------------

    def start(self) -> None:
        """Запускає таймер автозбереження."""
        self._timer.start(AUTOSAVE_INTERVAL_MS)

    def stop(self) -> None:
        """Зупиняє таймер автозбереження."""
        self._timer.stop()

    # ------------------------------------------------------------------
    # Внутрішній обробник таймера
    # ------------------------------------------------------------------

    def _do_autosave(self) -> None:
        """Виконує збереження, якщо схема змінена та містить хоча б один вузол.

        Зберігається у тимчасовий файл AUTOSAVE_PATH без жодного UI.
        Помилки виводяться лише в stderr, щоб не заважати роботі.
        """
        if not self.canvas.is_modified:
            return
        if not self.canvas.nodes:
            return

        try:
            shapes_data = [s for s in (_serialize_shape(sh) for sh in self.canvas._shape_items) if s]
            data = {
                'schema_version': SCHEMA_VERSION,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                'grid_enabled': self.canvas.get_grid_enabled(),
                'snap_to_grid': self.canvas._snap_to_grid,
                'viewport': self.canvas.get_viewport_state(),
                'nodes': [node.to_dict() for node in self.canvas.nodes.values()],
                'links': [link.to_dict() for link in self.canvas.links.values()],
                'shapes': shapes_data,
            }

            with open(AUTOSAVE_PATH, 'w', encoding='utf-8') as fh:
                json.dump(data, fh, indent=2, ensure_ascii=False)

        except Exception as exc:
            import sys as _sys
            print(f'[AutosaveManager] автозбереження не вдалось: {exc}', file=_sys.stderr)

    # ------------------------------------------------------------------
    # Перевірка наявності файлу автозбереження
    # ------------------------------------------------------------------

    def check_for_autosave(self) -> Optional[str]:
        """Повертає шлях до файлу автозбереження, якщо він існує; інакше None."""
        if os.path.isfile(AUTOSAVE_PATH):
            return AUTOSAVE_PATH
        return None

    # ------------------------------------------------------------------
    # Видалення файлу автозбереження
    # ------------------------------------------------------------------

    def clear_autosave(self) -> None:
        """Видаляє файл автозбереження, якщо він існує."""
        try:
            if os.path.isfile(AUTOSAVE_PATH):
                os.remove(AUTOSAVE_PATH)
        except Exception as exc:
            import sys as _sys
            print(f'[AutosaveManager] не вдалось видалити автозбереження: {exc}', file=_sys.stderr)
# =============================================================================
# ЧАСТИНА 4 — Діалоги, панелі, головне вікно та точка входу
# =============================================================================


# ---------------------------------------------------------------------------
# Діалог редагування / створення вузла
# ---------------------------------------------------------------------------

class NodeDialog(QDialog):
    """Діалог для створення нового або редагування існуючого вузла."""

    def __init__(self, parent=None, node: 'Node' = None) -> None:
        super().__init__(parent)
        self._node = node
        # Поточний колір кнопки (hex-рядок)
        self._color: str = NODE_DEFAULT_COLORS.get('Person', '#4A90D9')
        # Флаг: чи користувач вже вручну обрав колір (не змінювати при зміні типу)
        self._custom_color: bool = False
        # Фото у вигляді base64-рядка
        self._photo_b64: str = ''

        self.setWindowTitle('Редагувати вузол' if node else 'Новий вузол')
        self.setMinimumWidth(420)
        self._build_ui()

        if node:
            self._populate_from_node(node)

    # ------------------------------------------------------------------
    # Побудова UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setSpacing(10)
        root_layout.setContentsMargins(12, 12, 12, 12)

        form = QFormLayout()
        form.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(8)

        # --- Тип вузла ---
        self._type_combo = QComboBox()
        for key, label in NODE_TYPE_LABELS.items():
            self._type_combo.addItem(label, userData=key)
        self._type_combo.currentIndexChanged.connect(self._on_type_changed)
        form.addRow('Тип:', self._type_combo)

        # --- Назва (обов'язкове поле) ---
        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("Назва вузла (обов'язково)")
        self._title_edit.textChanged.connect(self._validate)
        form.addRow('Назва:', self._title_edit)

        # --- Примітка ---
        self._note_edit = QTextEdit()
        self._note_edit.setPlaceholderText('Довільна примітка…')
        self._note_edit.setMaximumHeight(72)  # приблизно 3 рядки
        form.addRow('Примітка:', self._note_edit)

        # --- Дата ---
        self._date_edit = QLineEdit()
        self._date_edit.setPlaceholderText('дд.мм.рррр або довільно')
        form.addRow('Дата:', self._date_edit)

        # --- Колір ---
        self._color_btn = QPushButton()
        self._color_btn.setFixedWidth(90)
        self._color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._color_btn.clicked.connect(self._on_pick_color)
        self._refresh_color_button()
        form.addRow('Колір:', self._color_btn)

        # --- Фото ---
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

        # --- Icon Frame ---
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

        # --- Кнопки OK / Скасувати ---
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText('OK')
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('Скасувати')
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self._ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
        root_layout.addWidget(buttons)

        # Первинна перевірка
        self._validate()

    # ------------------------------------------------------------------
    # Заповнення полів при редагуванні
    # ------------------------------------------------------------------

    def _populate_from_node(self, node: 'Node') -> None:
        # Тип
        for i in range(self._type_combo.count()):
            if self._type_combo.itemData(i) == node.type:
                self._type_combo.setCurrentIndex(i)
                break

        self._title_edit.setText(node.title)
        self._note_edit.setPlainText(node.note)
        self._date_edit.setText(node.date)

        # Колір: при редагуванні вважається, що він вже «вручну» заданий
        self._color = node.color
        self._custom_color = True
        self._refresh_color_button()

        # Фото
        if node.photo_base64:
            self._photo_b64 = node.photo_base64
            self._refresh_photo_label()

        # Frame
        self._frame_enabled_cb.setChecked(getattr(node, 'frame_enabled', False))
        self._frame_color = getattr(node, 'frame_color', '#FF0000')
        self._frame_width_spin.setValue(getattr(node, 'frame_width', 3))
        self._refresh_frame_color_btn()

    # ------------------------------------------------------------------
    # Слоти
    # ------------------------------------------------------------------

    def _on_type_changed(self, _index: int) -> None:
        """Автоматично підставляє стандартний колір типу, якщо не обрано власний."""
        if not self._custom_color:
            key = self._type_combo.currentData()
            self._color = NODE_DEFAULT_COLORS.get(key, '#4A90D9')
            self._refresh_color_button()

    def _on_pick_color(self) -> None:
        """Відкриває QColorDialog; фіксує прапор власного кольору."""
        current = QColor(self._color)
        chosen = QColorDialog.getColor(current, self, 'Виберіть колір вузла')
        if chosen.isValid():
            self._color = chosen.name()
            self._custom_color = True
            self._refresh_color_button()

    def _on_choose_photo(self) -> None:
        """Відкриває діалог вибору файлу зображення та завантажує його в base64."""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            'Вибрати фото',
            '',
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
        """Видаляє прив'язане фото."""
        self._photo_b64 = ''
        self._refresh_photo_label()

    def _validate(self) -> None:
        """Вмикає/вимикає кнопку OK залежно від заповнення поля назви."""
        has_title = bool(self._title_edit.text().strip())
        self._ok_btn.setEnabled(has_title)

    # ------------------------------------------------------------------
    # Допоміжні методи
    # ------------------------------------------------------------------

    def _refresh_color_button(self) -> None:
        """Оновлює фон кнопки кольору відповідно до self._color."""
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
        """Оновлює мініатюру фото та стан кнопки видалення."""
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

    # ------------------------------------------------------------------
    # Публічний API
    # ------------------------------------------------------------------

    def get_node_data(self) -> dict:
        """Повертає словник із даними форми або порожній dict при некоректних даних."""
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


# ---------------------------------------------------------------------------
# Діалог редагування / створення зв'язку
# ---------------------------------------------------------------------------

class LinkDialog(QDialog):
    """Діалог для створення нового або редагування існуючого зв'язку."""

    def __init__(self, parent=None, link: 'Link' = None) -> None:
        super().__init__(parent)
        self._link = link
        self._link_color: str = '#555555'
        self.setWindowTitle("Редагувати зв'язок" if link else "Новий зв'язок")
        self.setMinimumWidth(380)
        self._build_ui()
        if link:
            self._populate_from_link(link)

    # ------------------------------------------------------------------
    # Побудова UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root_layout = QVBoxLayout(self)
        root_layout.setSpacing(10)
        root_layout.setContentsMargins(12, 12, 12, 12)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(8)

        # --- Підпис зв'язку ---
        self._label_edit = QLineEdit()
        self._label_edit.setPlaceholderText("Підпис лінії (необов'язково)")
        form.addRow('Підпис:', self._label_edit)

        # --- Тип лінії ---
        self._line_type_combo = QComboBox()
        for key, label in LINE_TYPE_LABELS.items():
            self._line_type_combo.addItem(label, userData=key)
        form.addRow('Тип лінії:', self._line_type_combo)

        # --- Напрямок ---
        self._direction_combo = QComboBox()
        for key, label in DIRECTION_LABELS.items():
            self._direction_combo.addItem(label, userData=key)
        form.addRow('Напрямок:', self._direction_combo)

        # --- Надійність (strength) ---
        self._strength_combo = QComboBox()
        for key, label in LINK_STRENGTH_LABELS.items():
            self._strength_combo.addItem(label, userData=key)
        form.addRow('Надійність:', self._strength_combo)

        # --- Колір лінії ---
        self._link_color_btn = QPushButton()
        self._link_color_btn.setFixedWidth(100)
        self._link_color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._link_color_btn.setToolTip('Клік — вибрати колір лінії')
        self._link_color_btn.clicked.connect(self._on_pick_link_color)
        self._refresh_link_color_btn()
        form.addRow('Колір лінії:', self._link_color_btn)

        # --- Товщина лінії ---
        self._link_width_spin = QSpinBox()
        self._link_width_spin.setRange(1, 5)
        self._link_width_spin.setValue(2)
        form.addRow('Товщина:', self._link_width_spin)

        # --- Примітка ---
        self._note_edit = QTextEdit()
        self._note_edit.setPlaceholderText('Довільна примітка…')
        self._note_edit.setMaximumHeight(72)
        form.addRow('Примітка:', self._note_edit)

        root_layout.addLayout(form)

        # --- Кнопки ---
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Ok).setText('OK')
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText('Скасувати')
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root_layout.addWidget(buttons)

    # ------------------------------------------------------------------
    # Допоміжні методи для кнопки кольору
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Заповнення полів при редагуванні
    # ------------------------------------------------------------------

    def _populate_from_link(self, link: 'Link') -> None:
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

    # ------------------------------------------------------------------
    # Публічний API
    # ------------------------------------------------------------------

    def get_link_data(self) -> dict:
        """Повертає словник із даними форми."""
        return {
            'label': self._label_edit.text().strip(),
            'line_type': self._line_type_combo.currentData(),
            'direction': self._direction_combo.currentData(),
            'strength': self._strength_combo.currentData(),
            'color': self._link_color,
            'width': self._link_width_spin.value(),
            'note': self._note_edit.toPlainText().strip(),
        }


# ---------------------------------------------------------------------------
# Панель властивостей (праворуч)
# ---------------------------------------------------------------------------

class _NoteEdit(QTextEdit):
    """QTextEdit що сигналізує про завершення редагування при втраті фокусу."""
    editing_finished = pyqtSignal()

    def focusOutEvent(self, event) -> None:
        super().focusOutEvent(event)
        self.editing_finished.emit()


class PropertiesPanel(QWidget):
    """Бічна панель, що відображає властивості поточного виділеного елемента."""

    node_edit_requested = pyqtSignal(str)   # uuid вузла — відкрити повний діалог
    link_edit_requested = pyqtSignal(str)   # uuid зв'язку — відкрити повний діалог
    node_inline_changed = pyqtSignal(str, str, str)   # uuid, поле, нове_значення
    link_inline_changed = pyqtSignal(str, str, str)   # uuid, поле, нове_значення
    node_color_changed = pyqtSignal(str, str)          # uuid, new_color_hex

    # Індекси сторінок QStackedWidget
    _PAGE_EMPTY = 0
    _PAGE_MULTIPLE = 1
    _PAGE_NODE = 2
    _PAGE_LINK = 3

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setFixedWidth(240)
        self._current_node_uuid: str = ''
        self._current_link_uuid: str = ''
        self._updating: bool = False          # True під час програмного заповнення полів
        self._node_title_orig: str = ''       # значення до початку редагування
        self._node_note_orig: str = ''
        self._link_label_orig: str = ''
        self._build_ui()

    # ------------------------------------------------------------------
    # Побудова UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Заголовок панелі
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

        # Сторінка 0 — порожня
        empty_page = QWidget()
        empty_layout = QVBoxLayout(empty_page)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_lbl = QLabel('Виберіть вузол або зв\'язок,\nщоб переглянути властивості')
        empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_lbl.setWordWrap(True)
        empty_lbl.setStyleSheet('color: #999; font-size: 12px;')
        empty_layout.addWidget(empty_lbl)
        self._stack.addWidget(empty_page)  # індекс 0

        # Сторінка 1 — кілька виділених
        multi_page = QWidget()
        multi_layout = QVBoxLayout(multi_page)
        multi_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._multi_label = QLabel('Вибрано N елементів')
        self._multi_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._multi_label.setStyleSheet('color: #555; font-size: 12px;')
        multi_layout.addWidget(self._multi_label)
        self._stack.addWidget(multi_page)  # індекс 1

        # Сторінка 2 — вузол
        self._stack.addWidget(self._build_node_page())  # індекс 2

        # Сторінка 3 — зв'язок
        self._stack.addWidget(self._build_link_page())  # індекс 3

        self._stack.setCurrentIndex(self._PAGE_EMPTY)

    def _build_node_page(self) -> QScrollArea:
        """Будує сторінку властивостей вузла."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        form = QFormLayout(container)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(8)
        form.setContentsMargins(10, 10, 10, 10)

        # Мініатюра фото
        self._node_photo_label = QLabel()
        self._node_photo_label.setFixedSize(60, 60)
        self._node_photo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._node_photo_label.setStyleSheet(
            'border: 1px solid #ccc; border-radius: 4px; background: #f5f5f5;'
        )
        self._node_photo_label.hide()
        form.addRow('', self._node_photo_label)

        # Назва — редагується прямо в панелі
        self._node_title_edit = QLineEdit()
        self._node_title_edit.setPlaceholderText('Введіть назву…')
        self._node_title_edit.editingFinished.connect(self._on_title_committed)
        form.addRow('Назва:', self._node_title_edit)

        # Тип
        self._node_type_lbl = QLabel()
        form.addRow('Тип:', self._node_type_lbl)

        # Примітка — редагується прямо в панелі
        self._node_note_edit = _NoteEdit()
        self._node_note_edit.setFixedHeight(70)
        self._node_note_edit.setPlaceholderText('Примітка…')
        self._node_note_edit.editing_finished.connect(self._on_note_committed)
        form.addRow('Примітка:', self._node_note_edit)

        # Колір — кнопка для швидкої зміни (2 кліки без діалогу)
        self._node_color_btn = QPushButton()
        self._node_color_btn.setFixedWidth(100)
        self._node_color_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._node_color_btn.setToolTip('Клік — змінити колір вузла')
        self._node_color_btn.clicked.connect(self._on_node_color_btn_clicked)
        form.addRow('Колір:', self._node_color_btn)

        # Дата
        self._node_date_lbl = QLabel()
        form.addRow('Дата:', self._node_date_lbl)

        # UUID
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

        # Кнопка редагування
        self._node_edit_btn = QPushButton('Редагувати…')
        self._node_edit_btn.clicked.connect(self._on_node_edit_clicked)
        form.addRow('', self._node_edit_btn)

        scroll.setWidget(container)
        return scroll

    def _build_link_page(self) -> QScrollArea:
        """Будує сторінку властивостей зв'язку."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        form = QFormLayout(container)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        form.setSpacing(8)
        form.setContentsMargins(10, 10, 10, 10)

        # Підпис — редагується прямо в панелі
        self._link_label_edit = QLineEdit()
        self._link_label_edit.setPlaceholderText('Підпис зв\'язку…')
        self._link_label_edit.editingFinished.connect(self._on_link_label_committed)
        form.addRow('Підпис:', self._link_label_edit)

        # Тип лінії
        self._link_type_lbl = QLabel()
        form.addRow('Тип лінії:', self._link_type_lbl)

        # Напрямок
        self._link_dir_lbl = QLabel()
        form.addRow('Напрямок:', self._link_dir_lbl)

        # Примітка
        self._link_note_lbl = QLabel()
        self._link_note_lbl.setWordWrap(True)
        form.addRow('Примітка:', self._link_note_lbl)

        # UUID
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

        # Кнопка редагування
        self._link_edit_btn = QPushButton('Редагувати…')
        self._link_edit_btn.clicked.connect(self._on_link_edit_clicked)
        form.addRow('', self._link_edit_btn)

        scroll.setWidget(container)
        return scroll

    # ------------------------------------------------------------------
    # Слоти кнопок редагування
    # ------------------------------------------------------------------

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
        """Відкриває QColorDialog та надсилає сигнал зміни кольору вузла."""
        if not self._current_node_uuid:
            return
        current = self._node_color_btn.property('_color') or '#4A90D9'
        c = QColorDialog.getColor(QColor(current), self, 'Колір вузла')
        if c.isValid():
            self.node_color_changed.emit(self._current_node_uuid, c.name())

    # ------------------------------------------------------------------
    # Публічний API
    # ------------------------------------------------------------------

    def show_empty(self) -> None:
        """Показує порожню сторінку."""
        self._stack.setCurrentIndex(self._PAGE_EMPTY)

    def show_multiple(self, count: int) -> None:
        """Показує сторінку для множинного виділення."""
        self._multi_label.setText(f'Вибрано {count} елементів')
        self._stack.setCurrentIndex(self._PAGE_MULTIPLE)

    def show_node(self, node: 'Node') -> None:
        """Заповнює сторінку вузла та показує її."""
        self._current_node_uuid = node.uuid

        # Фото
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

        # Кнопка кольору
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

    def show_link(self, link: 'Link') -> None:
        """Заповнює сторінку зв'язку та показує її."""
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


# ---------------------------------------------------------------------------
# Панель пошуку
# ---------------------------------------------------------------------------

class SearchPanel(QWidget):
    """Горизонтальна панель для пошуку вузлів на схемі."""

    def __init__(self, canvas: 'DiagramCanvas', parent=None) -> None:
        super().__init__(parent)
        self._canvas = canvas
        self._results: list[str] = []   # uuid вузлів, що відповідають запиту
        self._result_idx: int = 0
        self._build_ui()

    # ------------------------------------------------------------------
    # Побудова UI
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Логіка пошуку
    # ------------------------------------------------------------------

    def _do_search(self) -> None:
        """Виконує пошук і виділяє знайдені вузли."""
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
            count = len(self._results)
            self._count_label.setText(f'Знайдено: {count}')
            self._select_result(0)
        else:
            self._count_label.setText('Нічого не знайдено')
            self._canvas.scene().clearSelection()

    def _select_result(self, idx: int) -> None:
        """Виділяє результат за індексом та центрує полотно на ньому."""
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
        """Очищає пошук, знімає виділення та приховує панель."""
        self._search_edit.clear()
        self._count_label.setText('')
        self._results = []
        self._result_idx = 0
        self._canvas.scene().clearSelection()
        # Сховати батьківський QDockWidget, якщо він є
        dock = self.parent()
        if isinstance(dock, QDockWidget):
            dock.hide()


# ---------------------------------------------------------------------------
# Панель фільтрації за типом
# ---------------------------------------------------------------------------

class FilterPanel(QWidget):
    """Панель для відображення/приховування вузлів за їх типом."""

    def __init__(self, canvas: 'DiagramCanvas', parent=None) -> None:
        super().__init__(parent)
        self._canvas = canvas
        self._checkboxes: dict[str, QCheckBox] = {}
        self._build_ui()

    # ------------------------------------------------------------------
    # Побудова UI
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # Заголовок
        title = QLabel('Фільтр за типом')
        title_font = QFont()
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # Чекбокси для кожного типу
        for key, label in NODE_TYPE_LABELS.items():
            cb = QCheckBox(label)
            cb.setChecked(True)
            cb.stateChanged.connect(self._on_filter_changed)
            self._checkboxes[key] = cb
            layout.addWidget(cb)

        # Кнопки «Показати всі» / «Сховати всі»
        btn_row = QHBoxLayout()
        show_all_btn = QPushButton('Показати всі')
        show_all_btn.clicked.connect(self._show_all)
        hide_all_btn = QPushButton('Сховати всі')
        hide_all_btn.clicked.connect(self._hide_all)
        btn_row.addWidget(show_all_btn)
        btn_row.addWidget(hide_all_btn)
        layout.addLayout(btn_row)

        layout.addStretch()

    # ------------------------------------------------------------------
    # Слоти
    # ------------------------------------------------------------------

    def _on_filter_changed(self) -> None:
        """Збирає відмічені типи та передає фільтр на полотно."""
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


# ---------------------------------------------------------------------------
# Панель візуального пошуку (P2.6)
# ---------------------------------------------------------------------------

class VisualSearchPanel(QWidget):
    """Структурований пошук по елементах схеми з фільтрами типу/strength/direction/дати."""

    def __init__(self, canvas: 'DiagramCanvas', parent=None) -> None:
        super().__init__(parent)
        self._canvas = canvas
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        title = QLabel('Візуальний пошук')
        f = QFont(); f.setBold(True)
        title.setFont(f)
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(5)

        # Текстовий пошук
        self._text_edit = QLineEdit()
        self._text_edit.setPlaceholderText('Текст у заголовку вузла…')
        form.addRow('Текст:', self._text_edit)

        # Тип вузла
        self._type_combo = QComboBox()
        self._type_combo.addItem('Всі типи', userData='')
        for key, label in NODE_TYPE_LABELS.items():
            self._type_combo.addItem(label, userData=key)
        form.addRow('Тип:', self._type_combo)

        # Надійність зв'язку
        self._strength_combo = QComboBox()
        self._strength_combo.addItem('Будь-яка', userData='')
        for key, label in LINK_STRENGTH_LABELS.items():
            self._strength_combo.addItem(label, userData=key)
        form.addRow('Надійність зв\'язку:', self._strength_combo)

        # Напрямок зв'язку
        self._direction_combo = QComboBox()
        self._direction_combo.addItem('Будь-який', userData='')
        for key, label in DIRECTION_LABELS.items():
            self._direction_combo.addItem(label, userData=key)
        form.addRow('Напрямок:', self._direction_combo)

        # Дата вузла (від / до)
        self._date_from = QLineEdit()
        self._date_from.setPlaceholderText('РРРР-ММ-ДД')
        self._date_to = QLineEdit()
        self._date_to.setPlaceholderText('РРРР-ММ-ДД')
        form.addRow('Дата від:', self._date_from)
        form.addRow('Дата до:', self._date_to)

        layout.addLayout(form)

        # Кнопки
        btn_row = QHBoxLayout()
        search_btn = QPushButton('Пошук')
        search_btn.clicked.connect(self._run_search)
        reset_btn = QPushButton('Скинути')
        reset_btn.clicked.connect(self._reset)
        btn_row.addWidget(search_btn)
        btn_row.addWidget(reset_btn)
        layout.addLayout(btn_row)

        # Результати
        self._results_label = QLabel('Результати:')
        layout.addWidget(self._results_label)

        self._results_list = QListWidget()
        self._results_list.itemClicked.connect(self._on_result_clicked)
        layout.addWidget(self._results_list)

    def _run_search(self) -> None:
        """Запускає пошук і відображає результати."""
        text = self._text_edit.text().strip().lower()
        node_type = self._type_combo.currentData()
        strength_filter = self._strength_combo.currentData()
        direction_filter = self._direction_combo.currentData()
        date_from = self._date_from.text().strip()
        date_to = self._date_to.text().strip()

        # Знаходимо вузли що задовольняють фільтрам
        matched_nodes: list[str] = []
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

        # Якщо є фільтри по зв'язках — звужуємо до вузлів з такими зв'язками
        if strength_filter or direction_filter:
            linked_nodes: set[str] = set()
            for lk in self._canvas.links.values():
                if strength_filter and getattr(lk, 'strength', '') != strength_filter:
                    continue
                if direction_filter and lk.direction != direction_filter:
                    continue
                linked_nodes.add(lk.source_uuid)
                linked_nodes.add(lk.target_uuid)
            matched_nodes = [u for u in matched_nodes if u in linked_nodes]

        # Відображаємо/ховаємо
        all_uuids = set(self._canvas.nodes.keys())
        matched_set = set(matched_nodes)
        for uid, it in self._canvas.node_items.items():
            it.setVisible(uid in matched_set)
        for uid, li in self._canvas.link_items.items():
            lk = self._canvas.links.get(uid)
            if lk:
                visible = lk.source_uuid in matched_set and lk.target_uuid in matched_set
                li.setVisible(visible)

        # Список результатів
        self._results_list.clear()
        for uid in matched_nodes:
            node = self._canvas.nodes[uid]
            item = QListWidgetItem(f"{node.title or '(без назви)'}  [{node.type}]")
            item.setData(Qt.ItemDataRole.UserRole, uid)
            self._results_list.addItem(item)
        self._results_label.setText(f'Результати: {len(matched_nodes)} знайдено')

    def _reset(self) -> None:
        """Скидає фільтри і відображає всі вузли."""
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
        """Центрує вигляд на вибраному вузлі."""
        uid = item.data(Qt.ItemDataRole.UserRole)
        node_it = self._canvas.node_items.get(uid)
        if node_it:
            self._canvas.centerOn(node_it)
            self._canvas.scene().clearSelection()
            node_it.setSelected(True)


# ---------------------------------------------------------------------------
# Головне вікно програми
# ---------------------------------------------------------------------------

class MainWindow(QMainWindow):
    """Головне вікно редактора зв'язкових схем."""

    def __init__(self) -> None:
        super().__init__()

        # Стек скасування/повтору операцій
        self.undo_stack = QUndoStack(self)

        # Полотно схеми
        self.canvas = DiagramCanvas(self.undo_stack, self)
        self.setCentralWidget(self.canvas)

        # Менеджер автозбереження
        self.autosave = AutosaveManager(self.canvas, self)

        self.setMinimumSize(1200, 800)
        self.setWindowTitle("Редактор зв'язкових схем")

        # Побудова UI
        self._create_panels()
        self._create_toolbar()
        self._create_menubar()
        self._connect_canvas_signals()

        # Рядок стану
        self.statusBar().showMessage('Готово', 2000)

        # Запуск автозбереження та перевірка наявного файлу відновлення
        self.autosave.start()
        self._check_autosave_on_startup()

    # ==================================================================
    # Побудова панелей та доків
    # ==================================================================

    def _create_panels(self) -> None:
        """Створює бічні панелі та прикріплює їх як QDockWidget."""

        # --- Права панель властивостей ---
        self.properties_panel = PropertiesPanel(self)
        props_dock = QDockWidget('Властивості', self)
        props_dock.setWidget(self.properties_panel)
        props_dock.setAllowedAreas(Qt.DockWidgetArea.RightDockWidgetArea)
        # Прибираємо кнопку закриття
        props_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, props_dock)

        # --- Нижня панель пошуку ---
        self.search_panel = SearchPanel(self.canvas, self)
        self._search_dock = QDockWidget('Пошук', self)
        self._search_dock.setWidget(self.search_panel)
        self._search_dock.setAllowedAreas(
            Qt.DockWidgetArea.BottomDockWidgetArea | Qt.DockWidgetArea.TopDockWidgetArea
        )
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._search_dock)
        self._search_dock.hide()

        # --- Нижня панель фільтрів ---
        self.filter_panel = FilterPanel(self.canvas, self)
        self._filter_dock = QDockWidget('Фільтр', self)
        self._filter_dock.setWidget(self.filter_panel)
        self._filter_dock.setAllowedAreas(
            Qt.DockWidgetArea.BottomDockWidgetArea |
            Qt.DockWidgetArea.LeftDockWidgetArea |
            Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._filter_dock)
        self._filter_dock.hide()

        # --- Панель візуального пошуку (P2.6) ---
        self.visual_search_panel = VisualSearchPanel(self.canvas, self)
        self._visual_search_dock = QDockWidget('Візуальний пошук', self)
        self._visual_search_dock.setWidget(self.visual_search_panel)
        self._visual_search_dock.setAllowedAreas(
            Qt.DockWidgetArea.BottomDockWidgetArea |
            Qt.DockWidgetArea.LeftDockWidgetArea |
            Qt.DockWidgetArea.RightDockWidgetArea
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._visual_search_dock)
        self._visual_search_dock.hide()

        # Мінімапа
        self._minimap_view = MinimapView(self.canvas._scene, self.canvas, self)
        self._minimap_dock = QDockWidget('Мінімапа', self)
        self._minimap_dock.setWidget(self._minimap_view)
        self._minimap_dock.setAllowedAreas(
            Qt.DockWidgetArea.RightDockWidgetArea |
            Qt.DockWidgetArea.LeftDockWidgetArea
        )
        self._minimap_dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable |
            QDockWidget.DockWidgetFeature.DockWidgetMovable
        )
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self._minimap_dock)
        self._minimap_dock.hide()

    # ==================================================================
    # Панель інструментів
    # ==================================================================

    def _create_toolbar(self) -> None:
        """Створює основну панель інструментів."""
        toolbar = QToolBar('Основний', self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Файлові операції
        act_new = QAction('Новий', self)
        act_new.setShortcut(QKeySequence.StandardKey.New)
        act_new.triggered.connect(self._action_new)
        toolbar.addAction(act_new)

        act_open = QAction('Відкрити', self)
        act_open.setShortcut(QKeySequence.StandardKey.Open)
        act_open.triggered.connect(self._action_open)
        toolbar.addAction(act_open)

        act_save = QAction('Зберегти', self)
        act_save.setShortcut(QKeySequence.StandardKey.Save)
        act_save.triggered.connect(self._action_save)
        toolbar.addAction(act_save)

        toolbar.addSeparator()

        # Додавання вузла
        act_add_node = QAction('Додати вузол', self)
        act_add_node.triggered.connect(self._action_add_node)
        toolbar.addAction(act_add_node)

        toolbar.addSeparator()

        # Інструменти: вибір / зв'язок (взаємовиключні)
        mode_group = QActionGroup(self)

        self._act_mode_select = QAction('Вибір', self)
        self._act_mode_select.setCheckable(True)
        self._act_mode_select.setChecked(True)
        self._act_mode_select.triggered.connect(self._action_set_mode_select)
        mode_group.addAction(self._act_mode_select)
        toolbar.addAction(self._act_mode_select)

        self._act_mode_link = QAction("Зв'язок", self)
        self._act_mode_link.setCheckable(True)
        self._act_mode_link.triggered.connect(self._action_set_mode_link)
        mode_group.addAction(self._act_mode_link)
        toolbar.addAction(self._act_mode_link)

        toolbar.addSeparator()

        # Shape Tools (ті ж mode_group — тільки один режим активний одночасно)
        self._act_mode_line = QAction('Лінія', self)
        self._act_mode_line.setCheckable(True)
        self._act_mode_line.triggered.connect(self._action_set_mode_line)
        mode_group.addAction(self._act_mode_line)
        toolbar.addAction(self._act_mode_line)

        self._act_mode_circle = QAction('Коло', self)
        self._act_mode_circle.setCheckable(True)
        self._act_mode_circle.triggered.connect(self._action_set_mode_circle)
        mode_group.addAction(self._act_mode_circle)
        toolbar.addAction(self._act_mode_circle)

        self._act_mode_rect = QAction('Прямокутник', self)
        self._act_mode_rect.setCheckable(True)
        self._act_mode_rect.triggered.connect(self._action_set_mode_rect)
        mode_group.addAction(self._act_mode_rect)
        toolbar.addAction(self._act_mode_rect)

        self._act_mode_text = QAction('Текст', self)
        self._act_mode_text.setCheckable(True)
        self._act_mode_text.triggered.connect(self._action_set_mode_text)
        mode_group.addAction(self._act_mode_text)
        toolbar.addAction(self._act_mode_text)

        toolbar.addSeparator()

        # Видалення
        act_delete = QAction('Видалити', self)
        act_delete.setShortcut(QKeySequence.StandardKey.Delete)
        act_delete.triggered.connect(self._action_delete)
        toolbar.addAction(act_delete)

        toolbar.addSeparator()

        # Масштаб
        act_zoom_in = QAction('Збільшити', self)
        act_zoom_in.triggered.connect(self.canvas.zoom_in)
        toolbar.addAction(act_zoom_in)

        act_zoom_out = QAction('Зменшити', self)
        act_zoom_out.triggered.connect(self.canvas.zoom_out)
        toolbar.addAction(act_zoom_out)

        act_fit = QAction('За розміром', self)
        act_fit.triggered.connect(self.canvas.fit_to_screen)
        toolbar.addAction(act_fit)

        # Сітка (перемикач)
        self._act_grid = QAction('Сітка', self)
        self._act_grid.setCheckable(True)
        self._act_grid.setChecked(self.canvas.get_grid_enabled())
        self._act_grid.triggered.connect(self.canvas.toggle_grid)
        toolbar.addAction(self._act_grid)

        toolbar.addSeparator()

        # Експорт
        act_png = QAction('PNG', self)
        act_png.triggered.connect(self._action_export_png)
        toolbar.addAction(act_png)

        act_pdf = QAction('PDF', self)
        act_pdf.triggered.connect(self._action_export_pdf)
        toolbar.addAction(act_pdf)

        toolbar.addSeparator()

        # Пошук
        act_search = QAction('Пошук', self)
        act_search.setShortcut(QKeySequence('Ctrl+F'))
        act_search.triggered.connect(self._action_toggle_search)
        toolbar.addAction(act_search)

    # ==================================================================
    # Меню
    # ==================================================================

    def _create_menubar(self) -> None:
        """Будує головне меню програми."""
        menubar = self.menuBar()

        # ---- Файл ----
        file_menu = menubar.addMenu('Файл')

        act_new = QAction('Новий', self)
        act_new.setShortcut(QKeySequence.StandardKey.New)
        act_new.triggered.connect(self._action_new)
        file_menu.addAction(act_new)

        act_open = QAction('Відкрити', self)
        act_open.setShortcut(QKeySequence.StandardKey.Open)
        act_open.triggered.connect(self._action_open)
        file_menu.addAction(act_open)

        act_save = QAction('Зберегти', self)
        act_save.setShortcut(QKeySequence.StandardKey.Save)
        act_save.triggered.connect(self._action_save)
        file_menu.addAction(act_save)

        act_save_as = QAction('Зберегти як…', self)
        act_save_as.setShortcut(QKeySequence('Ctrl+Shift+S'))
        act_save_as.triggered.connect(self._action_save_as)
        file_menu.addAction(act_save_as)

        file_menu.addSeparator()

        act_import_csv = QAction('Імпорт CSV', self)
        act_import_csv.triggered.connect(self._action_import_csv)
        file_menu.addAction(act_import_csv)

        file_menu.addSeparator()

        act_export_png = QAction('Експорт PNG', self)
        act_export_png.triggered.connect(self._action_export_png)
        file_menu.addAction(act_export_png)

        act_export_pdf = QAction('Експорт PDF', self)
        act_export_pdf.triggered.connect(self._action_export_pdf)
        file_menu.addAction(act_export_pdf)

        act_print_preview = QAction('Попередній перегляд друку…', self)
        act_print_preview.triggered.connect(self._action_print_preview)
        file_menu.addAction(act_print_preview)

        file_menu.addSeparator()

        act_quit = QAction('Вихід', self)
        act_quit.setShortcut(QKeySequence.StandardKey.Quit)
        act_quit.triggered.connect(self.close)
        file_menu.addAction(act_quit)

        # ---- Редагування ----
        edit_menu = menubar.addMenu('Редагування')

        act_undo = self.undo_stack.createUndoAction(self, 'Скасувати')
        act_undo.setShortcut(QKeySequence.StandardKey.Undo)
        edit_menu.addAction(act_undo)

        act_redo = self.undo_stack.createRedoAction(self, 'Повторити')
        act_redo.setShortcut(QKeySequence('Ctrl+Shift+Z'))
        edit_menu.addAction(act_redo)

        edit_menu.addSeparator()

        act_select_all = QAction('Вибрати все', self)
        act_select_all.setShortcut(QKeySequence.StandardKey.SelectAll)
        act_select_all.triggered.connect(self._action_select_all)
        edit_menu.addAction(act_select_all)

        act_delete = QAction('Видалити', self)
        act_delete.setShortcut(QKeySequence.StandardKey.Delete)
        act_delete.triggered.connect(self._action_delete)
        edit_menu.addAction(act_delete)

        act_duplicate = QAction('Дублювати', self)
        act_duplicate.setShortcut(QKeySequence('Ctrl+D'))
        act_duplicate.triggered.connect(self._action_duplicate)
        edit_menu.addAction(act_duplicate)

        act_deselect = QAction('Зняти виділення', self)
        act_deselect.setShortcut(QKeySequence('Escape'))
        act_deselect.triggered.connect(self._action_clear_selection)
        edit_menu.addAction(act_deselect)

        edit_menu.addSeparator()

        act_group = QAction('Згрупувати', self)
        act_group.setShortcut(QKeySequence('Ctrl+G'))
        act_group.triggered.connect(self._action_group)
        edit_menu.addAction(act_group)

        act_ungroup = QAction('Розгрупувати', self)
        act_ungroup.setShortcut(QKeySequence('Ctrl+Shift+G'))
        act_ungroup.triggered.connect(self._action_ungroup)
        edit_menu.addAction(act_ungroup)

        # ---- Вигляд ----
        view_menu = menubar.addMenu('Вигляд')

        act_zoom_in = QAction('Збільшити', self)
        act_zoom_in.setShortcut(QKeySequence('Ctrl++'))
        act_zoom_in.triggered.connect(self.canvas.zoom_in)
        view_menu.addAction(act_zoom_in)

        act_zoom_out = QAction('Зменшити', self)
        act_zoom_out.setShortcut(QKeySequence('Ctrl+-'))
        act_zoom_out.triggered.connect(self.canvas.zoom_out)
        view_menu.addAction(act_zoom_out)

        act_fit = QAction('За розміром', self)
        act_fit.setShortcut(QKeySequence('Ctrl+0'))
        act_fit.triggered.connect(self.canvas.fit_to_screen)
        view_menu.addAction(act_fit)

        view_menu.addSeparator()

        self._menu_act_grid = QAction('Сітка', self)
        self._menu_act_grid.setCheckable(True)
        self._menu_act_grid.setChecked(self.canvas.get_grid_enabled())
        self._menu_act_grid.triggered.connect(self.canvas.toggle_grid)
        view_menu.addAction(self._menu_act_grid)

        self._menu_act_snap = QAction("Прив'язка до сітки", self)
        self._menu_act_snap.setCheckable(True)
        self._menu_act_snap.setChecked(False)
        self._menu_act_snap.triggered.connect(self.canvas.toggle_snap_to_grid)
        view_menu.addAction(self._menu_act_snap)

        act_minimap = QAction('Мінімапа', self)
        act_minimap.setCheckable(True)
        act_minimap.triggered.connect(self._on_minimap_toggle)
        view_menu.addAction(act_minimap)

        view_menu.addSeparator()

        auto_layout_menu = view_menu.addMenu('Авто-розміщення')

        act_layout_grid = QAction('По сітці', self)
        act_layout_grid.triggered.connect(self.canvas.auto_layout_grid)
        auto_layout_menu.addAction(act_layout_grid)

        act_layout_radial = QAction('Радіально', self)
        act_layout_radial.triggered.connect(self.canvas.auto_layout_radial)
        auto_layout_menu.addAction(act_layout_radial)

        auto_layout_menu.addSeparator()

        act_layout_circular = QAction('Circular (i2)', self)
        act_layout_circular.triggered.connect(self.canvas.auto_layout_circular)
        auto_layout_menu.addAction(act_layout_circular)

        act_layout_hierarchy = QAction('Hierarchy (i2)', self)
        act_layout_hierarchy.triggered.connect(self.canvas.auto_layout_hierarchy)
        auto_layout_menu.addAction(act_layout_hierarchy)

        act_layout_peacock = QAction('Peacock (i2)', self)
        act_layout_peacock.triggered.connect(self.canvas.auto_layout_peacock)
        auto_layout_menu.addAction(act_layout_peacock)

        # ---- Інструменти ----
        tools_menu = menubar.addMenu('Інструменти')

        act_tool_select = QAction('Інструмент вибору', self)
        act_tool_select.triggered.connect(self._action_set_mode_select)
        tools_menu.addAction(act_tool_select)

        act_tool_link = QAction("Інструмент зв'язку", self)
        act_tool_link.triggered.connect(self._action_set_mode_link)
        tools_menu.addAction(act_tool_link)

        tools_menu.addSeparator()

        act_search_tool = QAction('Пошук', self)
        act_search_tool.setShortcut(QKeySequence('Ctrl+F'))
        act_search_tool.triggered.connect(self._action_toggle_search)
        tools_menu.addAction(act_search_tool)

        act_filter_tool = QAction('Фільтр', self)
        act_filter_tool.triggered.connect(self._action_filter)
        tools_menu.addAction(act_filter_tool)

        act_visual_search = QAction('Візуальний пошук…', self)
        act_visual_search.setShortcut(QKeySequence('Ctrl+Alt+F'))
        act_visual_search.triggered.connect(
            lambda: self._visual_search_dock.setVisible(not self._visual_search_dock.isVisible())
        )
        tools_menu.addAction(act_visual_search)

        tools_menu.addSeparator()

        act_find_path = QAction('Знайти шлях між вузлами…', self)
        act_find_path.setShortcut(QKeySequence('Ctrl+Shift+F'))
        act_find_path.triggered.connect(self._action_find_path)
        tools_menu.addAction(act_find_path)

        act_show_all = QAction('Показати всі елементи', self)
        act_show_all.triggered.connect(self.canvas.show_all_nodes)
        tools_menu.addAction(act_show_all)

        # ---- Довідка ----
        help_menu = menubar.addMenu('Довідка')

        act_about = QAction('Про програму', self)
        act_about.triggered.connect(self._action_about)
        help_menu.addAction(act_about)

    # ==================================================================
    # Підключення сигналів полотна
    # ==================================================================

    def _connect_canvas_signals(self) -> None:
        """Підключає всі сигнали DiagramCanvas до відповідних обробників."""

        # Вибір елементів
        self.canvas.node_selected.connect(self._on_node_selected)
        self.canvas.link_selected.connect(self._on_link_selected)
        self.canvas.selection_changed.connect(self._on_selection_changed)

        # Стан змін та заголовок вікна
        self.canvas.modified_changed.connect(lambda _: self._update_window_title())

        # Запити на відкриття діалогів
        self.canvas.link_creation_requested.connect(self._on_link_creation_requested)
        self.canvas.node_edit_requested.connect(self._on_edit_node)
        self.canvas.link_edit_requested.connect(self._on_edit_link)

        # Рядок стану
        self.canvas.status_message.connect(
            lambda msg: self.statusBar().showMessage(msg, 3000)
        )

        # Подвійний клік по порожньому місцю — додати вузол
        self.canvas.empty_space_double_clicked.connect(self._on_add_node_at)

        # Панель властивостей → запити редагування
        self.properties_panel.node_edit_requested.connect(self._on_edit_node)
        self.properties_panel.link_edit_requested.connect(self._on_edit_link)

        # Inline редагування в панелі
        self.properties_panel.node_inline_changed.connect(self._on_node_inline_changed)
        self.properties_panel.link_inline_changed.connect(self._on_link_inline_changed)
        self.properties_panel.node_color_changed.connect(self._on_node_color_from_panel)

        # Оновлення панелі після Undo/Redo
        self.canvas.undo_stack.indexChanged.connect(self._refresh_properties)

    # ------------------------------------------------------------------
    # Слоти сигналів вибору
    # ------------------------------------------------------------------

    def _on_node_selected(self, node) -> None:
        if node:
            self.properties_panel.show_node(node)
        else:
            self.properties_panel.show_empty()

    def _on_link_selected(self, link) -> None:
        if link:
            self.properties_panel.show_link(link)
        else:
            self.properties_panel.show_empty()

    def _on_selection_changed(self, items: list) -> None:
        if len(items) > 1:
            self.properties_panel.show_multiple(len(items))

    # ==================================================================
    # Обробники дій файлового меню
    # ==================================================================

    def _action_new(self) -> None:
        """Створює новий порожній документ."""
        if not self.check_unsaved_changes():
            return
        self.canvas.clear_scene()
        self._update_window_title()

    def _action_open(self) -> None:
        """Відкриває JSON-файл схеми."""
        if not self.check_unsaved_changes():
            return
        filepath, _ = QFileDialog.getOpenFileName(
            self, 'Відкрити схему', '', 'JSON схеми (*.json)'
        )
        if not filepath:
            return
        success, msg = load_from_json(self.canvas, filepath)
        if success:
            self.statusBar().showMessage('Файл відкрито', 3000)
            self._update_window_title()
            if msg:
                QMessageBox.warning(self, 'Увага', msg)
        else:
            QMessageBox.critical(self, 'Помилка', f'Не вдалося відкрити файл:\n{msg}')

    def _action_save(self) -> None:
        """Зберігає поточний документ. Якщо ще не прив'язаний до файлу — «Зберегти як»."""
        if self.canvas.current_file:
            if save_to_json(self.canvas, self.canvas.current_file):
                self.statusBar().showMessage('Файл збережено', 3000)
                self._update_window_title()
            else:
                QMessageBox.critical(self, 'Помилка', 'Не вдалося зберегти файл.')
        else:
            self._action_save_as()

    def _action_save_as(self) -> None:
        """Зберігає документ під новим іменем."""
        filepath, _ = QFileDialog.getSaveFileName(
            self, 'Зберегти схему як', '', 'JSON схеми (*.json)'
        )
        if not filepath:
            return
        if not filepath.endswith('.json'):
            filepath += '.json'
        if save_to_json(self.canvas, filepath):
            self.statusBar().showMessage('Файл збережено', 3000)
            self._update_window_title()
        else:
            QMessageBox.critical(self, 'Помилка', 'Не вдалося зберегти файл.')

    def _action_import_csv(self) -> None:
        """Імпортує вузли та зв'язки з CSV-файлу."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, 'Імпорт CSV', '', 'CSV файли (*.csv)'
        )
        if not filepath:
            return
        n_nodes, n_links, err = import_from_csv(self.canvas, filepath)
        msg = f'Імпортовано вузлів: {n_nodes}, зв\'язків: {n_links}'
        if err:
            msg += f'\n\nПопередження: {err}'
        QMessageBox.information(self, 'Імпорт CSV', msg)

    def _action_export_png(self) -> None:
        """Експортує схему у PNG-зображення."""
        filepath, _ = QFileDialog.getSaveFileName(
            self, 'Експорт PNG', '', 'PNG зображення (*.png)'
        )
        if not filepath:
            return
        if not filepath.endswith('.png'):
            filepath += '.png'
        if self.canvas.export_png(filepath):
            self.statusBar().showMessage('Експорт PNG завершено', 3000)
        else:
            QMessageBox.critical(self, 'Помилка', 'Не вдалося експортувати PNG.')

    def _action_export_pdf(self) -> None:
        """Експортує схему у PDF-документ."""
        filepath, _ = QFileDialog.getSaveFileName(
            self, 'Експорт PDF', '', 'PDF документи (*.pdf)'
        )
        if not filepath:
            return
        if not filepath.endswith('.pdf'):
            filepath += '.pdf'
        if self.canvas.export_pdf(filepath):
            self.statusBar().showMessage('Експорт PDF завершено', 3000)
        else:
            QMessageBox.warning(
                self, 'Увага',
                'Експорт PDF поки недоступний.\nСпробуйте експортувати як PNG.'
            )

    # ==================================================================
    # Обробники дій редагування
    # ==================================================================

    def _action_add_node(self) -> None:
        """Відкриває діалог та додає вузол у центр видимої ділянки полотна."""
        center = self.canvas.mapToScene(self.canvas.viewport().rect().center())
        self._open_add_node_dialog(center)

    def _on_add_node_at(self, scene_pos: QPointF) -> None:
        """Відкриває діалог та додає вузол у вказану позицію (подвійний клік)."""
        self._open_add_node_dialog(scene_pos)

    def _open_add_node_dialog(self, scene_pos: QPointF) -> None:
        """Спільна логіка відкриття діалогу для додавання нового вузла."""
        dialog = NodeDialog(parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        data = dialog.get_node_data()
        if not data:
            return
        node = Node(
            type=data['type'],
            title=data['title'],
            note=data['note'],
            date=data['date'],
            x=scene_pos.x() - NODE_W / 2,
            y=scene_pos.y() - NODE_H / 2,
            color=data['color'],
            photo_base64=data['photo_base64'],
        )
        self.canvas.undo_stack.push(AddNodeCommand(self.canvas, node))
        self.statusBar().showMessage('Вузол додано', 2000)

    def _on_link_creation_requested(self, source_uuid: str, target_uuid: str) -> None:
        """Відкриває діалог і створює зв'язок між двома вузлами."""
        dialog = LinkDialog(parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        data = dialog.get_link_data()
        link = Link(
            source_uuid=source_uuid,
            target_uuid=target_uuid,
            label=data['label'],
            line_type=data['line_type'],
            direction=data['direction'],
            note=data['note'],
            color=data['color'],
            width=data['width'],
            strength=data.get('strength', 'Confirmed'),
        )
        self.canvas.undo_stack.push(AddLinkCommand(self.canvas, link))
        self.statusBar().showMessage("Зв'язок додано", 2000)

    def _on_edit_node(self, node_uuid: str) -> None:
        """Відкриває діалог редагування вузла та застосовує зміни через undo-команду."""
        node = self.canvas.nodes.get(node_uuid)
        if not node:
            return
        dialog = NodeDialog(parent=self, node=node)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        new_data = dialog.get_node_data()
        if not new_data:
            return
        old_data = {k: getattr(node, k) for k in ['type', 'title', 'note', 'date', 'color', 'photo_base64', 'frame_enabled', 'frame_color', 'frame_width']}
        self.canvas.undo_stack.push(EditNodeCommand(self.canvas, node_uuid, old_data, new_data))

    def _on_edit_link(self, link_uuid: str) -> None:
        """Відкриває діалог редагування зв'язку та застосовує зміни через undo-команду."""
        link = self.canvas.links.get(link_uuid)
        if not link:
            return
        dialog = LinkDialog(parent=self, link=link)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        new_data = dialog.get_link_data()
        old_data = {k: getattr(link, k) for k in ['label', 'line_type', 'direction', 'note', 'color', 'width', 'strength']}
        self.canvas.undo_stack.push(EditLinkCommand(self.canvas, link_uuid, old_data, new_data))

    def _action_delete(self) -> None:
        """Видаляє виділені вузли, зв'язки та/або геометричні фігури."""
        selected = self.canvas.scene().selectedItems()

        sel_nodes = [
            self.canvas.nodes[i.node.uuid]
            for i in selected
            if isinstance(i, NodeItem) and i.node.uuid in self.canvas.nodes
        ]
        sel_links = [
            self.canvas.links[i.link.uuid]
            for i in selected
            if isinstance(i, LinkItem) and i.link.uuid in self.canvas.links
        ]
        sel_shapes = [
            i for i in selected
            if not isinstance(i, (NodeItem, LinkItem))
        ]

        # Збираємо зв'язки, пов'язані з вузлами, що видаляються
        node_uuids = {n.uuid for n in sel_nodes}
        related_links = [
            lk for lk in self.canvas.links.values()
            if lk.source_uuid in node_uuids or lk.target_uuid in node_uuids
        ]

        # Дедуплікація зв'язків
        all_links_map: dict[str, Link] = {lk.uuid: lk for lk in sel_links + related_links}
        all_links = list(all_links_map.values())

        if sel_nodes:
            self.canvas.undo_stack.push(DeleteNodesCommand(self.canvas, sel_nodes, all_links))
        elif all_links:
            self.canvas.undo_stack.push(DeleteLinksCommand(self.canvas, all_links))

        if sel_shapes:
            self.canvas.undo_stack.push(DeleteShapeCommand(self.canvas, sel_shapes))
            self.canvas.mark_modified()

    def _action_duplicate(self) -> None:
        """Дублює виділені вузли зі зміщенням 40px."""
        selected = [i for i in self.canvas.scene().selectedItems() if isinstance(i, NodeItem)]
        for item in selected:
            new_node = copy.deepcopy(item.node)
            new_node.uuid = str(uuid.uuid4())
            new_node.x += 40
            new_node.y += 40
            # Скидаємо часові мітки нового вузла
            now = datetime.now().isoformat()
            new_node.created_at = now
            new_node.updated_at = now
            self.canvas.undo_stack.push(DuplicateNodeCommand(self.canvas, new_node))

    def _action_select_all(self) -> None:
        """Виділяє всі елементи сцени."""
        for item in self.canvas.scene().items():
            item.setSelected(True)

    def _action_clear_selection(self) -> None:
        """Знімає виділення з усіх елементів."""
        self.canvas.scene().clearSelection()

    # ==================================================================
    # Обробники дій вигляду та інструментів
    # ==================================================================

    def _on_node_inline_changed(self, uuid: str, field: str, value: str) -> None:
        """Застосовує inline-зміну поля вузла через undo-стек."""
        node = self.canvas.nodes.get(uuid)
        if node is None:
            return
        old_data = {field: getattr(node, field, '')}
        new_data = {field: value}
        self.canvas.undo_stack.push(
            EditNodeCommand(self.canvas, uuid, old_data, new_data, f'Редагувати {field}')
        )

    def _on_link_inline_changed(self, uuid: str, field: str, value: str) -> None:
        """Застосовує inline-зміну поля зв'язку через undo-стек."""
        link = self.canvas.links.get(uuid)
        if link is None:
            return
        old_data = {field: getattr(link, field, '')}
        new_data = {field: value}
        self.canvas.undo_stack.push(
            EditLinkCommand(self.canvas, uuid, old_data, new_data, f'Редагувати {field}')
        )

    def _refresh_properties(self) -> None:
        """Оновлює панель після Undo/Redo."""
        uuid = self.properties_panel._current_node_uuid
        if uuid and uuid in self.canvas.nodes:
            self.properties_panel.show_node(self.canvas.nodes[uuid])
            return
        uuid = self.properties_panel._current_link_uuid
        if uuid and uuid in self.canvas.links:
            self.properties_panel.show_link(self.canvas.links[uuid])

    def _action_set_mode_select(self) -> None:
        self.canvas.set_mode('select')
        self._act_mode_select.setChecked(True)

    def _action_set_mode_link(self) -> None:
        self.canvas.set_mode('link')
        self._act_mode_link.setChecked(True)

    def _action_set_mode_line(self) -> None:
        self.canvas.set_mode('line')
        self._act_mode_line.setChecked(True)

    def _action_set_mode_circle(self) -> None:
        self.canvas.set_mode('circle')
        self._act_mode_circle.setChecked(True)

    def _action_set_mode_rect(self) -> None:
        self.canvas.set_mode('rect')
        self._act_mode_rect.setChecked(True)

    def _action_set_mode_text(self) -> None:
        self.canvas.set_mode('text')
        self._act_mode_text.setChecked(True)

    def _action_toggle_search(self) -> None:
        """Перемикає видимість панелі пошуку."""
        self._search_dock.setVisible(not self._search_dock.isVisible())

    def _action_filter(self) -> None:
        """Перемикає видимість панелі фільтрів."""
        self._filter_dock.setVisible(not self._filter_dock.isVisible())

    def _action_find_path(self) -> None:
        """Діалог пошуку найкоротшого шляху між двома вузлами."""
        node_titles = {uid: (n.title or uid[:8]) for uid, n in self.canvas.nodes.items()}
        if len(node_titles) < 2:
            QMessageBox.information(self, 'Find Path', 'Потрібно щонайменше 2 вузли.')
            return

        items = [f"{t}  [{uid[:8]}]" for uid, t in node_titles.items()]
        uid_list = list(node_titles.keys())

        start_label, ok1 = QInputDialog.getItem(
            self, 'Find Path', 'Початковий вузол:', items, 0, False
        )
        if not ok1:
            return
        end_label, ok2 = QInputDialog.getItem(
            self, 'Find Path', 'Кінцевий вузол:', items, 1, False
        )
        if not ok2:
            return

        start_uuid = uid_list[items.index(start_label)]
        end_uuid = uid_list[items.index(end_label)]

        path = self.canvas.find_path_between(start_uuid, end_uuid)
        if path:
            self.canvas.highlight_path(path)
        else:
            QMessageBox.information(self, 'Find Path', 'Шлях між вузлами не знайдено.')

    def _on_minimap_toggle(self, checked: bool) -> None:
        self._minimap_dock.setVisible(checked)
        if checked:
            self._minimap_view._do_fit()

    def _action_group(self) -> None:
        self.canvas.group_selected()

    def _action_ungroup(self) -> None:
        self.canvas.ungroup_selected()

    def _action_print_preview(self) -> None:
        """Відкриває попередній перегляд друку."""
        printer = QPrinter()
        printer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
        printer.setPageOrientation(QPageLayout.Orientation.Landscape)
        preview = QPrintPreviewDialog(printer, self)
        preview.paintRequested.connect(self._render_for_print)
        preview.exec()

    def _render_for_print(self, printer: QPrinter) -> None:
        painter = QPainter(printer)
        rect = self.canvas.scene().itemsBoundingRect()
        self.canvas.scene().render(painter, source=rect)
        painter.end()

    def _on_node_color_from_panel(self, uuid: str, color: str) -> None:
        """Обробляє зміну кольору вузла з бічної панелі через undo-стек."""
        node = self.canvas.nodes.get(uuid)
        if node is None:
            return
        old_color = node.color
        if old_color == color:
            return
        self.canvas.undo_stack.push(ColorNodeCommand(self.canvas, uuid, old_color, color))
        if uuid in self.canvas.nodes:
            self.properties_panel.show_node(self.canvas.nodes[uuid])

    def _action_about(self) -> None:
        QMessageBox.about(
            self,
            'Про програму',
            'Редактор зв\'язкових схем\nВерсія 1.0\n\nІнструмент для побудови схем взаємодій.',
        )

    # ==================================================================
    # Допоміжні методи
    # ==================================================================

    def _update_window_title(self) -> None:
        """Оновлює заголовок вікна з ім'ям файлу та маркером незбережених змін."""
        base = "Редактор зв'язкових схем"
        if self.canvas.current_file:
            base += f' — {Path(self.canvas.current_file).name}'
        if self.canvas.is_modified:
            base += ' *'
        self.setWindowTitle(base)

    def check_unsaved_changes(self) -> bool:
        """Пропонує зберегти зміни. Повертає True, якщо можна продовжувати."""
        if not self.canvas.is_modified:
            return True
        btn = QMessageBox.question(
            self,
            'Незбережені зміни',
            'Є незбережені зміни. Зберегти перед продовженням?',
            QMessageBox.StandardButton.Save |
            QMessageBox.StandardButton.Discard |
            QMessageBox.StandardButton.Cancel,
        )
        if btn == QMessageBox.StandardButton.Save:
            self._action_save()
            return True
        if btn == QMessageBox.StandardButton.Discard:
            return True
        # Cancel
        return False

    def _check_autosave_on_startup(self) -> None:
        """Перевіряє наявність файлу автозбереження та пропонує відновити схему."""
        path = self.autosave.check_for_autosave()
        if not path:
            return
        btn = QMessageBox.question(
            self,
            'Відновлення',
            'Знайдено автозбереження. Відновити?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if btn == QMessageBox.StandardButton.Yes:
            load_from_json(self.canvas, path)
            self._update_window_title()
        # При відмові — не видаляємо файл автозбереження без явної згоди користувача

    # ==================================================================
    # Закриття вікна
    # ==================================================================

    def closeEvent(self, event) -> None:
        """Перевіряє незбережені зміни та зупиняє автозбереження перед виходом."""
        if self.check_unsaved_changes():
            self.autosave.stop()
            self.autosave.clear_autosave()
            event.accept()
        else:
            event.ignore()


# ---------------------------------------------------------------------------
# Точка входу
# ---------------------------------------------------------------------------

def main() -> None:
    """Запускає програму."""
    app = QApplication(sys.argv)
    app.setApplicationName("Редактор зв'язкових схем")
    app.setApplicationVersion('1.0')

    available_styles = QStyleFactory.keys()
    if 'macOS' in available_styles:
        app.setStyle('macOS')
    else:
        app.setStyle('Fusion')

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
