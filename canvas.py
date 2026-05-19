from __future__ import annotations
import copy
import uuid
import math
from collections import deque
from typing import Optional, TYPE_CHECKING

from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsItem, QInputDialog,
    QGraphicsLineItem, QGraphicsEllipseItem, QGraphicsRectItem,
    QGraphicsSimpleTextItem,
)
from PyQt6.QtCore import Qt, QRectF, QPointF, QSizeF, QLineF, pyqtSignal
from PyQt6.QtGui import (
    QPainter, QPen, QBrush, QColor, QImage, QPdfWriter,
    QPageSize, QPageLayout, QUndoStack, QFont,
)

from models import Node, Link
from items import NodeItem, LinkItem, GroupItem
from commands import (
    AddNodeCommand, DeleteNodesCommand, EditNodeCommand, ColorNodeCommand,
    DuplicateNodeCommand, AddLinkCommand, DeleteLinksCommand, EditLinkCommand,
    AddShapeCommand, DeleteShapeCommand,
)
from constants import NODE_W, NODE_H, NODE_TYPE_LABELS, LINK_STRENGTH_LABELS, DIRECTION_LABELS


class DiagramCanvas(QGraphicsView):
    """Основне полотно схеми зв'язків."""

    node_selected = pyqtSignal(object)
    link_selected = pyqtSignal(object)
    selection_changed = pyqtSignal(list)
    modified_changed = pyqtSignal(bool)
    link_creation_requested = pyqtSignal(str, str)
    node_edit_requested = pyqtSignal(str)
    link_edit_requested = pyqtSignal(str)
    status_message = pyqtSignal(str)
    empty_space_double_clicked = pyqtSignal(QPointF)

    def __init__(self, undo_stack: QUndoStack, parent=None) -> None:
        super().__init__(parent)

        self.nodes: dict[str, Node] = {}
        self.links: dict[str, Link] = {}
        self.node_items: dict[str, NodeItem] = {}
        self.link_items: dict[str, LinkItem] = {}
        self._shape_items: list = []
        self._group_items: list = []

        self.is_modified: bool = False
        self.current_file: Optional[str] = None

        self._mode: str = 'select'
        self._link_source_uuid: Optional[str] = None
        self._shape_start: Optional[QPointF] = None
        self._shape_preview: Optional[QGraphicsItem] = None

        self._grid_enabled: bool = True
        self._snap_to_grid: bool = False
        self._space_pressed: bool = False
        self._pan_start: Optional[QPointF] = None

        self.undo_stack = undo_stack

        self._scene = QGraphicsScene(self)
        self._scene.setSceneRect(QRectF(-10000, -10000, 20000, 20000))
        self.setScene(self._scene)

        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setViewportUpdateMode(QGraphicsView.ViewportUpdateMode.FullViewportUpdate)
        self.setBackgroundBrush(QBrush(QColor('white')))
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

        self._scene.selectionChanged.connect(self._on_selection_changed)

    # ------------------------------------------------------------------
    # Nodes
    # ------------------------------------------------------------------

    def add_node(self, node: Node) -> NodeItem:
        self.nodes[node.uuid] = node
        item = NodeItem(node)
        item._canvas = self
        self._scene.addItem(item)
        item.setPos(node.x, node.y)
        item.position_changed.connect(self._on_node_moved)
        item.edit_requested.connect(self.node_edit_requested)
        item.delete_requested.connect(self._on_delete_node_requested)
        item.duplicate_requested.connect(self._on_duplicate_node_requested)
        item.color_change_requested.connect(self._on_color_change_requested)
        self.node_items[node.uuid] = item
        return item

    def remove_node(self, node_uuid: str) -> None:
        if node_uuid in self.node_items:
            self._scene.removeItem(self.node_items[node_uuid])
            del self.node_items[node_uuid]
        if node_uuid in self.nodes:
            del self.nodes[node_uuid]

    # ------------------------------------------------------------------
    # Links
    # ------------------------------------------------------------------

    def add_link(self, link: Link) -> LinkItem:
        self.links[link.uuid] = link
        source_item = self.node_items[link.source_uuid]
        target_item = self.node_items[link.target_uuid]
        link_item = LinkItem(link, source_item, target_item)
        self._scene.addItem(link_item)
        link_item.edit_requested.connect(self.link_edit_requested)
        link_item.delete_requested.connect(self._on_delete_link_requested)
        self.link_items[link.uuid] = link_item
        return link_item

    def remove_link(self, link_uuid: str) -> None:
        if link_uuid in self.link_items:
            self._scene.removeItem(self.link_items[link_uuid])
            del self.link_items[link_uuid]
        if link_uuid in self.links:
            del self.links[link_uuid]

    # ------------------------------------------------------------------
    # Lookups
    # ------------------------------------------------------------------

    def get_node_item(self, node_uuid: str) -> Optional[NodeItem]:
        return self.node_items.get(node_uuid)

    def get_link_item(self, link_uuid: str) -> Optional[LinkItem]:
        return self.link_items.get(link_uuid)

    # ------------------------------------------------------------------
    # Scene management
    # ------------------------------------------------------------------

    def clear_scene(self) -> None:
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

    def mark_modified(self) -> None:
        self.is_modified = True
        self.modified_changed.emit(True)

    # ------------------------------------------------------------------
    # View
    # ------------------------------------------------------------------

    def fit_to_screen(self) -> None:
        if self.nodes:
            self.fitInView(
                self._scene.itemsBoundingRect().adjusted(-50, -50, 50, 50),
                Qt.AspectRatioMode.KeepAspectRatio,
            )
        else:
            self.resetTransform()

    def set_mode(self, mode: str) -> None:
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
        self._grid_enabled = not self._grid_enabled
        self.viewport().update()

    def get_grid_enabled(self) -> bool:
        return self._grid_enabled

    def toggle_snap_to_grid(self) -> None:
        self._snap_to_grid = not self._snap_to_grid

    def get_snap_to_grid(self) -> bool:
        return self._snap_to_grid

    # ------------------------------------------------------------------
    # Auto-layouts
    # ------------------------------------------------------------------

    def auto_layout_grid(self) -> None:
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
        nodes = list(self.nodes.values())
        if not nodes:
            return
        adj: dict[str, list[str]] = {n.uuid: [] for n in nodes}
        for lk in self.links.values():
            adj[lk.source_uuid].append(lk.target_uuid)
            adj[lk.target_uuid].append(lk.source_uuid)
        root = max(adj, key=lambda u: len(adj[u]))
        level: dict[str, int] = {root: 0}
        queue: deque[str] = deque([root])
        while queue:
            cur = queue.popleft()
            for nb in adj[cur]:
                if nb not in level:
                    level[nb] = level[cur] + 1
                    queue.append(nb)
        max_lvl = max(level.values(), default=0)
        for n in nodes:
            if n.uuid not in level:
                max_lvl += 1
                level[n.uuid] = max_lvl
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
        nodes = list(self.nodes.values())
        if not nodes:
            return
        adj: dict[str, list[str]] = {n.uuid: [] for n in nodes}
        for lk in self.links.values():
            adj[lk.source_uuid].append(lk.target_uuid)
            adj[lk.target_uuid].append(lk.source_uuid)
        hub = max(adj, key=lambda u: len(adj[u]))
        cx, cy = 500, 400
        hub_node = self.nodes[hub]
        hub_node.x, hub_node.y = cx, cy
        hub_it = self.node_items.get(hub)
        if hub_it:
            hub_it.setPos(cx, cy)
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
    # Groups
    # ------------------------------------------------------------------

    def group_selected(self) -> Optional[GroupItem]:
        items = [it for it in self._scene.selectedItems() if isinstance(it, NodeItem)]
        if len(items) < 2:
            self.status_message.emit('Виберіть 2 або більше вузлів для групування')
            return None
        label, ok = QInputDialog.getText(None, 'Назва групи', "Введіть назву (необов'язково):")
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
    # Connectivity filters
    # ------------------------------------------------------------------

    def show_only_connected(self, node_uuid: str) -> None:
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
        for it in self.node_items.values():
            it.setVisible(True)
        for li in self.link_items.values():
            li.setVisible(True)
        self.status_message.emit('Усі елементи відображено')

    # ------------------------------------------------------------------
    # Path finding
    # ------------------------------------------------------------------

    def find_path_between(self, start_uuid: str, end_uuid: str) -> list:
        if start_uuid not in self.nodes or end_uuid not in self.nodes:
            return []
        if start_uuid == end_uuid:
            return [start_uuid]
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
        if not path_uuids:
            self.status_message.emit('Шлях не знайдено')
            return
        path_set = set(path_uuids)
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
    # Background rendering
    # ------------------------------------------------------------------

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        painter.fillRect(rect, QColor('white'))
        if not self._grid_enabled:
            return
        step = 30
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
    # Zoom
    # ------------------------------------------------------------------

    def wheelEvent(self, event) -> None:
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        current_scale = self.transform().m11()
        if factor > 1 and current_scale > 5:
            return
        if factor < 1 and current_scale < 0.1:
            return
        self.scale(factor, factor)

    def zoom_in(self) -> None:
        self.scale(1.2, 1.2)

    def zoom_out(self) -> None:
        self.scale(1 / 1.2, 1 / 1.2)

    # ------------------------------------------------------------------
    # Keyboard / mouse
    # ------------------------------------------------------------------

    def keyPressEvent(self, event) -> None:
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
        if event.key() == Qt.Key.Key_Space:
            self._space_pressed = False
            self._pan_start = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            if self._mode == 'select':
                self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        else:
            super().keyReleaseEvent(event)

    def mousePressEvent(self, event) -> None:
        is_pan_trigger = (
            self._space_pressed
            or event.button() == Qt.MouseButton.MiddleButton
        )
        if is_pan_trigger:
            self._pan_start = event.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            self.setDragMode(QGraphicsView.DragMode.NoDrag)
            return

        if self._mode == 'link' and event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(event.pos())
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
                else:
                    preview = QGraphicsRectItem(QRectF(scene_pos, QSizeF(0, 0)))
                    preview.setPen(pen)
                    preview.setBrush(QBrush(QColor(100, 150, 255, 50)))
                preview.setZValue(-0.5)
                self._shape_preview = preview
                self._scene.addItem(preview)
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
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
        if (
            self._mode == 'select'
            and event.button() == Qt.MouseButton.LeftButton
        ):
            item = self.itemAt(event.pos())
            if item is None:
                scene_pos = self.mapToScene(event.pos())
                self.empty_space_double_clicked.emit(scene_pos)
                return
        super().mouseDoubleClickEvent(event)

    # ------------------------------------------------------------------
    # Selection
    # ------------------------------------------------------------------

    def _on_selection_changed(self) -> None:
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
    # Node event handlers
    # ------------------------------------------------------------------

    def _on_node_moved(self, node_uuid: str) -> None:
        for link_uuid, link in self.links.items():
            if link.source_uuid == node_uuid or link.target_uuid == node_uuid:
                if link_uuid in self.link_items:
                    self.link_items[link_uuid].update_position()

    def _on_delete_node_requested(self, node_uuid: str) -> None:
        node = self.nodes.get(node_uuid)
        if node is None:
            return
        related_links = [
            lk for lk in self.links.values()
            if lk.source_uuid == node_uuid or lk.target_uuid == node_uuid
        ]
        self.undo_stack.push(DeleteNodesCommand(self, [node], related_links))

    def _on_duplicate_node_requested(self, node_uuid: str) -> None:
        original = self.nodes.get(node_uuid)
        if original is None:
            return
        new_node = copy.deepcopy(original)
        new_node.uuid = str(uuid.uuid4())
        new_node.x += 40
        new_node.y += 40
        self.undo_stack.push(DuplicateNodeCommand(self, new_node))

    def _on_color_change_requested(self, node_uuid: str, new_color: str) -> None:
        node = self.nodes.get(node_uuid)
        if node is None:
            return
        old_color = node.color
        self.undo_stack.push(ColorNodeCommand(self, node_uuid, old_color, new_color))

    # ------------------------------------------------------------------
    # Link event handlers
    # ------------------------------------------------------------------

    def _on_delete_link_requested(self, link_uuid: str) -> None:
        link = self.links.get(link_uuid)
        if link is None:
            return
        self.undo_stack.push(DeleteLinksCommand(self, [link]))

    # ------------------------------------------------------------------
    # Viewport state
    # ------------------------------------------------------------------

    def get_viewport_state(self) -> dict:
        center = self.mapToScene(self.viewport().rect().center())
        return {
            'center_x': center.x(),
            'center_y': center.y(),
            'zoom': self.transform().m11(),
        }

    def set_viewport_state(self, state: dict) -> None:
        self.resetTransform()
        zoom = state.get('zoom', 1.0)
        self.scale(zoom, zoom)
        self.centerOn(
            QPointF(state.get('center_x', 0.0), state.get('center_y', 0.0))
        )

    # ------------------------------------------------------------------
    # Type filter
    # ------------------------------------------------------------------

    def set_type_filter(self, visible_types: list) -> None:
        for node_uuid, item in self.node_items.items():
            item.setVisible(item.node.type in visible_types)
        for link_uuid, item in self.link_items.items():
            link = self.links.get(link_uuid)
            if link is None:
                item.setVisible(False)
                continue
            src_visible = (
                self.node_items[link.source_uuid].isVisible()
                if link.source_uuid in self.node_items else False
            )
            tgt_visible = (
                self.node_items[link.target_uuid].isVisible()
                if link.target_uuid in self.node_items else False
            )
            item.setVisible(src_visible and tgt_visible)

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_png(self, filepath: str) -> bool:
        rect = self._scene.itemsBoundingRect().adjusted(-20, -20, 20, 20)
        if rect.width() <= 0 or rect.height() <= 0:
            return False
        image = QImage(int(rect.width()), int(rect.height()), QImage.Format.Format_RGB32)
        image.fill(QColor('white'))
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._scene.render(painter, QRectF(image.rect()), rect)
        painter.end()
        return image.save(filepath, 'PNG')

    def export_pdf(self, filepath: str) -> bool:
        try:
            scene_rect = self._scene.itemsBoundingRect().adjusted(-20, -20, 20, 20)
            if scene_rect.width() <= 0 or scene_rect.height() <= 0:
                return False
            writer = QPdfWriter(filepath)
            writer.setPageSize(QPageSize(QPageSize.PageSizeId.A4))
            writer.setPageOrientation(QPageLayout.Orientation.Landscape)
            writer.setResolution(150)
            painter = QPainter(writer)
            if not painter.isActive():
                return False
            page_rect = QRectF(0, 0, writer.width(), writer.height())
            self._scene.render(painter, page_rect, scene_rect, Qt.AspectRatioMode.KeepAspectRatio)
            painter.end()
            return True
        except Exception as e:
            print(f'[PDF Export Error] {e}')
            return False


class MinimapView(QGraphicsView):
    """Мінімапа: зменшений вид сцени з позначкою поточного viewport."""

    def __init__(self, scene: QGraphicsScene, main_view: DiagramCanvas, parent=None) -> None:
        super().__init__(scene, parent)
        self._main_view = main_view
        self.setFixedSize(240, 170)
        self.setInteractive(False)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setStyleSheet('border: 1px solid #bbb; background: #f8f8f8;')

        main_view.horizontalScrollBar().valueChanged.connect(self._refresh)
        main_view.verticalScrollBar().valueChanged.connect(self._refresh)

        from PyQt6.QtCore import QTimer
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
        super().drawForeground(painter, rect)
        visible = self._main_view.mapToScene(
            self._main_view.viewport().rect()
        ).boundingRect()
        pen = QPen(QColor('#E74C3C'), 2)
        pen.setCosmetic(True)
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor(231, 76, 60, 35)))
        painter.drawRect(visible)
