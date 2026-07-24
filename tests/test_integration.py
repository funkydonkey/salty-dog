"""Интеграционные тесты: полный пайплайн от markdown-файлов до content.json.

Проверяет связку parser -> structured_parsers -> builder -> ContentBundle.
"""

from pathlib import Path

import pytest

from app.content.builder import build_content, write_content_json
from app.content.models import ContentBundle
from app.content.parser import parse_markdown_file


# ---------------------------------------------------------------------------
# Хелперы для создания тестовых vault-ов
# ---------------------------------------------------------------------------

SAFETY_BRIEFING_MD = """\
# Инструктаж по безопасности

## 1. Спасательное оборудование

- [x] Спасательные жилеты — в рундуке кокпита (8 шт)
- [x] Огнетушители — камбуз и моторный отсек
- [ ] Спасательный плот — проверить срок годности

## 2. Действия при падении за борт

- [ ] Крикнуть «Человек за бортом!»
- [ ] Бросить спасательный круг
- [ ] Не терять из виду
"""

CREW_LIST_MD = """\
# Список экипажа

## Экипаж

| Имя | Роль | Возраст |
|-----|------|---------|
| Иван | Шкипер | 42 |
| Мария | Штурман | 38 |
| Дети Петровы | Юнги | 10, 7 |

## Роли

- Шкипер — Иван (все решения по безопасности)
- Штурман — Мария (навигация и связь)
"""

ROUTE_PLAN_MD = """\
# План маршрута

- Принцип: не более 25 NM в день
- Принцип: стоянка до 16:00

### День 1 — Трогир — Маслиница

| **Откуда** | Марина Трогир |
| **Куда** | Маслиница (о. Шолта) |
| **Дистанция** | 12 NM |
| **Стоянка** | Бочки в бухте |
| **Для детей** | Пляж, снорклинг |

### День 2 — Маслиница — Вис

| **Откуда** | Маслиница |
| **Куда** | г. Вис |
| **Дистанция** | 18 NM |
| **Стоянка** | Городская марина |
"""

SIMPLE_PAGE_MD = """\
# О путешествии

Это вводная страница без шаблона. Просто текст с описанием
предстоящего чартера по Хорватии.

## Даты

Июль 2026, первая неделя.

## Участники

Семья Петровых и семья Ивановых.
"""

DAILY_ROUTE_WITH_COORDS_MD = """\
---
title: Маршрут по дням
---

# Маршрут

## День 1

- **Марина Трогир** | 43.508, 16.440 | Точка отправления
- **Маслиница** | 43.386, 16.183 | Якорная стоянка

## День 2

- **Город Вис** | 43.063, 16.183 | Историческая гавань
"""


def _create_vault(
    tmp_path: Path,
    app_yaml: str,
    files: dict[str, str],
) -> Path:
    """Создаёт временный vault с _app.yaml и набором markdown-файлов."""
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "_app.yaml").write_text(app_yaml, encoding="utf-8")
    for name, content in files.items():
        (vault / f"{name}.md").write_text(content, encoding="utf-8")
    return vault


# ---------------------------------------------------------------------------
# 1. Полный пайплайн: vault -> build_content -> ContentBundle -> JSON
# ---------------------------------------------------------------------------

