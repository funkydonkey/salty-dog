# Route Plan: Per-Day Blocks + Photos Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the captain author `Route plan.md` day-by-day in Obsidian, splitting each day into free-titled sub-blocks (prose + optional photos), rendered as a swipe carousel on the site.

**Architecture:** Day heading moves `###` → `##` so `###` is free for sub-blocks. `parse_route_plan` gains `intro` (day prose before first block) and `blocks` (list of `{title, text, photos}`, photos as raw `![[filename]]` basenames). A new `app/content/image_pipeline.py` resolves those basenames against the whole vault (Obsidian-style, folder-agnostic), resizes/re-encodes with Pillow, and copies into both hosting targets' asset dirs. `builder.py` calls it after parsing the route page, mutating `structured_data` photo lists from raw filenames to served relative paths (`route/<slug>.jpg`). Both `index.html` files get a `SALTY_ASSET_BASE` global (mirrors the existing `SALTY_CONTENT_URL` override pattern) so the same `content.json` works on Render (`/assets/`) and GitHub Pages (`static/assets/`). `renderRoutePlan` in `templates.js` renders intro + blocks + a pure-CSS scroll-snap carousel — no JS carousel library.

**Tech Stack:** Python 3.11, FastAPI, Pillow (new), pytest, vanilla JS, CSS scroll-snap.

## Global Constraints

- Day heading regex: `## День N — заголовок` (was `###`); sub-blocks: `### заголовок`.
- Photos referenced as `![[filename.jpg]]`, resolved by basename anywhere in the vault (`vault_path.rglob(filename)`), not a fixed attachments folder.
- Image processing: max dimension 1600px, JPEG quality 80, via Pillow — build-time only, not a runtime dependency of FastAPI requests.
- Missing image or missing Pillow → log warning, skip that photo, never fail the build (matches existing "file not found → skip, log" pattern in `builder.py`).
- Output goes to both `frontend/assets/route/` (Render, served via existing `/assets` mount) and `docs/static/assets/route/` (GitHub Pages mirror) — same processed bytes in both.
- `content.json` stores photo paths as `route/<slug>.jpg` (relative fragment, no leading slash, no host prefix) — each frontend prepends its own `SALTY_ASSET_BASE`.
- No new runtime JS dependencies; carousel is pure CSS (`overflow-x: auto; scroll-snap-type: x mandatory`).

---

### Task 1: Add Pillow dependency

**Files:**
- Modify: `pyproject.toml`

**Interfaces:**
- Produces: `PIL.Image` importable in `app/content/image_pipeline.py` (Task 3).

- [ ] **Step 1: Add Pillow to dependencies**

In `pyproject.toml`, in the `dependencies` list, add after `"pyyaml>=6.0",`:

```toml
    "pillow>=11.0.0",
```

- [ ] **Step 2: Install**

Run: `uv sync`
Expected: resolves and installs `pillow` with no errors.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml uv.lock
git commit -m "chore: add Pillow for route photo processing"
```

---

### Task 2: Update `parse_route_plan` — day heading, intro, blocks

**Files:**
- Modify: `app/content/structured_parsers.py:147-199` (`parse_route_plan`)
- Test: `tests/test_structured_parsers.py` (`TestParseRoutePlan` class, currently lines ~68-169)

**Interfaces:**
- Produces: `parse_route_plan(md: str) -> dict` returning:
  ```python
  {
    "days": [
      {
        "day": int, "title": str,
        "from": str, "to": str, "nm": str, "course": str, "anchorage": str,
        "highlights": str, "kids": str, "note": str,
        "bullets": list[str],
        "intro": str,
        "blocks": [{"title": str, "text": str, "photos": list[str]}, ...],
      }, ...
    ],
    "principles": list[str],
  }
  ```
  `photos` entries are raw filenames as written in `![[filename.jpg]]` (Task 3/4 resolve these into served paths later — this parser stays pure-text).

- [ ] **Step 1: Update existing test fixtures to the new heading level**

In `tests/test_structured_parsers.py`, in `TestParseRoutePlan.ROUTE_MD`, replace every `### День` with `## День` (there are two: "День 1" and "День 2"). Do the same in every other test in the class that hand-writes a `### День` string: `test_day_without_table`, `test_bold_markers_stripped_from_principles`, `test_day_with_dash_separator`. After this step the whole class should look identical except `###` → `##` in day headings; do not touch the class docstring yet (next step).

