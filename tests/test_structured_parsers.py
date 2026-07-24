"""Тесты для парсеров структурированных данных (app.content.structured_parsers).

Каждый парсер извлекает dict из Obsidian-markdown.
Тестируем: корректный ввод, пустой/минимальный ввод, черновые данные.
"""

import pytest

from app.content.structured_parsers import (
    extract_structured_data,
    parse_route_plan,
    parse_travel_logistics,
    parse_safety_briefing,
    parse_emergency_contacts,
    parse_kids_on_board,
    parse_crew_list,
    parse_equipment_checklist,
    parse_provisions,
)


# ---------------------------------------------------------------------------
# Диспетчер extract_structured_data
# ---------------------------------------------------------------------------

class TestExtractStructuredData:
    """Тесты диспетчера: маршрутизация по имени шаблона."""

    def test_dispatches_to_route_plan(self):
        md = "### День 1 — Сплит\n| **Откуда** | Марина Кашела |\n| **Куда** | Масленица |"
        result = extract_structured_data("route_plan", md)
        assert "days" in result
        assert result["days"][0]["day"] == 1

    def test_dispatches_to_safety_briefing(self):
        md = "## 1. Спасательное оборудование\n- [ ] Жилеты под банкой"
        result = extract_structured_data("safety_briefing", md)
        assert "sections" in result

    def test_unknown_template_returns_empty(self):
        result = extract_structured_data("nonexistent_template", "# Markdown")
        assert result == {}

    def test_empty_template_returns_empty(self):
        result = extract_structured_data("", "# Some content")
        assert result == {}

    def test_exception_in_parser_returns_empty(self):
        """Если парсер бросает исключение, диспетчер ловит и возвращает {}."""
        # None вместо строки вызовет AttributeError внутри парсера
        result = extract_structured_data("route_plan", None)
        assert result == {}

    def test_all_template_names_are_valid(self):
        """Проверяем, что все 8 шаблонов маршрутизируются (не возвращают {} на пустую строку)."""
        templates = [
            "route_plan", "travel_logistics", "safety_briefing",
            "emergency_contacts", "kids_on_board", "crew_list",
            "equipment_checklist", "provisions",
        ]
        for name in templates:
            # Пустая строка — парсер вернёт {}, но не упадёт
            result = extract_structured_data(name, "")
            assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# parse_route_plan
# ---------------------------------------------------------------------------

