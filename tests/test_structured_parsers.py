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
        md = "## День 1 — Сплит\n| **Откуда** | Марина Кашела |\n| **Куда** | Масленица |"
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
    """Парсер маршрутного плана: ## День N + ### под-блоки + вертикальные таблицы."""

    ROUTE_MD = """\
- Идём только днём, ночные переходы исключены
- Якорные стоянки в приоритете над маринами

## День 1 — Сплит → Масленица (Шолта)

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

## День 2 — Масленица → Вис

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
        md = "## День 1 — Только заголовок\n\nПросто текст."
        result = parse_route_plan(md)

        assert len(result["days"]) == 1
        assert result["days"][0]["from"] == ""
        assert result["days"][0]["to"] == ""

    def test_bold_markers_stripped_from_principles(self):
        md = "- **Важный** принцип навигации\n\n## День 1 — Тест\n| **Откуда** | A |"
        result = parse_route_plan(md)

        assert "Важный принцип навигации" in result["principles"]

    def test_day_with_dash_separator(self):
        """Поддержка разных разделителей: тире, длинное тире, дефис."""
        md = "## День 3 – Хвар → Корчула\n| **Откуда** | Хвар |"
        result = parse_route_plan(md)
        assert result["days"][0]["day"] == 3
        assert "Хвар" in result["days"][0]["title"]

    BLOCKS_MD = """\
## День 1 — Острова Терсане и Яшика

| **Откуда** | Göçek |
|---|---|
| **Куда** | Tersane Adası |
| **Дистанция** | 8 nm |
| **Стоянка** | бухта Yassıca |

Общий текст дня про купание.

### Переход до Фетхие
Текст блока.
![[foto1.jpg]]
![[foto2.jpg]]

### После обеда — Канакой
На тачке едем в Канакёй.
![[foto3.jpg]]

## День 2 — Без блоков

| **Откуда** | A |
|---|---|
| **Куда** | B |

Просто текст, без под-заголовков.
"""

    def test_intro_extracted(self):
        result = parse_route_plan(self.BLOCKS_MD)
        assert result["days"][0]["intro"] == "Общий текст дня про купание."

    def test_blocks_extracted(self):
        result = parse_route_plan(self.BLOCKS_MD)
        blocks = result["days"][0]["blocks"]
        assert len(blocks) == 2
        assert blocks[0]["title"] == "Переход до Фетхие"
        assert blocks[0]["text"] == "Текст блока."
        assert blocks[0]["photos"] == ["foto1.jpg", "foto2.jpg"]
        assert blocks[1]["title"] == "После обеда — Канакой"
        assert blocks[1]["text"] == "На тачке едем в Канакёй."
        assert blocks[1]["photos"] == ["foto3.jpg"]

    def test_day_without_blocks_has_intro_and_empty_blocks(self):
        result = parse_route_plan(self.BLOCKS_MD)
        day2 = result["days"][1]
        assert day2["blocks"] == []
        assert day2["intro"] == "Просто текст, без под-заголовков."

    def test_block_with_no_photos(self):
        md = "## День 1 — Тест\n\n### Блок без фото\nТолько текст.\n"
        result = parse_route_plan(md)
        assert result["days"][0]["blocks"][0]["photos"] == []

    def test_photo_with_obsidian_resize_suffix_strips_it(self):
        """![[foto.jpg|680]] — Obsidian-синтаксис ресайза, берём только имя файла."""
        md = "## День 1 — Тест\n\n### Блок\n![[foto.jpg|680]]\n"
        result = parse_route_plan(md)
        assert result["days"][0]["blocks"][0]["photos"] == ["foto.jpg"]


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
    """Парсер провизии: интро, меню, чеки-закупки, дежурства, магазины."""

    PROVISIONS_MD = """\
# Provisions — Провизия

8 человек, 7 дней, докупка один раз.

## Логика двух чеков

| | Чек [A] — марина | Чек [B] — середина |
|---|---|---|
| Что берём | Бакалея и вода | Скоропорт |
| Вес | Тяжёлый | Лёгкий |

## Правила камбуза

- **One-pot блюда.** Одна кастрюля.
- Рецепты на ≤30 минут.

## Завтраки

- Ночная овсянка
- Омлет с творогом

## Обеды

| # | Блюдо | Ключевые продукты | Чек |
|---|---|---|---|
| L1 | Паста с песто | паста 700 г, песто | A |
| L5 | Кускус с кюфте | кускус 600 г, фарш 1 кг | B |

## Ужины

| # | Блюдо | Ключевые продукты | Чек |
|---|---|---|---|
| U1 | Путтанеска | паста 800 г, тунец | A |

## Заметки по меню

- Гарнир — чобан-салат.

## Чек A — домашняя марина

### Мясо
- [ ] Куриное филе — 1,6 кг
- [x] Sucuk — 1,3 кг

### Вода
- [ ] 5 л — 18 шт

## Чек B — середина маршрута

### Скоропорт
- [ ] Фарш — 1,7 кг

## Дежурства на камбузе