class TestFullPipeline:
    """Полный путь: markdown + _app.yaml -> build_content -> content.json."""

    @pytest.fixture()
    def vault(self, tmp_path: Path) -> Path:
        app_yaml = """\
trip:
  name: "Хорватия 2026"
  boat: "Bavaria C42"
  dates: "5-12 июля 2026"
  departure_date: "2026-07-05"

sections:
  - id: "prep"
    title: "Подготовка"
    icon: "clipboard"
    tab: "prep"
    files:
      - {file: "Safety briefing", template: "safety_briefing"}
      - {file: "Crew list", template: "crew_list"}
      - "About"

  - id: "route"
    title: "Маршрут"
    icon: "map"
    tab: "route"
    files:
      - {file: "Route plan", template: "route_plan"}
      - "Daily route"
"""
        return _create_vault(tmp_path, app_yaml, {
            "Safety briefing": SAFETY_BRIEFING_MD,
            "Crew list": CREW_LIST_MD,
            "Route plan": ROUTE_PLAN_MD,
            "Daily route": DAILY_ROUTE_WITH_COORDS_MD,
            "About": SIMPLE_PAGE_MD,
        })

    def test_bundle_has_correct_sections(self, vault: Path):
        bundle = build_content(vault)

        assert len(bundle.sections) == 2
        ids = [s.id for s in bundle.sections]
        assert ids == ["prep", "route"]

    def test_pages_with_template_have_structured_data(self, vault: Path):
        """Страницы с шаблоном должны содержать непустые structured_data."""
        bundle = build_content(vault)
        prep = next(s for s in bundle.sections if s.id == "prep")

        safety = next(p for p in prep.pages if "безопасности" in p.title.lower() or "Safety" in p.title)
        assert safety.template == "safety_briefing"
        assert safety.structured_data != {}
        # Парсер safety_briefing возвращает {"sections": [...]}
        assert "sections" in safety.structured_data
        assert len(safety.structured_data["sections"]) >= 2

        crew = next(p for p in prep.pages if "экипажа" in p.title.lower() or "Crew" in p.title)
        assert crew.template == "crew_list"
        assert crew.structured_data != {}
        assert "members" in crew.structured_data

    def test_pages_without_template_have_empty_structured_data(self, vault: Path):
        """Страницы без шаблона — structured_data пустой dict."""
        bundle = build_content(vault)
        prep = next(s for s in bundle.sections if s.id == "prep")

        about = next(p for p in prep.pages if "путешествии" in p.title.lower() or "About" in p.title)
        assert about.template == ""
        assert about.structured_data == {}

    def test_trip_departure_date_preserved(self, vault: Path):
        bundle = build_content(vault)

        assert bundle.trip.departure_date == "2026-07-05"
        assert bundle.trip.name == "Хорватия 2026"
        assert bundle.trip.boat == "Bavaria C42"

    def test_content_hash_is_nonempty(self, vault: Path):
        bundle = build_content(vault)

        assert bundle.content_hash != ""
        assert len(bundle.content_hash) == 12

    def test_route_waypoints_extracted(self, vault: Path):
        """Координаты из файлов секции route должны попасть в route.waypoints."""
        bundle = build_content(vault)

        # Daily route имеет 3 waypoint-а в markdown
        assert len(bundle.route.waypoints) >= 3
        names = [w.name for w in bundle.route.waypoints]
        assert "Марина Трогир" in names
        assert "Город Вис" in names

    def test_write_and_read_json(self, vault: Path, tmp_path: Path):
        """Проверяем сериализацию: bundle -> JSON -> можно прочитать обратно."""
        import json

        bundle = build_content(vault)
        output = write_content_json(bundle, tmp_path / "output")

        assert output.exists()
        data = json.loads(output.read_text(encoding="utf-8"))

        assert data["trip"]["departure_date"] == "2026-07-05"
        assert len(data["sections"]) == 2
        assert data["content_hash"] == bundle.content_hash

    def test_all_pages_have_html_content(self, vault: Path):
        """Каждая страница должна иметь html_content и raw_markdown."""
        bundle = build_content(vault)

        for section in bundle.sections:
            for page in section.pages:
                assert page.html_content, f"Пустой html_content у {page.filename}"
                assert page.raw_markdown, f"Пустой raw_markdown у {page.filename}"


# ---------------------------------------------------------------------------
# 2. Шаблонная интеграция: parse_markdown_file + structured_parsers
# ---------------------------------------------------------------------------

class TestTemplateIntegration:
    """Парсинг markdown с шаблоном: html_content + structured_data одновременно."""

    def test_safety_briefing_template(self, tmp_path: Path):
        filepath = tmp_path / "Safety briefing.md"
        filepath.write_text(SAFETY_BRIEFING_MD, encoding="utf-8")

        page = parse_markdown_file(filepath, template="safety_briefing")

        # HTML для fallback-отображения
        assert "<h1>" in page.html_content or "<h2>" in page.html_content
        assert page.html_content != ""

        # Структурированные данные для шаблонного рендера
        assert page.structured_data != {}
        assert page.template == "safety_briefing"
        assert "sections" in page.structured_data

        # Проверяем содержимое парсинга
        sections = page.structured_data["sections"]
        assert sections[0]["number"] == 1
        assert sections[0]["title"] == "Спасательное оборудование"
        # Должны быть чекбоксы
        items = sections[0]["items"]
        assert any(i["checked"] for i in items)
        assert any(not i["checked"] for i in items)

    def test_crew_list_template(self, tmp_path: Path):
        filepath = tmp_path / "Crew list.md"
        filepath.write_text(CREW_LIST_MD, encoding="utf-8")

        page = parse_markdown_file(filepath, template="crew_list")

        assert page.template == "crew_list"
        assert "members" in page.structured_data
        assert len(page.structured_data["members"]) == 3
        assert page.structured_data["members"][0]["Имя"] == "Иван"

    def test_route_plan_template(self, tmp_path: Path):
        filepath = tmp_path / "Route plan.md"
        filepath.write_text(ROUTE_PLAN_MD, encoding="utf-8")

        page = parse_markdown_file(filepath, template="route_plan")

        assert page.template == "route_plan"
        assert "days" in page.structured_data
        days = page.structured_data["days"]
        assert len(days) == 2
        assert days[0]["day"] == 1
        assert days[0]["from"] == "Марина Трогир"
        assert days[1]["to"] == "г. Вис"

    def test_unknown_template_returns_empty_structured_data(self, tmp_path: Path):
        """Неизвестный шаблон — structured_data пустой, но html есть."""
        filepath = tmp_path / "page.md"
        filepath.write_text("# Заголовок\n\nТекст страницы.", encoding="utf-8")

        page = parse_markdown_file(filepath, template="nonexistent_template")

        assert page.template == "nonexistent_template"
        assert page.structured_data == {}
        assert page.html_content != ""

    def test_no_template_skips_structured_parsing(self, tmp_path: Path):
        """Без шаблона structured_parsers вообще не вызывается."""
        filepath = tmp_path / "simple.md"
        filepath.write_text(SIMPLE_PAGE_MD, encoding="utf-8")

        page = parse_markdown_file(filepath, template="")

        assert page.template == ""
        assert page.structured_data == {}
        assert "<h1>" in page.html_content


