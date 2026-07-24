"""Парсер Obsidian-markdown в HTML с поддержкой wiki-ссылок, таблиц, чекбоксов."""

import re
from pathlib import Path

import frontmatter
import markdown

from app.content.models import ContentPage
from app.content.structured_parsers import extract_structured_data

# Расширения markdown: таблицы, блоки кода, перенос строк
MD_EXTENSIONS = ["tables", "fenced_code", "nl2br"]

# Wiki-ссылка: [[Note Name]] или [[Note Name|Display Text]]
WIKILINK_PATTERN = re.compile(r"\[\[([^\]|]+?)(?:\|([^\]]+?))?\]\]")


def _slugify(name: str) -> str:
    """Превращает имя заметки в URL-якорь: 'Safety briefing' -> 'safety-briefing'."""
    return re.sub(r"[^a-z0-9а-яё-]", "", name.lower().replace(" ", "-"))


def _resolve_wikilinks(text: str) -> str:
    """Заменяет [[Note]] и [[Note|текст]] на HTML-ссылки для навигации внутри приложения."""

    def replace_link(match: re.Match) -> str:
        note_name = match.group(1).strip()
        display = match.group(2) or note_name
        # Убираем якорь вида #Section из имени заметки
        base_name = note_name.split("#")[0]
        slug = _slugify(base_name)
        return f'<a href="#page-{slug}" class="wikilink">{display.strip()}</a>'

    return WIKILINK_PATTERN.sub(replace_link, text)


def _extract_title(text: str, filename: str) -> str:
    """Извлекает заголовок из первого H1, иначе использует имя файла."""
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# ") and not stripped.startswith("## "):
            return stripped[2:].strip()
    return filename


def parse_markdown_file(filepath: Path, template: str = "") -> ContentPage:
    """Читает markdown-файл и возвращает ContentPage с HTML и метаданными."""
    raw_text = filepath.read_text(encoding="utf-8")

    # Разделяем frontmatter и контент
    post = frontmatter.loads(raw_text)
    body = post.content

    filename = filepath.stem
    title = post.get("title") or _extract_title(body, filename)

    # Обрабатываем wiki-ссылки до конвертации в HTML
    body_with_links = _resolve_wikilinks(body)

    # Конвертируем markdown -> HTML
    html = markdown.markdown(body_with_links, extensions=MD_EXTENSIONS)

    # Извлекаем структурированные данные если указан шаблон
    structured_data = {}
    if template:
        structured_data = extract_structured_data(template, body)

    return ContentPage(
        filename=filename,
        title=title,
        html_content=html,
        raw_markdown=body,
        template=template,
        structured_data=structured_data,
    )