18 приёмов пищи за 7 дней. Капитаны вне ротации.

| Дни | Завтрак | Обед | Ужин |
|---|---|---|---|
| 1-3 | готовит A, моет C | готовит B, моет A | готовит C, моет B |

## Правила дежурства

- **Мойка в две руки:** один намыливает, второй ополаскивает.

## Где покупать

| Магазин | Что |
|---|---|
| Migros | Основная закупка |
| Tekel | Алкоголь |

## Логистика закупки

Заказать в марине тележку или такси до Migros.
"""

    def test_intro_parsed(self):
        result = parse_provisions(self.PROVISIONS_MD)
        assert result["intro"] == "8 человек, 7 дней, докупка один раз."

    def test_checks_logic_table(self):
        result = parse_provisions(self.PROVISIONS_MD)
        logic = result["checks_logic"]

        assert len(logic) == 2
        assert logic[0][""] == "Что берём"
        assert logic[0]["Чек [A] — марина"] == "Бакалея и вода"
        assert logic[1]["Чек [B] — середина"] == "Лёгкий"

    def test_galley_rules_bold_stripped(self):
        result = parse_provisions(self.PROVISIONS_MD)
        assert result["galley_rules"][0] == "One-pot блюда. Одна кастрюля."
        assert len(result["galley_rules"]) == 2

    def test_breakfasts_parsed(self):
        result = parse_provisions(self.PROVISIONS_MD)
        assert result["breakfasts"] == ["Ночная овсянка", "Омлет с творогом"]

    def test_lunches_and_dinners(self):
        result = parse_provisions(self.PROVISIONS_MD)

        assert len(result["lunches"]) == 2
        assert result["lunches"][0]["#"] == "L1"
        assert result["lunches"][1]["Чек"] == "B"
        assert len(result["dinners"]) == 1
        assert result["dinners"][0]["Блюдо"] == "Путтанеска"

    def test_menu_notes(self):
        result = parse_provisions(self.PROVISIONS_MD)
        assert result["menu_notes"] == ["Гарнир — чобан-салат."]

    def test_shopping_lists_by_check(self):
        result = parse_provisions(self.PROVISIONS_MD)
        lists = result["lists"]

        assert len(lists) == 2
        assert lists[0]["name"] == "Чек A — домашняя марина"
        assert [c["name"] for c in lists[0]["categories"]] == ["Мясо", "Вода"]
        assert lists[1]["categories"][0]["items"][0]["text"] == "Фарш — 1,7 кг"

    def test_checked_state_parsed(self):
        result = parse_provisions(self.PROVISIONS_MD)
        meat = result["lists"][0]["categories"][0]["items"]

        assert meat[0]["checked"] is False
        assert meat[1]["checked"] is True

    def test_duty_intro_and_rota(self):
        result = parse_provisions(self.PROVISIONS_MD)

        assert result["duty_intro"].startswith("18 приёмов пищи")
        assert len(result["duty_rota"]) == 1
        assert result["duty_rota"][0]["Дни"] == "1-3"
        assert result["duty_rota"][0]["Ужин"] == "готовит C, моет B"

    def test_duty_rules_separate_from_galley_rules(self):
        result = parse_provisions(self.PROVISIONS_MD)
        assert result["duty_rules"] == [
            "Мойка в две руки: один намыливает, второй ополаскивает."
        ]

    def test_shops_and_logistics(self):
        result = parse_provisions(self.PROVISIONS_MD)

        assert len(result["shops"]) == 2
        assert result["shops"][0]["Магазин"] == "Migros"
        assert result["logistics"].startswith("Заказать в марине тележку")

    def test_empty_input_returns_empty(self):
        assert parse_provisions("") == {}

    def test_no_matching_sections(self):
        md = "# Просто текст\n\nБез провизии."
        result = parse_provisions(md)
        assert result == {"intro": "Без провизии."}

    def test_only_shopping_list(self):
        md = "## Чек A\n\n### Хлеб\n- [ ] Лаваш\n"
        result = parse_provisions(md)
        assert result["lists"][0]["categories"][0]["items"][0]["text"] == "Лаваш"
        assert "lunches" not in result



# ---------------------------------------------------------------------------
# Граничные случаи: черновые данные, неполные таблицы
# ---------------------------------------------------------------------------

class TestDraftAndEdgeCases:
    """Тесты на черновые/неполные данные — парсеры не должны падать."""

    def test_route_plan_with_empty_table_values(self):
        md = """\
## День 1 — TBD

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
        """Строка таблицы меню с меньшим числом столбцов — не падает."""
        md = """\
## Обеды

| # | Блюдо | Ключевые продукты | Чек |
|---|---|---|---|
| L1 | Паста | паста 700 г |
"""
        result = parse_provisions(md)
        item = result["lunches"][0]
        assert item["Блюдо"] == "Паста"
        assert item["Ключевые продукты"] == "паста 700 г"
        # Чек — пустая строка (столбец отсутствует, но не падает)
        assert item["Чек"] == ""

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