# ---------------------------------------------------------------------------
# 3. Dict-формат записей в _app.yaml
# ---------------------------------------------------------------------------

class TestDictFormatFileEntries:
    """Записи вида {file: 'Name', template: 'tpl'} в _app.yaml."""

    def test_dict_entries_assign_templates(self, tmp_path: Path):
        app_yaml = """\
trip:
  name: "Тест"

sections:
  - id: "info"
    title: "Информация"
    icon: "info"
    tab: "info"
    files:
      - {file: "Safety", template: "safety_briefing"}
      - {file: "Crew", template: "crew_list"}
"""
        vault = _create_vault(tmp_path, app_yaml, {
            "Safety": SAFETY_BRIEFING_MD,
            "Crew": CREW_LIST_MD,
        })

        bundle = build_content(vault)
        pages = bundle.sections[0].pages

        assert len(pages) == 2
        assert pages[0].template == "safety_briefing"
        assert pages[0].structured_data != {}
        assert pages[1].template == "crew_list"
        assert pages[1].structured_data != {}

    def test_dict_entry_without_template_field(self, tmp_path: Path):
        """Dict без поля template — шаблон пустой."""
        app_yaml = """\
trip:
  name: "Тест"

sections:
  - id: "s"
    title: "S"
    icon: ""
    tab: "s"
    files:
      - {file: "About"}
"""
        vault = _create_vault(tmp_path, app_yaml, {"About": SIMPLE_PAGE_MD})

        bundle = build_content(vault)
        page = bundle.sections[0].pages[0]

        assert page.template == ""
        assert page.structured_data == {}

    def test_mixed_dict_and_string_entries(self, tmp_path: Path):
        """Смешанные записи: dict + строка в одной секции."""
        app_yaml = """\
trip:
  name: "Микс"

sections:
  - id: "mix"
    title: "Смешанная секция"
    icon: ""
    tab: "mix"
    files:
      - {file: "Safety", template: "safety_briefing"}
      - "About"
"""
        vault = _create_vault(tmp_path, app_yaml, {
            "Safety": SAFETY_BRIEFING_MD,
            "About": SIMPLE_PAGE_MD,
        })

        bundle = build_content(vault)
        pages = bundle.sections[0].pages

        assert len(pages) == 2
        # Первая — с шаблоном
        assert pages[0].template == "safety_briefing"
        assert pages[0].structured_data != {}
        # Вторая — строка, без шаблона
        assert pages[1].template == ""
        assert pages[1].structured_data == {}


# ---------------------------------------------------------------------------
# 4. Обратная совместимость: строковые записи без шаблонов
# ---------------------------------------------------------------------------

class TestBackwardCompat:
    """Строковые записи в _app.yaml (старый формат) продолжают работать."""

    def test_plain_string_entries_work(self, tmp_path: Path):
        app_yaml = """\
trip:
  name: "Старый формат"
  boat: "Jeanneau 54"
  dates: "Август 2026"

sections:
  - id: "docs"
    title: "Документы"
    icon: "file"
    tab: "docs"
    files:
      - "Safety"
      - "About"
"""
        vault = _create_vault(tmp_path, app_yaml, {
            "Safety": SAFETY_BRIEFING_MD,
            "About": SIMPLE_PAGE_MD,
        })

        bundle = build_content(vault)

        assert len(bundle.sections) == 1
        pages = bundle.sections[0].pages
        assert len(pages) == 2

        for page in pages:
            # Строковые записи — без шаблона
            assert page.template == ""
            assert page.structured_data == {}
            # Но HTML и markdown на месте
            assert page.html_content != ""
            assert page.raw_markdown != ""

    def test_plain_string_entries_preserve_titles(self, tmp_path: Path):
        """Заголовки извлекаются из markdown даже без шаблона."""
        app_yaml = """\
trip:
  name: "Тест"

sections:
  - id: "s"
    title: "S"
    icon: ""
    tab: "s"
    files:
      - "About"
"""
        vault = _create_vault(tmp_path, app_yaml, {"About": SIMPLE_PAGE_MD})

        bundle = build_content(vault)
        page = bundle.sections[0].pages[0]

        # Заголовок берётся из первого H1 в markdown
        assert "путешествии" in page.title.lower()

    def test_trip_defaults_for_missing_fields(self, tmp_path: Path):
        """Поля trip с дефолтами не ломаются при частичном конфиге."""
        app_yaml = """\
trip:
  name: "Минимальный трип"

sections: []
"""
        vault = _create_vault(tmp_path, app_yaml, {})

        bundle = build_content(vault)

        assert bundle.trip.name == "Минимальный трип"
        assert bundle.trip.boat == "TBD"
        assert bundle.trip.dates == "TBD"
        assert bundle.trip.departure_date == ""
