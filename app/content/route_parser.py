"""Извлекает GPS-координаты маршрута из markdown-файлов.

Поддерживает два формата:
1. Frontmatter: waypoints: [{name, lat, lng, description}]
2. Markdown-строки: - **Name** | 43.123, 16.456 | описание
"""

import re
from pathlib import Path

import frontmatter

from app.content.models import Waypoint

# Строка вида: - **Harbour Name** | 43.508, 16.440 | описание
# Также без bold: - Harbour Name | 43.508, 16.440 | описание
WAYPOINT_LINE = re.compile(
    r"^-\s+\*{0,2}(.+?)\*{0,2}\s*\|\s*"  # имя (с/без bold)
    r"(-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)"  # lat, lng
    r"(?:\s*\|\s*(.*))?$"                  # описание (опционально)
)


def _parse_frontmatter_waypoints(data: dict) -> list[Waypoint]:
    """Извлекает waypoints из YAML frontmatter."""
    raw = data.get("waypoints", [])
    if not isinstance(raw, list):
        return []

    result = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        try:
            result.append(Waypoint(
                name=str(item.get("name", "")),
                lat=float(item["lat"]),
                lng=float(item["lng"]),
                description=str(item.get("description", "")),
            ))
        except (KeyError, ValueError, TypeError):
            continue
    return result


def _parse_markdown_waypoints(text: str) -> list[Waypoint]:
    """Ищет координаты в строках markdown."""
    result = []
    for line in text.splitlines():
        match = WAYPOINT_LINE.match(line.strip())
        if not match:
            continue
        result.append(Waypoint(
            name=match.group(1).strip(),
            lat=float(match.group(2)),
            lng=float(match.group(3)),
            description=(match.group(4) or "").strip(),
        ))
    return result


def extract_waypoints(filepath: Path) -> list[Waypoint]:
    """Извлекает список waypoints из файла. Возвращает пустой список если координат нет."""
    raw_text = filepath.read_text(encoding="utf-8")
    post = frontmatter.loads(raw_text)

    # Сначала пробуем frontmatter, затем markdown
    waypoints = _parse_frontmatter_waypoints(post.metadata)
    if waypoints:
        return waypoints

    return _parse_markdown_waypoints(post.content)