- [ ] **Step 2: Update the class docstring and run to confirm the expected RED**

Change the docstring on `TestParseRoutePlan` from `"""Парсер маршрутного плана: ### День N + вертикальные таблицы."""` to `"""Парсер маршрутного плана: ## День N + ### под-блоки + вертикальные таблицы."""`.

Run: `uv run pytest tests/test_structured_parsers.py -k TestParseRoutePlan -v`
Expected: FAIL — current parser still splits on `### ` so it finds zero days (headings are now `##`, but old code looks for `###` and would instead find nothing, or misparse). Confirms the fixtures now exercise the new format.

- [ ] **Step 3: Add new tests for intro + blocks + photos onto the same class**

Append to `TestParseRoutePlan` in `tests/test_structured_parsers.py`:

```python
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
```

- [ ] **Step 4: Run to verify these fail too**

Run: `uv run pytest tests/test_structured_parsers.py -k TestParseRoutePlan -v`
Expected: FAIL (KeyError on `intro`/`blocks` or wrong day count) — implementation not updated yet.

- [ ] **Step 5: Rewrite `parse_route_plan`**

Replace `app/content/structured_parsers.py:147-199` (the whole `parse_route_plan` function) with:

```python
def parse_route_plan(md: str) -> dict:
    """Парсит Route plan: ## День N заголовки, вертикальные таблицы,
    и вложенные ### под-блоки (текст + фото ![[файл.jpg]])."""
    days = []
    day_sections = re.split(r"^## ", md, flags=re.MULTILINE)

    for section in day_sections[1:]:  # Пропускаем текст до первого ##
        lines = section.split("\n")
        header = lines[0].strip()

        day_match = re.match(r"День\s+(\d+)\s*[—–-]?\s*(.*)", header)
        if not day_match:
            continue

        day_num = int(day_match.group(1))
        title = day_match.group(2).strip()
        body = "\n".join(lines[1:])

        # Делим тело дня на intro (до первого ###) и под-блоки
        block_parts = re.split(r"^### ", body, flags=re.MULTILINE)
        intro_raw_lines = block_parts[0].split("\n")

        table_data = _parse_vertical_table(intro_raw_lines)

        bullets = []
        intro_prose_lines = []
        for line in intro_raw_lines:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("|"):
                continue
            if stripped.startswith("- "):
                bullets.append(_clean_bold(stripped[2:]))
                continue
            intro_prose_lines.append(stripped)
        intro = " ".join(intro_prose_lines).strip()

        blocks = []
        for block_part in block_parts[1:]:
            block_lines = block_part.split("\n")
            block_title = block_lines[0].strip()
            photos = []
            text_lines = []
            for line in block_lines[1:]:
                stripped = line.strip()
                if not stripped:
                    continue
                photo_match = re.match(r"!\[\[(.+?)\]\]", stripped)
                if photo_match:
                    photos.append(photo_match.group(1))
                    continue
                text_lines.append(stripped)
            blocks.append({
                "title": block_title,
                "text": _clean_bold(" ".join(text_lines).strip()),
                "photos": photos,
            })

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
            "intro": intro,
            "blocks": blocks,
        }
        days.append(day)

    if not days:
        return {}

    # Извлекаем общие принципы (текст до первого ##)
    principles = []
    for line in md.split("## ")[0].split("\n"):
        stripped = line.strip()
        if stripped.startswith("- "):
            principles.append(_clean_bold(stripped[2:]))

    return {"days": days, "principles": principles}
```

Note: `text_lines` join with `_clean_bold` reuses the existing helper at `app/content/structured_parsers.py:138` — no new helper needed.

- [ ] **Step 6: Run full test file to verify everything passes**