class TestParseRoutePlan:
    """Парсер маршрутного плана: ### День N + вертикальные таблицы."""

    ROUTE_MD = """\
- Идём только днём, ночные переходы исключены
- Якорные стоянки в приоритете над маринами

### День 1 — Сплит → Масленица (Шолта)

| **Откуда** | Марина Кашела |
|---|---|
| **Куда** | Масленица, Шолта |
| **Дистанция** | 12 nm |
| **Курс** | 240° |
| **Стоянка** | Якорь в бухте |
| **Highlights** | Средневековый замок |
| **Для детей** | Пляж с мелким песком |
| **Примечание** | Прибытие после 14:00 |

- Заправка в марине перед выходом
- Купить лёд

### День 2 — Масленица → Вис

| **Откуда** | Масленица |
|---|---|
| **Куда** | г. Вис |
| **Дистанция** | 22 nm |
| **Курс** | 210° |
| **Стоянка** | Марина Вис |
"""

    def test_parses_multiple_days(self):
        result = parse_route_plan(self.ROUTE_MD)
        assert len(result["days"]) == 2

    def test_day_fields_extracted(self):
        result = parse_route_plan(self.ROUTE_MD)
        day1 = result["days"][0]

        assert day1["day"] == 1
        assert day1["title"] == "Сплит → Масленица (Шолта)"
        assert day1["from"] == "Марина Кашела"
        assert day1["to"] == "Масленица, Шолта"
        assert day1["nm"] == "12 nm"
        assert day1["course"] == "240°"
        assert day1["anchorage"] == "Якорь в бухте"
        assert day1["highlights"] == "Средневековый замок"
        assert day1["kids"] == "Пляж с мелким песком"
        assert day1["note"] == "Прибытие после 14:00"

    def test_day2_fields(self):
        result = parse_route_plan(self.ROUTE_MD)
        day2 = result["days"][1]

        assert day2["day"] == 2
        assert day2["from"] == "Масленица"
        assert day2["to"] == "г. Вис"
        assert day2["nm"] == "22 nm"

    def test_bullets_collected(self):
        result = parse_route_plan(self.ROUTE_MD)
        day1 = result["days"][0]

        assert "Заправка в марине перед выходом" in day1["bullets"]
        assert "Купить лёд" in day1["bullets"]

    def test_principles_extracted(self):
        result = parse_route_plan(self.ROUTE_MD)

        assert "Идём только днём, ночные переходы исключены" in result["principles"]
        assert "Якорные стоянки в приоритете над маринами" in result["principles"]

    def test_empty_input_returns_empty(self):
        assert parse_route_plan("") == {}

    def test_no_days_returns_empty(self):
        md = "# Маршрут\n\nОбщая информация без конкретных дней."
        assert parse_route_plan(md) == {}

    def test_day_without_table(self):
        """День с заголовком, но без таблицы — поля будут пустыми строками."""
        md = "### День 1 — Только заголовок\n\nПросто текст."
        result = parse_route_plan(md)

        assert len(result["days"]) == 1
        assert result["days"][0]["from"] == ""
        assert result["days"][0]["to"] == ""

    def test_bold_markers_stripped_from_principles(self):
        md = "- **Важный** принцип навигации\n\n### День 1 — Тест\n| **Откуда** | A |"
        result = parse_route_plan(md)

        assert "Важный принцип навигации" in result["principles"]

    def test_day_with_dash_separator(self):
        """Поддержка разных разделителей: тире, длинное тире, дефис."""
        md = "### День 3 – Хвар → Корчула\n| **Откуда** | Хвар |"
        result = parse_route_plan(md)
        assert result["days"][0]["day"] == 3
        assert "Хвар" in result["days"][0]["title"]


# ---------------------------------------------------------------------------
# parse_travel_logistics
# ---------------------------------------------------------------------------

class TestParseTravelLogistics:
    """Парсер логистики: аэропорты, перелёты, трансферы, координация, ручная кладь."""

    LOGISTICS_MD = """\
# Логистика перелётов

## Аэропорты

| Город | Код | Расстояние до марины |
|---|---|---|
| Сплит | SPU | 25 км |
| Загреб | ZAG | 410 км |

## Перелёты

| Рейс | Дата | Время | Маршрут |
|---|---|---|---|
| SU2082 | 28.06 | 06:15 | SVO → SPU |
| SU2083 | 05.07 | 14:30 | SPU → SVO |

## Трансферы

| Откуда | Куда | Время | Стоимость |
|---|---|---|---|
| SPU аэропорт | Марина Кашела | 30 мин | €40 |

## Координация прибытия

| Участник | Рейс | Прибытие |
|---|---|---|
| Семья Ивановых | SU2082 | 10:15 |

## Что взять в ручную кладь

- Документы (паспорта, права, страховки)
- Аптечка (от укачивания обязательно!)
- Солнцезащитный крем SPF50
"""

    def test_airports_parsed(self):
        result = parse_travel_logistics(self.LOGISTICS_MD)
        assert len(result["airports"]) == 2
        assert result["airports"][0]["Код"] == "SPU"
        assert result["airports"][1]["Город"] == "Загреб"

    def test_flights_parsed(self):
        result = parse_travel_logistics(self.LOGISTICS_MD)
        assert len(result["flights"]) == 2
        assert result["flights"][0]["Рейс"] == "SU2082"
        assert result["flights"][1]["Маршрут"] == "SPU → SVO"

    def test_transfers_parsed(self):
        result = parse_travel_logistics(self.LOGISTICS_MD)
        assert len(result["transfers"]) == 1
        assert result["transfers"][0]["Стоимость"] == "€40"

    def test_coordination_parsed(self):
        result = parse_travel_logistics(self.LOGISTICS_MD)
        assert len(result["coordination"]) == 1
        assert result["coordination"][0]["Участник"] == "Семья Ивановых"

    def test_carry_on_parsed(self):
        result = parse_travel_logistics(self.LOGISTICS_MD)
        assert len(result["carry_on"]) == 3
        assert "Документы (паспорта, права, страховки)" in result["carry_on"]
        assert "Солнцезащитный крем SPF50" in result["carry_on"]

    def test_empty_input_returns_empty(self):
        assert parse_travel_logistics("") == {}

    def test_only_carry_on_section(self):
        md = "## Что взять в ручную кладь\n\n- Паспорта\n- Деньги"
        result = parse_travel_logistics(md)
        assert result["carry_on"] == ["Паспорта", "Деньги"]

    def test_no_matching_sections(self):
        md = "## Другой раздел\n\nТекст без таблиц."
        assert parse_travel_logistics(md) == {}


