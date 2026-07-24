"""Парсеры структурированных данных из Obsidian-markdown.

Каждая функция принимает сырой markdown текст и возвращает dict.
При ошибке или пустых данных возвращает {}.
"""

import re


def extract_structured_data(template: str, raw_markdown: str) -> dict:
    """Диспетчер: вызывает нужный парсер по имени шаблона."""
    parsers = {
        "route_plan": parse_route_plan,
        "travel_logistics": parse_travel_logistics,
        "safety_briefing": parse_safety_briefing,
        "emergency_contacts": parse_emergency_contacts,
        "kids_on_board": parse_kids_on_board,
        "crew_list": parse_crew_list,
        "equipment_checklist": parse_equipment_checklist,
        "provisions": parse_provisions,
        "trip_overview": parse_trip_overview,
    }
    parser = parsers.get(template)
    if not parser:
        return {}
    try:
        return parser(raw_markdown)
    except Exception:
        return {}


# ---------------------------------------------------------------------------
# Общие хелперы для парсинга markdown
# ---------------------------------------------------------------------------

def _parse_horizontal_table(lines: list[str]) -> list[dict]:
    """Парсит горизонтальную таблицу (с заголовками) в список словарей."""
    if len(lines) < 3:
        return []

    # Первая строка — заголовки
    headers = [h.strip() for h in lines[0].strip().strip("|").split("|")]
    # Вторая строка — разделитель (пропускаем)
    rows = []
    for line in lines[2:]:
        line = line.strip()
        if not line or not line.startswith("|"):
            break
        cells = [c.strip() for c in line.strip("|").split("|")]
        row = {}
        for i, header in enumerate(headers):
            row[header] = cells[i] if i < len(cells) else ""
        rows.append(row)
    return rows


def _parse_vertical_table(lines: list[str]) -> dict:
    """Парсит вертикальную таблицу (ключ|значение) в словарь."""
    result = {}
    for line in lines:
        line = line.strip()
        if not line.startswith("|"):
            continue
        if line.startswith("|---") or line.startswith("| ---"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) >= 2:
            key = re.sub(r"\*\*(.+?)\*\*", r"\1", cells[0]).strip()
            value = cells[1].strip()
            if key:
                result[key] = value
    return result


def _extract_table_lines(text: str, start_idx: int) -> list[str]:
    """Извлекает строки таблицы начиная с позиции start_idx."""
    lines = text.split("\n")
    table_lines = []
    started = False
    for line in lines[start_idx:]:
        stripped = line.strip()
        if stripped.startswith("|"):
            started = True
            table_lines.append(stripped)
        elif started:
            break
    return table_lines


def _find_tables_after_header(text: str, header_pattern: str) -> list[str]:
    """Находит строки таблицы после заголовка, совпадающего с паттерном."""
    lines = text.split("\n")
    found = False
    table_lines = []
    for line in lines:
        stripped = line.strip()
        if re.match(header_pattern, stripped, re.IGNORECASE):
            found = True
            table_lines = []
            continue
        if found:
            if stripped.startswith("|"):
                table_lines.append(stripped)
            elif table_lines:
                break
            elif stripped.startswith("#"):
                break
    return table_lines


def _parse_checklist_items(text: str) -> list[dict]:
    """Парсит чекбокс-элементы из markdown."""
    items = []
    for line in text.split("\n"):
        stripped = line.strip()
        # Чекбокс: - [ ] или - [x]
        cb_match = re.match(r"^-\s*\[([ xX])\]\s*(.+)$", stripped)
        if cb_match:
            items.append({
                "text": cb_match.group(2).strip(),
                "checked": cb_match.group(1).lower() == "x",
                "is_checkbox": True,
            })
            continue
        # Обычный bullet
        bullet_match = re.match(r"^-\s+(.+)$", stripped)
        if bullet_match and not stripped.startswith("---"):
            items.append({
                "text": bullet_match.group(1).strip(),
                "checked": False,
                "is_checkbox": False,
            })
    return items


def _clean_bold(text: str) -> str:
    """Убирает **bold** маркеры."""
    return re.sub(r"\*\*(.+?)\*\*", r"\1", text).strip()


# ---------------------------------------------------------------------------
# Парсеры по типу контента
# ---------------------------------------------------------------------------

