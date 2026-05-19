from pathlib import Path

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