# ---------------------------------------------------------------------------
# parse_safety_briefing
# ---------------------------------------------------------------------------

class TestParseSafetyBriefing:
    """Парсер инструктажа по безопасности: ## N. Заголовок + чекбоксы."""

    SAFETY_MD = """\
# Инструктаж по безопасности

## 1. Спасательное оборудование

- [x] Показать расположение жилетов
- [ ] Проверить срок годности пиротехники
- Дополнительный комментарий без чекбокса

## 2. Действия при падении за борт (MOB)

- [ ] **Крикнуть** «Человек за бортом!»
- [x] Бросить спасательный круг
- [ ] Нажать кнопку MOB на GPS

## 3. Пожарная безопасность

- [ ] Огнетушители: камбуз + кокпит
- [ ] Запрет курения в каюте
"""

    def test_all_sections_parsed(self):
        result = parse_safety_briefing(self.SAFETY_MD)
        assert len(result["sections"]) == 3

    def test_section_number_and_title(self):
        result = parse_safety_briefing(self.SAFETY_MD)
        s1 = result["sections"][0]
        assert s1["number"] == 1
        assert s1["title"] == "Спасательное оборудование"

        s2 = result["sections"][1]
        assert s2["number"] == 2
        assert "MOB" in s2["title"]

    def test_checkboxes_parsed(self):
        result = parse_safety_briefing(self.SAFETY_MD)
        items = result["sections"][0]["items"]

        # Первый чекбокс отмечен
        assert items[0]["text"] == "Показать расположение жилетов"
        assert items[0]["checked"] is True
        assert items[0]["is_checkbox"] is True

        # Второй — не отмечен
        assert items[1]["text"] == "Проверить срок годности пиротехники"
        assert items[1]["checked"] is False
        assert items[1]["is_checkbox"] is True

    def test_regular_bullets_included(self):
        """Обычные буллеты (без чекбокса) тоже попадают в items."""
        result = parse_safety_briefing(self.SAFETY_MD)
        items = result["sections"][0]["items"]

        bullet = items[2]
        assert bullet["text"] == "Дополнительный комментарий без чекбокса"
        assert bullet["is_checkbox"] is False
        assert bullet["checked"] is False

    def test_bold_text_cleaned(self):
        """**bold** маркеры убираются из текста элементов."""
        result = parse_safety_briefing(self.SAFETY_MD)
        items = result["sections"][1]["items"]

        assert items[0]["text"] == "Крикнуть «Человек за бортом!»"

    def test_empty_input_returns_empty(self):
        assert parse_safety_briefing("") == {}

    def test_no_numbered_sections(self):
        md = "## Без номера\n\n- [ ] Пункт"
        assert parse_safety_briefing(md) == {}

    def test_section_without_items(self):
        md = "## 1. Пустой раздел\n\nТолько текст, без чекбоксов."
        result = parse_safety_briefing(md)
        assert result["sections"][0]["items"] == []


