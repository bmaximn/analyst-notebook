from __future__ import annotations
import base64
import math
from typing import Optional, TYPE_CHECKING

from PyQt6.QtWidgets import (
    QGraphicsObject, QGraphicsItem, QGraphicsRectItem,
    QMenu, QColorDialog, QStyle,
)
from PyQt6.QtCore import Qt, QRectF, QPointF, QLineF, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QPixmap, QImage, QFont,
    QPainterPath, QPainterPathStroker, QPolygonF,
)

from models import Node, Link
from constants import NODE_W, NODE_H, NODE_TYPE_LABELS, NODE_ICONS

if TYPE_CHECKING:
    from canvas import DiagramCanvas


class NodeItem(QGraphicsObject):
    """Графічний елемент вузла на сцені."""

    position_changed = pyqtSignal(str)
    edit_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)
    duplicate_requested = pyqtSignal(str)
    color_change_requested = pyqtSignal(str, str)

    def __init__(self, node: Node, parent=None):
        super().__init__(parent)
        self.node = node
        self._pixmap: Optional[QPixmap] = None
        self._load_photo_pixmap()
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges, True)
        self.setPos(node.x, node.y)

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, NODE_W, NODE_H)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        rect = QRectF(0, 0, NODE_W, NODE_H)
        painter.setBrush(QBrush(QColor('#ffffff')))
        if selected:
            painter.setPen(QPen(QColor('#2196F3'), 3))
        else:
            painter.setPen(QPen(QColor(self.node.color), 2))
        painter.drawRoundedRect(rect, 8, 8)

        if getattr(self.node, 'frame_enabled', False) and not selected:
            fw = getattr(self.node, 'frame_width', 3)
            fc = getattr(self.node, 'frame_color', '#FF0000')
            frame_pen = QPen(QColor(fc), fw)
            painter.setPen(frame_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(rect.adjusted(fw / 2, fw / 2, -fw / 2, -fw / 2), 8, 8)

        top_area_h = 40
        top_area_rect = QRectF(0, 0, NODE_W, top_area_h)
        if self._pixmap is not None and not self._pixmap.isNull():
            thumb_w, thumb_h = 36, 36
            thumb_x = (NODE_W - thumb_w) / 2
            thumb_y = (top_area_h - thumb_h) / 2
            painter.drawPixmap(int(thumb_x), int(thumb_y), self._pixmap)
        else:
            icon_font = QFont()
            icon_font.setPointSize(20)
            painter.setFont(icon_font)
            painter.setPen(QPen(QColor('#333333')))
            icon_text = NODE_ICONS.get(self.node.type, '?')
            painter.drawText(top_area_rect, Qt.AlignmentFlag.AlignCenter, icon_text)

        title_rect = QRectF(5, top_area_h, NODE_W - 10, NODE_H - top_area_h - 18)
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(9)
        painter.setFont(title_font)
        painter.setPen(QPen(QColor('#111111')))
        fm = painter.fontMetrics()
        elided_title = fm.elidedText(
            self.node.title, Qt.TextElideMode.ElideRight, int(title_rect.width())
        )
        painter.drawText(title_rect, Qt.AlignmentFlag.AlignCenter, elided_title)

        type_rect = QRectF(0, NODE_H - 18, NODE_W, 18)
        type_font = QFont()
        type_font.setPointSize(8)
        painter.setFont(type_font)
        painter.setPen(QPen(QColor('#888888')))
        type_label = NODE_TYPE_LABELS.get(self.node.type, self.node.type)
        painter.drawText(type_rect, Qt.AlignmentFlag.AlignCenter, type_label)

    def itemChange(self, change, value):
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

    def update_from_node(self):
        self.prepareGeometryChange()
        self._load_photo_pixmap()
        self.update()

    def contextMenuEvent(self, event):
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

    def mouseDoubleClickEvent(self, event):
        self.edit_requested.emit(self.node.uuid)
        super().mouseDoubleClickEvent(event)

    def _load_photo_pixmap(self):
        if not self.node.photo_base64:
            self._pixmap = None
            return
        try:
            raw_bytes = base64.b64decode(self.node.photo_base64)
            image = QImage()
            loaded = image.loadFromData(raw_bytes)
            if not loaded or image.isNull():
                self._pixmap = None
                return
            pixmap = QPixmap.fromImage(image)
            self._pixmap = pixmap.scaled(
                36, 36,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        except Exception:
            self._pixmap = None


class LinkItem(QGraphicsObject):
    """Графічний елемент зв'язку між двома вузлами."""

    edit_requested = pyqtSignal(str)
    delete_requested = pyqtSignal(str)

    def __init__(self, link: Link, source_item: NodeItem, target_item: NodeItem, parent=None):
        super().__init__(parent)
        self.link = link
        self.source_item = source_item
        self.target_item = target_item
        self._line = QLineF()
        self.setZValue(-1)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.update_position()

    @staticmethod
    def _intersect_node_rect(line: QLineF, node_pos: QPointF) -> QPointF:
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
        self.update()

    def boundingRect(self) -> QRectF:
        pad = 20.0
        return QRectF(
            min(self._line.x1(), self._line.x2()) - pad,
            min(self._line.y1(), self._line.y2()) - pad,
            abs(self._line.dx()) + 2 * pad,
            abs(self._line.dy()) + 2 * pad,
        )

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        path.moveTo(self._line.p1())
        path.lineTo(self._line.p2())
        stroker = QPainterPathStroker()
        stroker.setWidth(10)
        return stroker.createStroke(path)

    def paint(self, painter: QPainter, option, widget=None):
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        selected = bool(option.state & QStyle.StateFlag.State_Selected)
        base_color = QColor(getattr(self.link, 'color', '#555555'))
        line_color = QColor('#2196F3') if selected else base_color
        lw = getattr(self.link, 'width', 2)
        line_type = self.link.line_type
        strength = getattr(self.link, 'strength', 'Confirmed')
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
        direction = self.link.direction
        angle_to_target = self._line.angle()
        angle_to_source = self._line.angle() + 180.0
        if direction == 'source_to_target':
            self._draw_arrow(painter, pen, self._line.p2(), angle_to_target)
        elif direction == 'target_to_source':
            self._draw_arrow(painter, pen, self._line.p1(), angle_to_source)
        elif direction == 'bidirectional':
            self._draw_arrow(painter, pen, self._line.p2(), angle_to_target)
            self._draw_arrow(painter, pen, self._line.p1(), angle_to_source)
        if self.link.label:
            self._draw_label(painter)

    def _draw_double_line(self, painter: QPainter, pen: QPen):
        length = self._line.length()
        if length < 1:
            return
        dx = self._line.dx() / length
        dy = self._line.dy() / length
        perp_x = -dy
        perp_y = dx
        offset = 3.0
        painter.setPen(pen)
        p1a = QPointF(self._line.x1() + perp_x * offset, self._line.y1() + perp_y * offset)
        p2a = QPointF(self._line.x2() + perp_x * offset, self._line.y2() + perp_y * offset)
        painter.drawLine(p1a, p2a)
        p1b = QPointF(self._line.x1() - perp_x * offset, self._line.y1() - perp_y * offset)
        p2b = QPointF(self._line.x2() - perp_x * offset, self._line.y2() - perp_y * offset)
        painter.drawLine(p1b, p2b)

    def _draw_arrow(self, painter: QPainter, pen: QPen, tip: QPointF, angle_degrees: float):
        arrow_size = 10.0
        angle_rad = math.radians(angle_degrees)
        wing_angle = math.radians(25)
        left_x = tip.x() - arrow_size * math.cos(angle_rad - wing_angle)
        left_y = tip.y() + arrow_size * math.sin(angle_rad - wing_angle)
        right_x = tip.x() - arrow_size * math.cos(angle_rad + wing_angle)
        right_y = tip.y() + arrow_size * math.sin(angle_rad + wing_angle)
        arrow_polygon = QPolygonF([tip, QPointF(left_x, left_y), QPointF(right_x, right_y)])
        painter.setPen(QPen(pen.color(), 1))
        painter.setBrush(QBrush(pen.color()))
        painter.drawPolygon(arrow_polygon)

    def _draw_label(self, painter: QPainter):
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
        painter.setPen(QPen(QColor('#cccccc'), 1))
        painter.setBrush(QBrush(QColor('#ffffff')))
        painter.drawRoundedRect(bg_rect, 3, 3)
        painter.setPen(QPen(QColor('#222222')))
        painter.drawText(bg_rect, Qt.AlignmentFlag.AlignCenter, self.link.label)

    def contextMenuEvent(self, event):
        menu = QMenu()
        action_edit = menu.addAction('Редагувати')
        action_delete = menu.addAction('Видалити')
        chosen = menu.exec(event.screenPos())
        if chosen == action_edit:
            self.edit_requested.emit(self.link.uuid)
        elif chosen == action_delete:
            self.delete_requested.emit(self.link.uuid)

    def mouseDoubleClickEvent(self, event):
        self.edit_requested.emit(self.link.uuid)
        super().mouseDoubleClickEvent(event)


class GroupItem(QGraphicsRectItem):
    """Напівпрозорий прямокутний контейнер навколо групи вузлів."""

    def __init__(self, member_items: list, label: str = '', parent=None):
        self._member_items: list = list(member_items)
        self._label: str = label
        pad = 20
        if member_items:
            xs = [it.pos().x() for it in member_items]
            ys = [it.pos().y() for it in member_items]
            x0 = min(xs) - pad
            y0 = min(ys) - pad - 22
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
