from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional

from constants import NODE_DEFAULT_COLORS


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

    def to_dict(self) -> dict:
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
    def from_dict(cls, d: dict) -> Node:
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
        self.updated_at = datetime.now().isoformat()


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

    def to_dict(self) -> dict:
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
    def from_dict(cls, d: dict) -> Link:
        raw_line_type = d.get('line_type', 'solid_arrow')
        strength = d.get('strength', 'Confirmed')
        if 'strength' not in d:
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
        self.updated_at = datetime.now().isoformat()