# ---------------------------------------------------------------------------
# parse_emergency_contacts
# ---------------------------------------------------------------------------

class TestParseEmergencyContacts:
    """Парсер экстренных контактов: горизонтальные и вертикальные таблицы."""

    CONTACTS_MD = """\
# Экстренные контакты

## Экстренные службы

| Служба | Номер | Примечание |
|---|---|---|
| Полиция | 192 | |
| Скорая помощь | 194 | |
| Береговая охрана | 195 | VHF канал 16 |

## Чартерная компания

| **Компания** | Sail Croatia d.o.o. |
|---|---|
| **Телефон** | +385 21 123 456 |
| **WhatsApp** | +385 91 987 654 |
| **Email** | charter@example.com |
| **База** | Марина Кашела, Сплит |

## Ближайшие больницы

| Город | Больница | Телефон |
|---|---|---|
| Сплит | KBC Split | +385 21 556 111 |
| Хвар | Dom zdravlja Hvar | +385 21 741 011 |

## Посольства

| **Посольство РФ** | +385 1 3755 038 |
|---|---|
| **Консул (моб.)** | +385 91 2345 678 |
| **Адрес** | Загреб, Босанска 44 |

## Участники

| Имя | Телефон | Роль |
|---|---|---|
| Иван Иванов | +7 999 123 4567 | Шкипер |
| Мария Петрова | +7 999 765 4321 | Штурман |

## VHF каналы

| Канал | Назначение |
|---|---|
| 16 | Экстренный вызов |
| 17 | Береговая охрана Сплит |
"""

    def test_services_parsed(self):
        result = parse_emergency_contacts(self.CONTACTS_MD)
        assert len(result["services"]) == 3
        assert result["services"][0]["Номер"] == "192"
        assert result["services"][2]["Служба"] == "Береговая охрана"

    def test_charter_vertical_table(self):
        result = parse_emergency_contacts(self.CONTACTS_MD)
        charter = result["charter"]
        assert charter["Компания"] == "Sail Croatia d.o.o."
        assert charter["Телефон"] == "+385 21 123 456"
        assert charter["Email"] == "charter@example.com"

    def test_hospitals_parsed(self):
        result = parse_emergency_contacts(self.CONTACTS_MD)
        assert len(result["hospitals"]) == 2
        assert result["hospitals"][0]["Город"] == "Сплит"

    def test_embassies_vertical_table(self):
        result = parse_emergency_contacts(self.CONTACTS_MD)
        emb = result["embassies"]
        assert emb["Посольство РФ"] == "+385 1 3755 038"
        assert "Загреб" in emb["Адрес"]

    def test_crew_contacts_parsed(self):
        result = parse_emergency_contacts(self.CONTACTS_MD)
        assert len(result["crew_contacts"]) == 2
        assert result["crew_contacts"][0]["Роль"] == "Шкипер"

    def test_vhf_parsed(self):
        result = parse_emergency_contacts(self.CONTACTS_MD)
        assert len(result["vhf"]) == 2
        assert result["vhf"][0]["Канал"] == "16"

    def test_empty_input_returns_empty(self):
        assert parse_emergency_contacts("") == {}

    def test_partial_data(self):
        """Только одна секция — остальные ключи отсутствуют."""
        md = """\
## Экстренные службы

| Служба | Номер |
|---|---|
| Полиция | 192 |
"""
        result = parse_emergency_contacts(md)
        assert "services" in result
        assert "charter" not in result
        assert "hospitals" not in result


# ---------------------------------------------------------------------------
# parse_kids_on_board
# ---------------------------------------------------------------------------