def parse_route_plan(md: str) -> dict:
    """Парсит Route plan: ### День N заголовки + вертикальные таблицы."""
    days = []
    sections = re.split(r"^### ", md, flags=re.MULTILINE)

    for section in sections[1:]:  # Пропускаем текст до первого ###
        lines = section.split("\n")
        header = lines[0].strip()

        # Извлекаем номер дня и описание
        day_match = re.match(r"День\s+(\d+)\s*[—–-]?\s*(.*)", header)
        if not day_match:
            continue

        day_num = int(day_match.group(1))
        title = day_match.group(2).strip()

        # Ищем таблицу (вертикальная: ключ|значение)
        table_data = _parse_vertical_table(lines[1:])

        # Также собираем пункты-буллеты
        bullets = []
        for line in lines[1:]:
            stripped = line.strip()
            if stripped.startswith("- ") and not stripped.startswith("|"):
                bullets.append(_clean_bold(stripped[2:]))

        day = {
            "day": day_num,
            "title": title,
            "from": table_data.get("Откуда", ""),
            "to": table_data.get("Куда", ""),
            "nm": table_data.get("Дистанция", ""),
            "course": table_data.get("Курс", ""),
            "anchorage": table_data.get("Стоянка", ""),
            "highlights": table_data.get("Highlights", ""),
            "kids": table_data.get("Для детей", ""),
            "note": table_data.get("Примечание", ""),
            "bullets": bullets,
        }
        days.append(day)

    if not days:
        return {}

    # Извлекаем общие принципы (текст до первого ###)
    principles = []
    for line in md.split("### ")[0].split("\n"):
        stripped = line.strip()
        if stripped.startswith("- "):
            principles.append(_clean_bold(stripped[2:]))

    return {"days": days, "principles": principles}


def parse_travel_logistics(md: str) -> dict:
    """Парсит Travel logistics: несколько таблиц + список."""
    result = {}

    # Аэропорты
    table = _find_tables_after_header(md, r"^##\s+Аэропорт")
    if table:
        result["airports"] = _parse_horizontal_table(table)

    # Перелёты
    table = _find_tables_after_header(md, r"^##\s+Перелёт")
    if table:
        result["flights"] = _parse_horizontal_table(table)

    # Трансферы
    table = _find_tables_after_header(md, r"^##\s+Трансфер")
    if table:
        result["transfers"] = _parse_horizontal_table(table)

    # Координация прибытия
    table = _find_tables_after_header(md, r"^##\s+Координация")
    if table:
        result["coordination"] = _parse_horizontal_table(table)

    # Ручная кладь
    carry_on = []
    in_carry_on = False
    for line in md.split("\n"):
        stripped = line.strip()
        if re.match(r"^##\s+Что взять", stripped, re.IGNORECASE):
            in_carry_on = True
            continue
        if in_carry_on:
            if stripped.startswith("## "):
                break
            if stripped.startswith("- "):
                carry_on.append(stripped[2:].strip())
    result["carry_on"] = carry_on

    return result if any(result.values()) else {}


def parse_safety_briefing(md: str) -> dict:
    """Парсит Safety briefing: ## N. Title + чекбоксы/буллеты."""
    sections = []
    parts = re.split(r"^## ", md, flags=re.MULTILINE)

    for part in parts[1:]:
        lines = part.split("\n")
        header = lines[0].strip()

        # Извлекаем номер и заголовок: "1. Спасательное оборудование"
        sec_match = re.match(r"(\d+)\.\s+(.+)", header)
        if not sec_match:
            continue

        number = int(sec_match.group(1))
        title = sec_match.group(2).strip()

        # Собираем элементы
        items = []
        for line in lines[1:]:
            stripped = line.strip()
            if stripped.startswith("## "):
                break
            cb_match = re.match(r"^-\s*\[([ xX])\]\s*(.+)$", stripped)
            if cb_match:
                items.append({
                    "text": _clean_bold(cb_match.group(2)),
                    "checked": cb_match.group(1).lower() == "x",
                    "is_checkbox": True,
                })
                continue
            bullet_match = re.match(r"^-\s+(.+)$", stripped)
            if bullet_match and not stripped.startswith("---"):
                items.append({
                    "text": _clean_bold(bullet_match.group(1)),
                    "checked": False,
                    "is_checkbox": False,
                })

        sections.append({
            "number": number,
            "title": title,
            "items": items,
        })

    return {"sections": sections} if sections else {}


