"""Сборщик контента: читает Obsidian-vault и собирает JSON-бандл для фронтенда.

Основной процесс:
1. Читает _app.yaml — конфигурация секций и файлов
2. Парсит каждый markdown-файл из конфига
3. Извлекает waypoints из файлов маршрута (секция route)
4. Собирает ContentBundle и сохраняет в app/static/content.json
"""

import hashlib
import json
from pathlib import Path

import yaml

from app.content.models import ContentBundle, Route, Section, TripConfig
from app.content.parser import parse_markdown_file
from app.content.route_parser import extract_waypoints

# Секции, в которых ищем координаты маршрута
ROUTE_SECTION_ID = "route"


def _load_app_config(vault_path: Path) -> dict:
    """Читает _app.yaml из vault."""
    config_file = vault_path / "_app.yaml"
    if not config_file.exists():
        raise FileNotFoundError(f"Не найден _app.yaml в {vault_path}")
    return yaml.safe_load(config_file.read_text(encoding="utf-8"))


def _find_markdown_file(vault_path: Path, name: str) -> Path | None:
    """Ищет markdown-файл по имени (без расширения)."""
    candidate = vault_path / f"{name}.md"
    if candidate.exists():
        return candidate
    return None


def _build_sections(vault_path: Path, sections_config: list[dict]) -> tuple[list[Section], Route]:
    """Собирает секции и маршрут из конфигурации."""
    sections = []
    all_waypoints = []

    for section_cfg in sections_config:
        pages = []
        file_entries = section_cfg.get("files", [])

        for entry in file_entries:
            # Поддержка двух форматов:
            # 1. Строка: "Route plan"
            # 2. Словарь: {file: "Route plan", template: "route_plan"}
            if isinstance(entry, dict):
                file_name = entry.get("file", "")
                template = entry.get("template", "")
            else:
                file_name = entry
                template = ""

            filepath = _find_markdown_file(vault_path, file_name)
            if filepath is None:
                print(f"  [!] Файл не найден: {file_name}.md — пропущен")
                continue

            page = parse_markdown_file(filepath, template=template)
            pages.append(page)

            # Из файлов маршрутной секции извлекаем координаты
            if section_cfg.get("id") == ROUTE_SECTION_ID:
                waypoints = extract_waypoints(filepath)
                all_waypoints.extend(waypoints)

        section = Section(
            id=section_cfg["id"],
            title=section_cfg["title"],
            icon=section_cfg.get("icon", ""),
            tab=section_cfg.get("tab", ""),
            pages=pages,
        )
        sections.append(section)

    return sections, Route(waypoints=all_waypoints)


def _compute_hash(bundle: ContentBundle) -> str:
    """Вычисляет хеш контента для инвалидации кеша на фронтенде."""
    # Хешируем JSON без мета-полей (hash и built_at)
    data = bundle.model_dump(exclude={"content_hash", "built_at"})
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


def build_content(vault_path: str | Path) -> ContentBundle:
    """Главная функция: собирает ContentBundle из vault."""
    vault = Path(vault_path)
    if not vault.is_dir():
        raise FileNotFoundError(f"Vault не найден: {vault}")

    config = _load_app_config(vault)

    trip = TripConfig(**config.get("trip", {}))
    sections, route = _build_sections(vault, config.get("sections", []))

    bundle = ContentBundle(
        trip=trip,
        sections=sections,
        route=route,
    )
    # Хеш вычисляем после сборки и вставляем в финальный бандл
    content_hash = _compute_hash(bundle)
    bundle = bundle.model_copy(update={"content_hash": content_hash})

    return bundle


def write_content_json(bundle: ContentBundle, output_dir: str | Path) -> Path:
    """Сериализует бандл в JSON и записывает в файл."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    output_file = output / "content.json"

    data = bundle.model_dump()
    output_file.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_file