Run: `uv run pytest tests/test_structured_parsers.py -v`
Expected: PASS — all `TestParseRoutePlan` tests including the pre-existing ones (now on `##`) and the new intro/blocks/photos tests. Also re-check the dispatcher tests (`TestExtractStructuredData`) and any other class in the file still pass (they don't touch route_plan format).

- [ ] **Step 7: Run the full suite for regressions**

Run: `uv run pytest tests/ -v`
Expected: PASS. If `tests/test_builder.py` or `tests/test_integration.py` embed a `### День` fixture, fix it the same way (`###` → `##`) before moving on.

- [ ] **Step 8: Commit**

```bash
git add app/content/structured_parsers.py tests/test_structured_parsers.py
git commit -m "feat: parse route plan day sub-blocks with intro text and photo refs"
```

---

### Task 3: Vault image resolver + processor

**Files:**
- Create: `app/content/image_pipeline.py`
- Test: `tests/test_image_pipeline.py`

**Interfaces:**
- Consumes: nothing from earlier tasks (pure new module, only stdlib + Pillow + `pathlib.Path`).
- Produces (used by Task 4):
  - `resolve_vault_image(vault_path: Path, filename: str) -> Path | None`
  - `slugify_filename(filename: str) -> str`
  - `process_route_photos(vault_path: Path, filenames: list[str], output_dirs: list[Path]) -> dict[str, str]` — returns `{original_filename: "route/<slug>.jpg"}` for every filename it could resolve and process; filenames it couldn't resolve are simply absent from the returned dict (caller checks membership).

- [ ] **Step 1: Write the failing tests**

Create `tests/test_image_pipeline.py`:

```python
"""Тесты для поиска и обработки фото маршрута из vault."""

from pathlib import Path

import pytest
from PIL import Image

from app.content.image_pipeline import (
    process_route_photos,
    resolve_vault_image,
    slugify_filename,
)


def _make_test_image(path: Path, size: tuple[int, int] = (2000, 1000)) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color=(200, 100, 50)).save(path)


class TestResolveVaultImage:
    def test_finds_image_in_nested_folder(self, tmp_path):
        img = tmp_path / "attachments" / "sub" / "foto1.jpg"
        _make_test_image(img)
        found = resolve_vault_image(tmp_path, "foto1.jpg")
        assert found == img

    def test_finds_image_at_vault_root(self, tmp_path):
        img = tmp_path / "foto2.jpg"
        _make_test_image(img)
        found = resolve_vault_image(tmp_path, "foto2.jpg")
        assert found == img

    def test_missing_image_returns_none(self, tmp_path):
        assert resolve_vault_image(tmp_path, "nope.jpg") is None


class TestSlugifyFilename:
    def test_strips_extension_and_slugifies(self):
        assert slugify_filename("IMG 0012 (Göcek).jpg") == "img-0012-g-cek"

    def test_empty_stem_falls_back(self):
        assert slugify_filename(".jpg") == "photo"


class TestProcessRoutePhotos:
    def test_resizes_and_copies_to_all_output_dirs(self, tmp_path):
        img = tmp_path / "vault" / "foto1.jpg"
        _make_test_image(img, size=(3000, 1500))
        out1 = tmp_path / "out1"
        out2 = tmp_path / "out2"

        result = process_route_photos(tmp_path / "vault", ["foto1.jpg"], [out1, out2])

        assert "foto1.jpg" in result
        served_path = result["foto1.jpg"]
        assert served_path.startswith("route/")
        assert served_path.endswith(".jpg")

        for out_dir in (out1, out2):
            written = out_dir / served_path
            assert written.exists()
            with Image.open(written) as processed:
                assert max(processed.size) <= 1600

    def test_missing_image_omitted_from_result(self, tmp_path):
        out1 = tmp_path / "out1"
        result = process_route_photos(tmp_path / "vault", ["missing.jpg"], [out1])
        assert "missing.jpg" not in result

    def test_duplicate_basenames_get_distinct_slugs(self, tmp_path):
        (tmp_path / "vault" / "a").mkdir(parents=True)
        (tmp_path / "vault" / "b").mkdir(parents=True)
        _make_test_image(tmp_path / "vault" / "a" / "same.jpg")
        # Two different files, but resolve_vault_image only ever sees one
        # basename per call — this test documents that the second identical
        # filename in a different folder is unreachable via basename lookup,
        # matching Obsidian's own last-match-wins resolution.
        result = process_route_photos(tmp_path / "vault", ["same.jpg"], [tmp_path / "out"])
        assert "same.jpg" in result
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_image_pipeline.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.content.image_pipeline'`.

- [ ] **Step 3: Implement `app/content/image_pipeline.py`**

```python
"""Резолвит фото маршрута из Obsidian-vault по имени файла (как сам Obsidian —
без привязки к папке), ресайзит и копирует в статические ассеты сборки."""

import re
from pathlib import Path

from PIL import Image

MAX_DIMENSION = 1600
JPEG_QUALITY = 80
ASSET_SUBDIR = "route"


def resolve_vault_image(vault_path: Path, filename: str) -> Path | None:
    """Ищет файл по имени рекурсивно по всему vault. При нескольких
    совпадениях берёт первое найденное (порядок файловой системы)."""
    matches = list(vault_path.rglob(filename))
    return matches[0] if matches else None


def slugify_filename(filename: str) -> str:
    """'IMG 0012 (Göcek).jpg' -> 'img-0012-g-cek'."""
    stem = Path(filename).stem
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", stem).strip("-").lower()
    return slug or "photo"


def _resize_and_save(source: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as img:
        img = img.convert("RGB")
        img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.LANCZOS)
        img.save(dest, "JPEG", quality=JPEG_QUALITY)


def process_route_photos(
    vault_path: Path, filenames: list[str], output_dirs: list[Path]
) -> dict[str, str]:
    """Резолвит, ресайзит и копирует каждое фото во все output_dirs.

    Возвращает {исходное_имя_файла: относительный_путь_в_ассетах},
    например {"foto1.jpg": "route/foto1.jpg"}. Файлы, которые не удалось
    найти в vault, в результат не попадают — вызывающий код сам решает,
    что делать (обычно просто опускает фото из блока).
    """
    result: dict[str, str] = {}
    used_slugs: set[str] = set()

    for filename in filenames:
        source = resolve_vault_image(vault_path, filename)
        if source is None:
            print(f"  [!] Фото не найдено в vault: {filename} — пропущено")
            continue

        slug = slugify_filename(filename)
        candidate = slug
        suffix = 2
        while candidate in used_slugs:
            candidate = f"{slug}-{suffix}"
            suffix += 1
        used_slugs.add(candidate)

        served_path = f"{ASSET_SUBDIR}/{candidate}.jpg"

        try:
            for output_dir in output_dirs:
                dest = output_dir / ASSET_SUBDIR / f"{candidate}.jpg"
                _resize_and_save(source, dest)
        except Exception as exc:  # noqa: BLE001 — не роняем сборку из-за одного фото
            print(f"  [!] Не удалось обработать фото {filename}: {exc}")
            continue

        result[filename] = served_path

    return result
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_image_pipeline.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add app/content/image_pipeline.py tests/test_image_pipeline.py
git commit -m "feat: resolve and process route plan photos from vault"
```

---

### Task 4: Wire photo processing into the builder

**Files:**
- Modify: `app/content/builder.py`
- Test: `tests/test_builder.py`

**Interfaces:**
- Consumes: `process_route_photos(vault_path, filenames, output_dirs) -> dict[str, str]` from Task 3.
- Produces: after `build_content()`, any `ContentPage` with `template == "route_plan"` has its `structured_data["days"][*]["blocks"][*]["photos"]` entries replaced from raw filenames (`"foto1.jpg"`) to served paths (`"route/foto1.jpg"`) — unresolvable photos are dropped from the list, not left as raw filenames.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_builder.py` (check the file's existing fixtures for how a temp vault is constructed — reuse that pattern; if it uses a `tmp_path`-based vault fixture already, follow the same `_app.yaml` + markdown file layout). Add:

```python
def test_route_plan_photos_resolved_and_copied(tmp_path):
    from PIL import Image

    from app.content.builder import build_content

    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "_app.yaml").write_text(
        "trip:\n  name: Test\n"
        "sections:\n"
        "  - id: route\n"
        "    title: Маршрут\n"
        "    icon: 🗺️\n"
        "    tab: map\n"
        "    files:\n"
        "      - file: Route plan\n"
        "        template: route_plan\n",
        encoding="utf-8",
    )
    (vault / "Route plan.md").write_text(
        "## День 1 — Тест\n\n"
        "| **Откуда** | A |\n"
        "|---|---|\n\n"
        "### Блок\n"
        "Текст.\n"
        "![[foto1.jpg]]\n",
        encoding="utf-8",
    )
    attachments = vault / "attachments"
    attachments.mkdir()
    Image.new("RGB", (2000, 1000), color=(10, 20, 30)).save(attachments / "foto1.jpg")

    import app.content.builder as builder_module
    output_dir1 = tmp_path / "assets1"
    output_dir2 = tmp_path / "assets2"
    monkey_dirs = [output_dir1, output_dir2]

    bundle = build_content(vault, route_photo_output_dirs=monkey_dirs)

    route_page = bundle.sections[0].pages[0]
    photos = route_page.structured_data["days"][0]["blocks"][0]["photos"]
    assert photos == ["route/foto1.jpg"]
    assert (output_dir1 / "route" / "foto1.jpg").exists()
    assert (output_dir2 / "route" / "foto1.jpg").exists()
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/test_builder.py::test_route_plan_photos_resolved_and_copied -v`
Expected: FAIL — `build_content()` doesn't accept `route_photo_output_dirs` yet.

- [ ] **Step 3: Extend `build_content` and `_build_sections`**

In `app/content/builder.py`, add the import at the top (near the existing `from app.content.route_parser import extract_waypoints`):

```python
from app.content.image_pipeline import process_route_photos
```

Replace the `_build_sections` signature and the loop body where pages are built (`app/content/builder.py:38-77`, the `_build_sections` function) — change the signature to accept output dirs and, right after `pages.append(page)`, add photo resolution for route_plan pages:

```python
def _build_sections(
    vault_path: Path,
    sections_config: list[dict],
    route_photo_output_dirs: list[Path],
) -> tuple[list[Section], Route]:
    """Собирает секции и маршрут из конфигурации."""
    sections = []
    all_waypoints = []

    for section_cfg in sections_config:
        pages = []
        file_entries = section_cfg.get("files", [])

        for entry in file_entries:
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

            if template == "route_plan":
                _resolve_route_photos(page, vault_path, route_photo_output_dirs)

            pages.append(page)

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