def parse_emergency_contacts(md: str) -> dict:
    """Парсит Emergency contacts: несколько таблиц по категориям."""
    result = {}

    # Экстренные службы
    table = _find_tables_after_header(md, r"^##\s+Экстренные службы")
    if table:
        result["services"] = _parse_horizontal_table(table)

    # Чартерная компания (вертикальная таблица)
    lines = md.split("\n")
    charter_start = None
    for i, line in enumerate(lines):
        if re.match(r"^##\s+Чартерная", line.strip()):
            charter_start = i + 1
            break
    if charter_start:
        charter_lines = _extract_table_lines(md, charter_start)
        if charter_lines:
            result["charter"] = _parse_vertical_table(charter_lines)

    # Больницы
    table = _find_tables_after_header(md, r"^##\s+Ближайшие больницы")
    if table:
        result["hospitals"] = _parse_horizontal_table(table)

    # Посольства (вертикальная таблица)
    lines_list = md.split("\n")
    embassy_start = None
    for i, line in enumerate(lines_list):
        if re.match(r"^##\s+Посольств", line.strip()):
            embassy_start = i + 1
            break
    if embassy_start:
        emb_lines = _extract_table_lines(md, embassy_start)
        if emb_lines:
            result["embassies"] = _parse_vertical_table(emb_lines)

    # Контакты на берегу
    table = _find_tables_after_header(md, r"^##\s+Участники")
    if table:
        result["crew_contacts"] = _parse_horizontal_table(table)

    # VHF каналы
    table = _find_tables_after_header(md, r"^##\s+VHF")
    if table:
        result["vhf"] = _parse_horizontal_table(table)

    return result if any(result.values()) else {}


def parse_kids_on_board(md: str) -> dict:
    """Парсит Kids on board: правила + снаряжение + активности + режим."""
    result = {}

    # Правила (нумерованный список)
    rules = []
    in_rules = False
    for line in md.split("\n"):
        stripped = line.strip()
        if re.match(r"^##\s+Правила", stripped):
            in_rules = True
            continue
        if in_rules:
            if stripped.startswith("## "):
                break
            rule_match = re.match(r"^(\d+)\.\s+(.+)$", stripped)
            if rule_match:
                rules.append(_clean_bold(rule_match.group(2)))
    result["rules"] = rules

    # Снаряжение (чекбоксы)
    equipment = []
    in_equipment = False
    for line in md.split("\n"):
        stripped = line.strip()
        if re.match(r"^##\s+Снаряжение", stripped):
            in_equipment = True
            continue
        if in_equipment:
            if stripped.startswith("## "):
                break
            cb_match = re.match(r"^-\s*\[([ xX])\]\s*(.+)$", stripped)
            if cb_match:
                equipment.append({
                    "text": cb_match.group(2).strip(),
                    "checked": cb_match.group(1).lower() == "x",
                })
    result["equipment"] = equipment

    # Активности (### подкатегории)
    activities = {}
    current_cat = None
    in_activities = False
    for line in md.split("\n"):
        stripped = line.strip()
        if re.match(r"^##\s+Активности", stripped):
            in_activities = True
            continue
        if in_activities:
            if stripped.startswith("## ") and not stripped.startswith("### "):
                break
            cat_match = re.match(r"^###\s+(.+)$", stripped)
            if cat_match:
                current_cat = cat_match.group(1).strip()
                activities[current_cat] = []
                continue
            if current_cat:
                bullet_match = re.match(r"^-\s+(.+)$", stripped)
                if bullet_match:
                    activities[current_cat].append(bullet_match.group(1).strip())
    result["activities"] = activities

    # Режим дня (таблица)
    table = _find_tables_after_header(md, r"^##\s+Режим")
    if table:
        result["schedule"] = _parse_horizontal_table(table)

    return result if any(v for v in result.values()) else {}


def parse_crew_list(md: str) -> dict:
    """Парсит Crew list: таблица экипажа + роли + вахта + жилеты."""
    result = {}

    # Экипаж
    table = _find_tables_after_header(md, r"^##\s+Экипаж")
    if table:
        result["members"] = _parse_horizontal_table(table)

    # Роли (список)
    roles = []
    in_roles = False
    for line in md.split("\n"):
        stripped = line.strip()
        if re.match(r"^##\s+Роли", stripped):
            in_roles = True
            continue
        if in_roles:
            if stripped.startswith("## ") or stripped.startswith("> "):
                if stripped.startswith("> "):
                    continue
                break
            bullet_match = re.match(r"^-\s+(.+)$", stripped)
            if bullet_match:
                roles.append(_clean_bold(bullet_match.group(1)))
    result["roles"] = roles

    # Вахтенное расписание
    table = _find_tables_after_header(md, r"^##\s+Вахтенное")
    if table:
        result["watch_schedule"] = _parse_horizontal_table(table)

    # Размеры спасжилетов
    table = _find_tables_after_header(md, r"^##\s+Размеры")
    if table:
        result["life_jackets"] = _parse_horizontal_table(table)

    return result if any(v for v in result.values()) else {}