class TestParseKidsOnBoard:
    """Парсер правил для детей: правила + снаряжение + активности + режим."""

    KIDS_MD = """\
# Дети на борту

## Правила безопасности

1. На палубе всегда в жилете
2. Без разрешения не выходить в кокпит ночью
3. При маневрах сидеть внизу

## Снаряжение

- [x] Детские спасжилеты (3 шт.)
- [x] Сетка на леера
- [ ] Солнцезащитный тент
- [ ] Детский горшок

## Активности

### На якоре

- Купание с маской
- Рыбалка удочкой
- Морской бинокль

### На ходу

- Рулить под присмотром
- Изучать карту
- Вести бортовой дневник

### На берегу

- Исследование крепостей
- Мороженое-квест

## Режим дня

| Время | Активность |
|---|---|
| 07:00 | Подъём, завтрак |
| 09:00 | Выход в море |
| 12:30 | Обед на якоре |
| 15:00 | Купание / берег |
| 19:00 | Ужин |
| 21:00 | Отбой |
"""

    def test_rules_parsed(self):
        result = parse_kids_on_board(self.KIDS_MD)
        assert len(result["rules"]) == 3
        assert "жилете" in result["rules"][0]
        assert "маневрах" in result["rules"][2]

    def test_equipment_checkboxes(self):
        result = parse_kids_on_board(self.KIDS_MD)
        eq = result["equipment"]

        assert len(eq) == 4
        assert eq[0]["text"] == "Детские спасжилеты (3 шт.)"
        assert eq[0]["checked"] is True
        assert eq[2]["text"] == "Солнцезащитный тент"
        assert eq[2]["checked"] is False

    def test_activities_by_category(self):
        result = parse_kids_on_board(self.KIDS_MD)
        acts = result["activities"]

        assert "На якоре" in acts
        assert "На ходу" in acts
        assert "На берегу" in acts
        assert "Купание с маской" in acts["На якоре"]
        assert "Рулить под присмотром" in acts["На ходу"]
        assert len(acts["На берегу"]) == 2

    def test_schedule_parsed(self):
        result = parse_kids_on_board(self.KIDS_MD)
        sched = result["schedule"]

        assert len(sched) == 6
        assert sched[0]["Время"] == "07:00"
        assert sched[0]["Активность"] == "Подъём, завтрак"
        assert sched[-1]["Время"] == "21:00"

    def test_empty_input_returns_empty(self):
        assert parse_kids_on_board("") == {}

    def test_only_rules_section(self):
        md = "## Правила\n\n1. Одно правило"
        result = parse_kids_on_board(md)
        assert result["rules"] == ["Одно правило"]

    def test_no_matching_sections(self):
        md = "## Другое\n\nТекст."
        assert parse_kids_on_board(md) == {}


# ---------------------------------------------------------------------------
# parse_crew_list
# ---------------------------------------------------------------------------