def _resolve_route_photos(page, vault_path: Path, output_dirs: list[Path]) -> None:
    """Заменяет сырые имена файлов фото в structured_data на пути в ассетах
    (или убирает фото, если файл не нашёлся в vault)."""
    days = page.structured_data.get("days", [])
    all_filenames = [
        filename
        for day in days
        for block in day.get("blocks", [])
        for filename in block.get("photos", [])
    ]
    if not all_filenames or not output_dirs:
        return

    resolved = process_route_photos(vault_path, all_filenames, output_dirs)

    for day in days:
        for block in day.get("blocks", []):
            block["photos"] = [
                resolved[name] for name in block["photos"] if name in resolved
            ]
```

Now update `build_content` (`app/content/builder.py`, the function right after `_compute_hash`) to accept and forward the output dirs, defaulting to the real project paths:

```python
def build_content(
    vault_path: str | Path,
    route_photo_output_dirs: list[Path] | None = None,
) -> ContentBundle:
    """Главная функция: собирает ContentBundle из vault."""
    vault = Path(vault_path)
    if not vault.is_dir():
        raise FileNotFoundError(f"Vault не найден: {vault}")

    if route_photo_output_dirs is None:
        project_root = Path(__file__).resolve().parent.parent.parent
        route_photo_output_dirs = [
            project_root / "frontend" / "assets",
            project_root / "docs" / "static" / "assets",
        ]

    config = _load_app_config(vault)

    trip = TripConfig(**config.get("trip", {}))
    sections, route = _build_sections(vault, config.get("sections", []), route_photo_output_dirs)

    bundle = ContentBundle(
        trip=trip,
        sections=sections,
        route=route,
    )
    content_hash = _compute_hash(bundle)
    bundle = bundle.model_copy(update={"content_hash": content_hash})

    return bundle