def parse_equipment_checklist(md: str) -> dict:
    """Парсит Equipment checklist: ## Category > ### Subcategory > чекбоксы."""
    categories = []
    current_cat = None
    current_subcat = None

    for line in md.split("\n"):
        stripped = line.strip()

        # ## Категория
        cat_match = re.match(r"^##\s+(.+)$", stripped)
        if cat_match:
            cat_name = cat_match.group(1).strip()
            current_cat = {"name": cat_name, "subcategories": []}
            categories.append(current_cat)
            current_subcat = None
            continue

        # ### Подкатегория
        subcat_match = re.match(r"^###\s+(.+)$", stripped)
        if subcat_match and current_cat:
            subcat_name = subcat_match.group(1).strip()
            current_subcat = {"name": subcat_name, "items": []}
            current_cat["subcategories"].append(current_subcat)
            continue

        # Чекбокс-элемент
        cb_match = re.match(r"^-\s*\[([ xX])\]\s*(.+)$", stripped)
        if cb_match:
            item = {
                "text": cb_match.group(2).strip(),
                "checked": cb_match.group(1).lower() == "x",
            }
            if current_subcat:
                current_subcat["items"].append(item)
            elif current_cat:
                # Элементы без подкатегории — создаём дефолтную
                if not current_cat["subcategories"] or current_cat["subcategories"][-1]["name"] != "":
                    current_cat["subcategories"].append({"name": "", "items": []})
                current_cat["subcategories"][-1]["items"].append(item)

    return {"categories": categories} if categories else {}


def parse_provisions(md: str) -> dict:
    """Парсит Provisions: ### Category таблицы + план питания + докупка."""
    result = {}

    # Основная закупка — таблицы по категориям
    shopping = []
    sections = re.split(r"^### ", md, flags=re.MULTILINE)

    for section in sections[1:]:
        lines = section.split("\n")
        cat_name = lines[0].strip()

        # Ищем таблицу в этой секции
        table_lines = []
        for line in lines[1:]:
            stripped = line.strip()
            if stripped.startswith("|"):
                table_lines.append(stripped)
            elif table_lines:
                break
            elif stripped.startswith("### ") or stripped.startswith("## "):
                break

        if table_lines:
            items = _parse_horizontal_table(table_lines)
            if items:
                shopping.append({"category": cat_name, "items": items})

    result["shopping"] = shopping

    # План питания по дням
    table = _find_tables_after_header(md, r"^##\s+План питания")
    if table:
        result["meal_plan"] = _parse_horizontal_table(table)

    # Докупка
    restock = []
    in_restock = False
    for line in md.split("\n"):
        stripped = line.strip()
        if re.match(r"^##\s+Докупка", stripped):
            in_restock = True
            continue
        if in_restock:
            if stripped.startswith("## "):
                break
            bullet_match = re.match(r"^-\s+(.+)$", stripped)
            if bullet_match:
                restock.append(bullet_match.group(1).strip())
    result["restock"] = restock

    return result if any(v for v in result.values()) else {}


def parse_trip_overview(md: str) -> dict:
    """Парсит Trip overview: вертикальная таблица фактов + статус (чекбоксы) + ростер (таблица)."""
    result = {}

    table = _find_tables_after_header(md, r"^##\s+На одном экране")
    if table:
        result["facts"] = _parse_vertical_table(table)

    status = []
    in_status = False
    for line in md.split("\n"):
        stripped = line.strip()
        if re.match(r"^##\s+Статус", stripped):
            in_status = True
            continue
        if in_status:
            if stripped.startswith("## "):
                break
            cb_match = re.match(r"^-\s*\[([ xX])\]\s*(.+)$", stripped)
            if cb_match:
                status.append({
                    "text": _clean_bold(cb_match.group(2)),
                    "checked": cb_match.group(1).lower() == "x",
                })
    result["status"] = status

    table = _find_tables_after_header(md, r"^##\s+Участники")
    if table:
        result["roster"] = _parse_horizontal_table(table)

    return result if any(v for v in result.values()) else {}
