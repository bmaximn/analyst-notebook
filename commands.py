from __future__ import annotations
import copy
from typing import TYPE_CHECKING

from PyQt6.QtGui import QUndoCommand

from models import Node, Link

if TYPE_CHECKING:
    from canvas import DiagramCanvas
    from PyQt6.QtWidgets import QGraphicsItem


class AddNodeCommand(QUndoCommand):
    def __init__(self, canvas: DiagramCanvas, node: Node, text: str = 'Додати вузол') -> None:
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
    def __init__(self, canvas: DiagramCanvas, nodes: list, links: list,
                 text: str = 'Видалити елементи') -> None:
        super().__init__(text)
        self.canvas = canvas
        self.nodes = [copy.deepcopy(n) for n in nodes]
        self.links = [copy.deepcopy(lk) for lk in links]

    def redo(self) -> None:
        for lk in self.links:
            self.canvas.remove_link(lk.uuid)
        for node in self.nodes:
            self.canvas.remove_node(node.uuid)
        self.canvas.mark_modified()

    def undo(self) -> None:
        for node in self.nodes:
            self.canvas.add_node(node)
        for lk in self.links:
            self.canvas.add_link(lk)
        self.canvas.mark_modified()


class EditNodeCommand(QUndoCommand):
    def __init__(self, canvas: DiagramCanvas, node_uuid: str, old_data: dict, new_data: dict,
                 text: str = 'Редагувати вузол') -> None:
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
    def __init__(self, canvas: DiagramCanvas, node_uuid: str, old_color: str, new_color: str,
                 text: str = 'Змінити колір') -> None:
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
    def __init__(self, canvas: DiagramCanvas, new_node: Node,
                 text: str = 'Дублювати вузол') -> None:
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
    def __init__(self, canvas: DiagramCanvas, link: Link,
                 text: str = "Додати зв'язок") -> None:
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
    def __init__(self, canvas: DiagramCanvas, links: list,
                 text: str = "Видалити зв'язки") -> None:
        super().__init__(text)
        self.canvas = canvas
        self.links = [copy.deepcopy(lk) for lk in links]

    def redo(self) -> None:
        for lk in self.links:
            self.canvas.remove_link(lk.uuid)
        self.canvas.mark_modified()

    def undo(self) -> None:
        for lk in self.links:
            self.canvas.add_link(lk)
        self.canvas.mark_modified()


class EditLinkCommand(QUndoCommand):
    def __init__(self, canvas: DiagramCanvas, link_uuid: str, old_data: dict, new_data: dict,
                 text: str = "Редагувати зв'язок") -> None:
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
    def __init__(self, canvas: DiagramCanvas, item: QGraphicsItem) -> None:
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
    def __init__(self, canvas: DiagramCanvas, items: list) -> None:
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