```

- [ ] **Step 4: Run to verify it passes**

Run: `uv run pytest tests/test_builder.py -v`
Expected: PASS.

- [ ] **Step 5: Run the full suite**

Run: `uv run pytest tests/ -v`
Expected: PASS — in particular re-check `tests/test_integration.py` still passes now that `build_content` writes real files as a side effect when called without explicit `route_photo_output_dirs` in any integration test; if such a test calls `build_content(vault)` directly without a route_plan template page, it's unaffected (the early-return in `_resolve_route_photos` when `all_filenames` is empty skips all file I/O).

- [ ] **Step 6: Commit**

```bash
git add app/content/builder.py tests/test_builder.py
git commit -m "feat: process and copy route plan photos during content build"
```

---

### Task 5: Asset base URL wiring + carousel rendering

**Files:**
- Modify: `frontend/index.html`
- Modify: `docs/index.html`
- Modify: `frontend/js/templates.js` (`renderRoutePlan`, `frontend/js/templates.js:94-173`)
- Modify: `frontend/css/templates.css`

**Interfaces:**
- Consumes: `window.SALTY_ASSET_BASE` (new global), `day.intro: string`, `day.blocks: [{title, text, photos: string[]}]` from Task 2/4 (photos are already served paths like `"route/foto1.jpg"` by the time JS sees them).

- [ ] **Step 1: Add `SALTY_ASSET_BASE` to `frontend/index.html`**

In `frontend/index.html`, this file currently has no inline `<script>` setting globals before the app scripts load (unlike `docs/index.html`). Add one right before the `<!-- App CSS -->` comment (after the Leaflet CSS `<link>`, matching where `docs/index.html` places its override block):

```html
  <!-- Asset base: Render serves vault photos under the /assets mount -->
  <script>
    window.SALTY_ASSET_BASE = '/assets/';
  </script>