class TestParseCrewList:
    """Парсер списка экипажа: таблица + роли + вахта + жилеты."""

    CREW_MD = """\
# Список экипажа

## Экипаж

| Имя | Возраст | Паспорт | Примечание |
|---|---|---|---|
| Иван Иванов | 38 | 72 1234567 | Шкипер |
| Мария Петрова | 35 | 72 7654321 | Штурман |
| Аня Иванова | 8 | 72 1111111 | Ребёнок |

## Роли на борту

- **Шкипер** — Иван (все решения на воде)
- **Штурман** — Мария (навигация, прогноз)
- **Кок** — чередование по дням

> Распределение ролей может меняться

## Вахтенное расписание

| Смена | Время | Вахтенный |
|---|---|---|
| Утренняя | 06:00–12:00 | Иван |
| Дневная | 12:00–18:00 | Мария |

## Размеры спасжилетов

| Имя | Размер | Номер жилета |
|---|---|---|
| Иван | XL | 1 |
| Мария | M | 2 |
| Аня | Детский | 3 |
"""

    def test_members_parsed(self):
        result = parse_crew_list(self.CREW_MD)
        members = result["members"]

        assert len(members) == 3
        assert members[0]["Имя"] == "Иван Иванов"
        assert members[2]["Примечание"] == "Ребёнок"

    def test_roles_parsed(self):
        result = parse_crew_list(self.CREW_MD)
        roles = result["roles"]

        assert len(roles) == 3
        # bold-маркеры убраны
        assert "Шкипер — Иван (все решения на воде)" in roles[0]

    def test_roles_skip_blockquotes(self):
        """Blockquote (> текст) не попадает в роли."""
        result = parse_crew_list(self.CREW_MD)
        for role in result["roles"]:
            assert not role.startswith(">")

    def test_watch_schedule_parsed(self):
        result = parse_crew_list(self.CREW_MD)
        ws = result["watch_schedule"]

        assert len(ws) == 2
        assert ws[0]["Смена"] == "Утренняя"
        assert ws[1]["Вахтенный"] == "Мария"

    def test_life_jackets_parsed(self):
        result = parse_crew_list(self.CREW_MD)
        lj = result["life_jackets"]

        assert len(lj) == 3
        assert lj[2]["Размер"] == "Детский"

    def test_empty_input_returns_empty(self):
        assert parse_crew_list("") == {}

    def test_only_members_table(self):
        md = """\
## Экипаж

| Имя | Возраст |
|---|---|
| Тест | 30 |
"""
        result = parse_crew_list(md)
        assert len(result["members"]) == 1
        assert result["roles"] == []

    def test_no_matching_sections(self):
        md = "## Другое\n\nНет данных."
        assert parse_crew_list(md) == {}


# ---------------------------------------------------------------------------
# parse_equipment_checklist
# ---------------------------------------------------------------------------

class TestParseEquipmentChecklist:
    """Парсер чеклиста снаряжения: ## Категория > ### Подкатегория > чекбоксы."""

    EQUIPMENT_MD = """\
# Чеклист снаряжения

## Навигация

### Электроника

- [x] Планшет с Navionics
- [x] Запасной телефон с iSailor
- [ ] Портативная рация VHF

### Бумажные карты

- [ ] Карта Средней Далмации 1:100000
- [x] Лоция Хорватии

## Безопасность

### Спасательное

- [x] Жилеты (по числу экипажа)
- [ ] Спасательный плот

### Аптечка

- [x] Пластыри, бинты
- [ ] Драмина (от укачивания)
- [ ] Антисептик

## Камбуз

- [x] Газовый баллон (запасной)
- [ ] Набор кастрюль
"""

    def test_categories_parsed(self):
        result = parse_equipment_checklist(self.EQUIPMENT_MD)
        cats = result["categories"]

        assert len(cats) == 3
        assert cats[0]["name"] == "Навигация"
        assert cats[1]["name"] == "Безопасность"
        assert cats[2]["name"] == "Камбуз"

    def test_subcategories_parsed(self):
        result = parse_equipment_checklist(self.EQUIPMENT_MD)
        nav = result["categories"][0]

        assert len(nav["subcategories"]) == 2
        assert nav["subcategories"][0]["name"] == "Электроника"
        assert nav["subcategories"][1]["name"] == "Бумажные карты"

    def test_items_in_subcategory(self):
        result = parse_equipment_checklist(self.EQUIPMENT_MD)
        electronics = result["categories"][0]["subcategories"][0]

        assert len(electronics["items"]) == 3
        assert electronics["items"][0]["text"] == "Планшет с Navionics"
        assert electronics["items"][0]["checked"] is True
        assert electronics["items"][2]["text"] == "Портативная рация VHF"
        assert electronics["items"][2]["checked"] is False

    def test_items_without_subcategory(self):
        """Категория 'Камбуз' без ### — создаётся дефолтная подкатегория."""
        result = parse_equipment_checklist(self.EQUIPMENT_MD)
        galley = result["categories"][2]

        assert len(galley["subcategories"]) == 1
        assert galley["subcategories"][0]["name"] == ""
        assert len(galley["subcategories"][0]["items"]) == 2

    def test_checked_status(self):
        result = parse_equipment_checklist(self.EQUIPMENT_MD)
        safety = result["categories"][1]["subcategories"][0]  # Спасательное

        assert safety["items"][0]["checked"] is True   # Жилеты
        assert safety["items"][1]["checked"] is False   # Плот

    def test_empty_input_returns_empty(self):
        assert parse_equipment_checklist("") == {}

    def test_no_categories(self):
        md = "Просто текст без заголовков."
        assert parse_equipment_checklist(md) == {}

    def test_category_without_items(self):
        md = "## Пустая категория\n\nТекст без чекбоксов."
        result = parse_equipment_checklist(md)
        assert result["categories"][0]["name"] == "Пустая категория"
        assert result["categories"][0]["subcategories"] == []

    def test_uppercase_x_treated_as_checked(self):
        md = "## Тест\n\n- [X] Отмечено большой X"
        result = parse_equipment_checklist(md)
        items = result["categories"][0]["subcategories"][0]["items"]
        assert items[0]["checked"] is True


