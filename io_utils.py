from __future__ import annotations
import os
import json
import csv
from datetime import datetime
from pathlib import Path
from typing import Optional, TYPE_CHECKING

from PyQt6.QtCore import Qt, QRectF, QPointF, QLineF
from PyQt6.QtGui import QPen, QBrush, QColor, QFont
from PyQt6.QtWidgets import (
    QGraphicsItem, QGraphicsLineItem, QGraphicsEllipseItem,
    QGraphicsRectItem, QGraphicsSimpleTextItem,
)

from models import Node, Link
from items import GroupItem
from constants import (
    SCHEMA_VERSION, NODE_TYPES, LINK_STRENGTH_LABELS, DIRECTION_LABELS,
)

if TYPE_CHECKING:
    from canvas import DiagramCanvas


def _serialize_shape(item) -> Optional[dict]:
    pen = item.pen() if hasattr(item, 'pen') else None
    pen_data: dict = {}
    if pen is not None:
        pen_data = {
            'color': pen.color().name(),
            'width': pen.widthF(),
            'style': int(pen.style()),
        }
    brush_data: dict = {}
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
        return {**base, 'type': 'text', 'text': item.text(), 'font_size': item.font().pointSize()}
    return None


def _deserialize_shape(d: dict) -> Optional[object]:
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
    try:
        original_created_at: Optional[str] = None
        if os.path.isfile(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as fh:
                    existing = json.load(fh)
                    original_created_at = existing.get('created_at')
            except Exception:
                pass

        now = datetime.now().isoformat()

        shapes_data = []
        for sh in canvas._shape_items:
            s = _serialize_shape(sh)
            if s:
                shapes_data.append(s)

        groups_data = []
        for grp in canvas._group_items:
            member_uuids = []
            for m in grp.members():
                from items import NodeItem
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

        canvas.is_modified = False
        canvas.current_file = filepath
        canvas.modified_changed.emit(False)
        return True
    except Exception:
        return False


def load_from_json(canvas: DiagramCanvas, filepath: str) -> tuple:
    try:
        with open(filepath, 'r', encoding='utf-8') as fh:
            data = json.load(fh)

        if not isinstance(data, dict) or 'nodes' not in data or 'links' not in data:
            return False, 'Невірний формат файлу: відсутні ключі "nodes" або "links".'

        canvas.clear_scene()

        for node_dict in data.get('nodes', []):
            try:
                node = Node.from_dict(node_dict)
                canvas.add_node(node)
            except Exception as exc:
                import sys as _sys
                print(f'[load_from_json] пропущено вузол: {exc}', file=_sys.stderr)

        skipped_links: list = []
        for link_dict in data.get('links', []):
            try:
                link = Link.from_dict(link_dict)
                if link.source_uuid not in canvas.nodes:
                    skipped_links.append(f'{link.uuid} (невідомий source {link.source_uuid})')
                    continue
                if link.target_uuid not in canvas.nodes:
                    skipped_links.append(f'{link.uuid} (невідомий target {link.target_uuid})')
                    continue
                canvas.add_link(link)
            except Exception as exc:
                skipped_links.append(f'помилка: {exc}')

        for shape_dict in data.get('shapes', []):
            item = _deserialize_shape(shape_dict)
            if item is not None:
                canvas._scene.addItem(item)
                canvas._shape_items.append(item)

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

        viewport_data = data.get('viewport', {})
        if viewport_data:
            canvas.set_viewport_state(viewport_data)

        if 'grid_enabled' in data and not data['grid_enabled']:
            canvas._grid_enabled = False
            canvas.viewport().update()
        canvas._snap_to_grid = bool(data.get('snap_to_grid', False))

        canvas.is_modified = False
        canvas.current_file = filepath
        canvas.modified_changed.emit(False)

        warning = ''
        if skipped_links:
            warning = (
                f'Пропущено {len(skipped_links)} зв\'язок(ів) '
                f'через відсутні вузли:\n' + '\n'.join(skipped_links)
            )
        return True, warning

    except Exception as exc:
        return False, str(exc)


def import_from_csv(
    canvas: DiagramCanvas,
    nodes_filepath: str,
    delimiter: str = ',',
    node_map: Optional[dict] = None,
    link_map: Optional[dict] = None,
) -> tuple:
    nodes_path = Path(nodes_filepath)
    links_path = nodes_path.parent / 'links.csv'

    if not nodes_path.is_file():
        return 0, 0, f'Файл не знайдено: {nodes_filepath}'

    if node_map is None:
        node_map = {f: f for f in ('id', 'title', 'type', 'note', 'date', 'color', 'x', 'y')}
    if link_map is None:
        link_map = {f: f for f in (
            'source_id', 'target_id', 'label', 'direction', 'strength',
            'date_time', 'source_reference', 'weighting_value', 'note',
        )}

    def gcol(row: dict, field: str, mapping: dict) -> str:
        col = mapping.get(field)
        return row.get(col, '').strip() if col else ''

    id_to_uuid: dict = {}
    nodes_count = 0
    errors: list = []
    auto_col = 0
    auto_row = 0
    auto_cols_per_row = 8
    auto_step = 150

    try:
        with open(nodes_path, newline='', encoding='utf-8-sig') as fh:
            reader = csv.DictReader(fh, delimiter=delimiter)
            if reader.fieldnames is None:
                return 0, 0, 'nodes.csv: порожній файл або відсутні заголовки.'
            id_col = node_map.get('id', 'id')
            title_col = node_map.get('title', 'title')
            required = {c for c in [id_col, title_col] if c}
            missing = required - set(reader.fieldnames)
            if missing:
                return 0, 0, f'nodes.csv: відсутні стовпці: {", ".join(sorted(missing))}'
            for row_num, row in enumerate(reader, start=2):
                row_id = gcol(row, 'id', node_map)
                if not row_id:
                    errors.append(f'nodes.csv рядок {row_num}: порожній id — пропущено')
                    continue
                raw_type = gcol(row, 'type', node_map)
                node_type = raw_type if raw_type in NODE_TYPES else 'Document'
                raw_color = gcol(row, 'color', node_map)
                node_color = raw_color if raw_color else None
                raw_x = gcol(row, 'x', node_map)
                raw_y = gcol(row, 'y', node_map)
                if raw_x and raw_y:
                    try:
                        node_x, node_y = float(raw_x), float(raw_y)
                    except ValueError:
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
                    title=gcol(row, 'title', node_map),
                    note=gcol(row, 'note', node_map),
                    date=gcol(row, 'date', node_map),
                    x=node_x, y=node_y, color=node_color,
                )
                id_to_uuid[row_id] = node.uuid
                canvas.add_node(node)
                nodes_count += 1
    except Exception as exc:
        return 0, 0, f'Помилка читання nodes.csv: {exc}'

    links_count = 0
    if links_path.is_file():
        try:
            with open(links_path, newline='', encoding='utf-8-sig') as fh:
                reader = csv.DictReader(fh, delimiter=delimiter)
                if reader.fieldnames is not None:
                    src_col = link_map.get('source_id', 'source_id')
                    tgt_col = link_map.get('target_id', 'target_id')
                    required_link = {c for c in [src_col, tgt_col] if c}
                    missing_link = required_link - set(reader.fieldnames)
                    if missing_link:
                        errors.append(
                            f'links.csv: відсутні стовпці '
                            f'{", ".join(sorted(missing_link))} — зв\'язки не завантажено'
                        )
                    else:
                        for row_num, row in enumerate(reader, start=2):
                            src_id = gcol(row, 'source_id', link_map)
                            tgt_id = gcol(row, 'target_id', link_map)
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
                            raw_strength = gcol(row, 'strength', link_map)
                            strength = raw_strength if raw_strength in LINK_STRENGTH_LABELS else 'Confirmed'
                            raw_dir = gcol(row, 'direction', link_map)
                            direction = raw_dir if raw_dir in DIRECTION_LABELS else 'source_to_target'
                            raw_w = gcol(row, 'weighting_value', link_map)
                            try:
                                weighting_value = float(raw_w) if raw_w else 0.0
                            except ValueError:
                                weighting_value = 0.0
                            link = Link(
                                source_uuid=id_to_uuid[src_id],
                                target_uuid=id_to_uuid[tgt_id],
                                label=gcol(row, 'label', link_map),
                                direction=direction,
                                note=gcol(row, 'note', link_map),
                                strength=strength,
                                date_time=gcol(row, 'date_time', link_map),
                                source_reference=gcol(row, 'source_reference', link_map),
                                weighting_value=weighting_value,
                            )
                            canvas.add_link(link)
                            links_count += 1
        except Exception as exc:
            errors.append(f'Помилка читання links.csv: {exc}')

    canvas.mark_modified()
    error_string = '\n'.join(errors) if errors else ''
    return nodes_count, links_count, error_string