```

- [ ] **Step 2: Add `SALTY_ASSET_BASE` to `docs/index.html`**

In `docs/index.html`, inside the existing inline `<script>` block (currently lines 39-42, the one setting `SALTY_CONTENT_URL`/`SALTY_VERSION_URL`), add a third line:

```html
  <script>
    window.SALTY_CONTENT_URL = 'static/content.json';
    window.SALTY_VERSION_URL = 'static/content.json';
    window.SALTY_ASSET_BASE = 'static/assets/';
  </script>
```

- [ ] **Step 3: Update `renderRoutePlan` to render intro + blocks + carousel**

In `frontend/js/templates.js`, inside the day loop in `renderRoutePlan` (`frontend/js/templates.js:94-173`), insert the intro/blocks rendering after the existing badges block and before the `isEmpty` placeholder check (i.e. right after line 162 `html += '</div>';` that closes `.timeline__badges`, before line 164 `if (isEmpty) {`). Also update the `isEmpty` computation on line 109. Replace:

```javascript
      var isEmpty = !hasValue(d.from) && !hasValue(d.to) && d.bullets.length === 0;
```

with:

```javascript
      var isEmpty = !hasValue(d.from) && !hasValue(d.to) && d.bullets.length === 0 &&
                    !hasValue(d.intro) && (d.blocks || []).length === 0;
```

Then insert right before the `if (isEmpty) {` line:

```javascript
      if (hasValue(d.intro)) {
        html += '<p class="route-block__day-intro">' + escLink(d.intro) + '</p>';
      }

      var blocks = d.blocks || [];
      for (var bi2 = 0; bi2 < blocks.length; bi2++) {
        var block = blocks[bi2];
        html += '<div class="route-block">';
        html += '<div class="route-block__title">' + escLink(block.title) + '</div>';
        if (hasValue(block.text)) {
          html += '<p class="route-block__text">' + escLink(block.text) + '</p>';
        }
        var photos = block.photos || [];
        if (photos.length > 0) {
          html += '<div class="route-block__carousel">';
          for (var pi = 0; pi < photos.length; pi++) {
            var assetBase = window.SALTY_ASSET_BASE || '/assets/';
            html += '<img class="route-block__photo" src="' + assetBase + photos[pi] + '" alt="' + escLink(block.title) + '" loading="lazy">';
          }
          html += '</div>';
          if (photos.length > 1) {
            html += '<div class="route-block__dots">';
            for (var di = 0; di < photos.length; di++) {
              html += '<span class="route-block__dot"></span>';
            }
            html += '</div>';
          }
        }
        html += '</div>';
      }
```

- [ ] **Step 4: Add carousel CSS**

Append to `frontend/css/templates.css`:

```css
/* route_plan — day sub-blocks with photo carousel */
.route-block__day-intro {
  margin: 8px 0 4px;
  color: var(--text-secondary, #555);
}

.route-block {
  margin-top: 16px;
  padding-top: 12px;
  border-top: 1px solid var(--border-color, #e5e5e5);
}

.route-block__title {
  font-weight: 700;
  margin-bottom: 4px;
}

.route-block__text {
  margin: 0 0 8px;
}

.route-block__carousel {
  display: flex;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  gap: 8px;
  -webkit-overflow-scrolling: touch;
}

.route-block__photo {
  flex: 0 0 85%;
  scroll-snap-align: start;
  border-radius: 12px;
  max-height: 240px;
  object-fit: cover;
  width: 85%;
}

.route-block__dots {
  display: flex;
  justify-content: center;
  gap: 6px;
  margin-top: 6px;
}

.route-block__dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--border-color, #d0d0d0);
}
```

- [ ] **Step 5: Manual smoke test**

Run: `uv run make build` (uses real vault — will process zero photos until the captain adds `### ` blocks with `![[...]]` to the real `Route plan.md`, that's expected and fine).
Then: `uv run make dev`, open `http://localhost:8000`, confirm the Маршрут tab still renders (empty-route placeholder if the real note has no `## День` headings yet, or existing day cards unaffected if it does).

Write a temporary scratch day into the real vault's `Route plan.md` (or a throwaway copy) with one `###` block and a real photo dropped into the vault, rerun `make build`, reload, confirm: block text renders, single photo renders full-width without dots, and (if you add a 2nd photo) the carousel swipes horizontally with dots showing on a narrow browser window / device emulation. Remove the scratch content afterward if it was only for testing — leave the real content decisions to the captain.

- [ ] **Step 6: Commit**

```bash
git add frontend/index.html docs/index.html frontend/js/templates.js frontend/css/templates.css
git commit -m "feat: render route plan day sub-blocks and photo carousel"
```

---

### Task 6: Sync GitHub Pages mirror and publish

**Files:**
- Modify: `Makefile`

**Interfaces:**
- Consumes: `frontend/assets/route/*.jpg` and `docs/static/assets/route/*.jpg` written by Task 4's build step.

- [ ] **Step 1: Extend `publish` target to sync route photos**

The existing `publish` target only copies `content.json`. Since `build_content()` (Task 4) already writes processed photos directly into both `frontend/assets/route/` and `docs/static/assets/route/` during `make build`, no extra copy step is needed for the photos themselves — but new photo files won't be tracked by git automatically. Update the `publish` target in `Makefile` to also stage the route asset directories:

```makefile
publish: build
	cp app/static/content.json docs/static/content.json
	git add app/static/content.json docs/static/content.json
	git add frontend/assets/route docs/static/assets/route
	git commit -m "Update content" || echo "Nothing to commit"
	git push origin main
	@echo "Pushed. Render redeploys automatically; GitHub Pages rebuilds in a couple of minutes."
```

- [ ] **Step 2: Verify `.gitignore` doesn't exclude the new asset dirs**

Run: `git check-ignore -v frontend/assets/route docs/static/assets/route 2>&1 || echo "not ignored — good"`
Expected: "not ignored — good" (per the conversation history, `frontend/assets/` was already un-ignored for the Pages static export; confirm it still holds for the new `route/` subfolder). If it IS ignored, add a `!frontend/assets/route/` negation line to `.gitignore` right after the existing `frontend/assets/` rule.

- [ ] **Step 3: Commit**

```bash
git add Makefile
git commit -m "chore: sync route plan photos in publish target"
```

---

## Self-Review Notes

- **Spec coverage:** markdown format (Task 2), photo resolution (Task 3), pipeline/compression (Task 3+4), data model (Task 2), rendering (Task 5), error handling (Tasks 3/4 skip-and-log), testing (unit tests in Tasks 2/3/4, manual in Task 5) — all covered. Publish/sync (not explicitly in spec but required for the dual-hosting architecture already established in this project) added as Task 6.
- **Type consistency checked:** `process_route_photos` return type (`dict[str, str]`) matches its use in `_resolve_route_photos`; `block["photos"]` list-of-strings shape is consistent from parser (Task 2) through builder mutation (Task 4) to renderer (Task 5).
- **No placeholders:** every step has literal code, not descriptions.