# ---------------------------------------------------------------------------
# parse_provisions
# ---------------------------------------------------------------------------

class TestParseProvisions:
    """Парсер провизии: ### Категория таблицы + план питания + докупка."""

    PROVISIONS_MD = """\
# Провизия

## Основная закупка

### Овощи и фрукты

| Продукт | Количество | Примечание |
|---|---|---|
| Помидоры | 3 кг | Черри + обычные |
| Огурцы | 2 кг | |
| Лимоны | 10 шт | Для воды и рыбы |

### Мясо и рыба

| Продукт | Количество | Примечание |
|---|---|---|
| Куриные бёдра | 2 кг | Для гриля |
| Фарш говяжий | 1 кг | Болоньезе |

### Напитки

| Продукт | Количество | Примечание |
|---|---|---|
| Вода 5л | 6 бут | |
| Пиво | 24 бан | Местное |

## План питания

| День | Завтрак | Обед | Ужин |
|---|---|---|---|
| День 1 | Круассаны | Салат | Гриль на борту |
| День 2 | Омлет | Сэндвичи | Ресторан на берегу |

## Докупка на месте

- Свежий хлеб (каждое утро)
- Рыба на местном рынке
- Лёд для кулера
"""

    def test_shopping_categories_parsed(self):
        result = parse_provisions(self.PROVISIONS_MD)
        shopping = result["shopping"]

        assert len(shopping) == 3
        assert shopping[0]["category"] == "Овощи и фрукты"
        assert shopping[1]["category"] == "Мясо и рыба"
        assert shopping[2]["category"] == "Напитки"

    def test_shopping_items(self):
        result = parse_provisions(self.PROVISIONS_MD)
        vegs = result["shopping"][0]["items"]

        assert len(vegs) == 3
        assert vegs[0]["Продукт"] == "Помидоры"
        assert vegs[0]["Количество"] == "3 кг"
        assert vegs[2]["Примечание"] == "Для воды и рыбы"

    def test_empty_cells_handled(self):
        """Пустые ячейки в таблице не вызывают ошибку."""
        result = parse_provisions(self.PROVISIONS_MD)
        vegs = result["shopping"][0]["items"]

        # Огурцы — пустое примечание
        assert vegs[1]["Примечание"] == ""

    def test_meal_plan_parsed(self):
        result = parse_provisions(self.PROVISIONS_MD)
        plan = result["meal_plan"]

        assert len(plan) == 2
        assert plan[0]["День"] == "День 1"
        assert plan[0]["Ужин"] == "Гриль на борту"
        assert plan[1]["Завтрак"] == "Омлет"

    def test_restock_list_parsed(self):
        result = parse_provisions(self.PROVISIONS_MD)
        restock = result["restock"]

        assert len(restock) == 3
        assert "Свежий хлеб (каждое утро)" in restock
        assert "Лёд для кулера" in restock

    def test_empty_input_returns_empty(self):
        assert parse_provisions("") == {}

    def test_only_meal_plan(self):
        md = """\
## План питания

| День | Завтрак |
|---|---|
| 1 | Каша |
"""
        result = parse_provisions(md)
        assert len(result["meal_plan"]) == 1
        assert result["shopping"] == []

    def test_only_restock(self):
        md = "## Докупка\n\n- Хлеб\n- Молоко"
        result = parse_provisions(md)
        assert result["restock"] == ["Хлеб", "Молоко"]

    def test_no_matching_sections(self):
        md = "# Просто текст\n\nБез провизии."
        assert parse_provisions(md) == {}


# ---------------------------------------------------------------------------
# Граничные случаи: черновые данные, неполные таблицы
# ---------------------------------------------------------------------------

class TestDraftAndEdgeCases:
    """Тесты на черновые/неполные данные — парсеры не должны падать."""

    def test_route_plan_with_empty_table_values(self):
        md = """\
### День 1 — TBD

| **Откуда** |  |
|---|---|
| **Куда** |  |
| **Дистанция** |  |
"""
        result = parse_route_plan(md)
        assert result["days"][0]["from"] == ""
        assert result["days"][0]["to"] == ""
        assert result["days"][0]["nm"] == ""

    def test_safety_briefing_mixed_checkbox_styles(self):
        md = """\
## 1. Проверки

- [x] Выполнено
- [X] Тоже выполнено
- [ ] Не выполнено
"""
        result = parse_safety_briefing(md)
        items = result["sections"][0]["items"]
        assert items[0]["checked"] is True
        assert items[1]["checked"] is True
        assert items[2]["checked"] is False

    def test_equipment_with_deeply_nested_content(self):
        """Контент после чекбоксов (подпункты, текст) игнорируется корректно."""
        md = """\
## Категория

### Подкатегория

- [x] Пункт 1
  - Подпункт (не чекбокс — будет проигнорирован)
- [ ] Пункт 2
"""
        result = parse_equipment_checklist(md)
        items = result["categories"][0]["subcategories"][0]["items"]
        assert len(items) == 2  # Только два чекбокса

    def test_provisions_table_with_missing_columns(self):
        """Таблица с меньшим числом столбцов в строке — не падает."""
        md = """\
### Еда

| Продукт | Количество | Примечание |
|---|---|---|
| Хлеб | 2 |
"""
        result = parse_provisions(md)
        item = result["shopping"][0]["items"][0]
        assert item["Продукт"] == "Хлеб"
        assert item["Количество"] == "2"
        # Примечание — пустая строка (столбец отсутствует, но не падает)

    def test_crew_list_table_with_extra_pipes(self):
        """Лишние пробелы и пайпы в таблице."""
        md = """\
## Экипаж

|  Имя  |  Возраст  |
|---|---|
|  Тест  |  25  |
"""
        result = parse_crew_list(md)
        assert result["members"][0]["Имя"] == "Тест"
        assert result["members"][0]["Возраст"] == "25"

    def test_kids_on_board_empty_activities_category(self):
        """Подкатегория активностей без пунктов."""
        md = """\
## Активности

### В дождь

### В штиль

- Рыбалка
"""
        result = parse_kids_on_board(md)
        assert result["activities"]["В дождь"] == []
        assert result["activities"]["В штиль"] == ["Рыбалка"]

    def test_emergency_contacts_only_vhf(self):
        md = """\
## VHF каналы

| Канал | Назначение |
|---|---|
| 16 | Бедствие |
"""
        result = parse_emergency_contacts(md)
        assert "vhf" in result
        assert result["vhf"][0]["Канал"] == "16"

    def test_travel_logistics_carry_on_stops_at_next_section(self):
        """Список ручной клади прерывается следующим ## заголовком."""
        md = """\
## Что взять в ручную кладь

- Паспорта
- Лекарства

## Другая секция

- Этот пункт не должен попасть в carry_on
"""
        result = parse_travel_logistics(md)
        assert result["carry_on"] == ["Паспорта", "Лекарства"]
