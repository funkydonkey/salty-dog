# Route Plan: per-day blocks + photos

## Purpose

Route plan page currently is an empty placeholder. Captain wants to author it day-by-day in Obsidian, each day splittable into free-titled sub-blocks (e.g. "Переход до Фетхие", "После обеда — Канакой"), each block carrying prose + zero or more photos rendered as a swipe carousel on mobile.

## Markdown authoring format

`Route plan.md` in vault:

```markdown
## День 1 — Острова Терсане и Яшика
| Откуда | Куда | Мили | Стоянка |
|---|---|---|---|
| Göçek | Tersane Adası | 8 | бухта Yassıca |

Общий текст дня, опционально. До первого ### под-заголовка.

### Переход до Фетхие
Текст блока.
![[foto1.jpg]]
![[foto2.jpg]]

### После обеда — Канакой
На тачке едем в Канакёй.
![[foto3.jpg]]
```

Rules:
- Day heading level moves from `###` to `##` (was `### День N`) — frees up `###` for sub-blocks nested under a day.
- Day heading regex unchanged in spirit: `## День N — заголовок`.
- Vertical facts table right after the day heading is parsed as today (`Откуда/Куда/Дистанция/Стоянка/...` → `from/to/nm/anchorage/...`).
- Free text between the table and the first `###` = day's general text (new field `intro`).
- Each `###` under a day = one block: `{ title, text, photos: [...] }`. Title is free text, no fixed vocabulary (утро/день/вечер not enforced).
- Photos referenced with Obsidian embed syntax `![[filename.jpg]]`, any number per block including zero.
- Top-level bullets before the first `##` still parsed as `principles` (unchanged from current behavior).

## Photo resolution & pipeline

- `![[filename.jpg]]` resolved by searching the **entire vault recursively** for a file with that basename — mirrors how Obsidian itself resolves wikilink embeds (unique basename, folder-agnostic). No fixed attachment folder assumed.
- During `scripts/build_content.py`:
  1. Parser collects referenced filenames per block.
  2. For each unique image found in the vault, resize to max dimension 1600px and re-encode as JPEG quality 80 using Pillow.
  3. Write the processed file to `frontend/assets/route/<slug>.jpg` (for Render) — filename slugified from original name, collisions get a numeric suffix.
  4. Also copy the same processed file to `docs/static/assets/route/<slug>.jpg` (for GitHub Pages static mirror), keeping the two hosting targets in sync the same way `make publish` already syncs `content.json`.
  5. `content.json` block photo entries store the relative served path (`/assets/route/<slug>.jpg` for Render via existing `/assets` mount; `static/assets/route/<slug>.jpg` for the Pages doc tree — resolved the same way other asset paths already differ between the two builds).
- New dependency: `Pillow` — added to `pyproject.toml` main dependencies (used only by the build script, not at runtime by FastAPI).
- If Pillow or a referenced image is missing, log a warning and skip that photo (don't fail the whole build) — consistent with existing "file not found → skip, log" pattern in `builder.py`.

## Data model changes

`app/content/structured_parsers.py::parse_route_plan`:
- Split on `^## ` instead of `^### ` for days.
- Within each day's raw text, split on `^### ` for blocks.
- New `Day` shape:
  ```python
  {
    "day": int, "title": str,
    "from": str, "to": str, "nm": str, "course": str, "anchorage": str,
    "highlights": str, "kids": str, "note": str,
    "bullets": [...],          # unchanged, legacy support
    "intro": str,               # NEW — free text before first block
    "blocks": [                 # NEW
      {"title": str, "text": str, "photos": [str, ...]},
      ...
    ],
  }
  ```
- `days` list and `principles` list keep their current shape/position in the returned dict.

## Rendering

`frontend/js/templates.js::renderRoutePlan`:
- Day card layout unchanged at the top (facts + existing fields).
- Render `intro` text (through `escLink()` for markdown link/bold support) below facts, above blocks.
- For each block: sub-heading (block title) + text (`escLink()`) + photo carousel if `photos.length > 0`.
- Carousel markup: horizontally scrollable row (`overflow-x: auto; scroll-snap-type: x mandatory`), each photo `scroll-snap-align: start`, dot indicators below driven by CSS (`:target`-free, pure CSS using scroll position is unreliable — instead render static dot markers, no active-state tracking; simplest robust option, no JS scroll listener needed). No external carousel library.
- New CSS in `frontend/css/templates.css`: `.route-block`, `.route-block__carousel`, `.route-block__photo`, `.route-block__dots`.

## Error handling

- Day with no `###` blocks still renders fine (empty `blocks: []`, `intro` holds all the text) — backward compatible with a day that's just prose, no photos yet.
- Missing/unresolvable photo reference: build-time warning + omitted from the block's photo list (never breaks the page).

## Testing

- Unit test for `parse_route_plan` with a day containing 2 blocks, one with photos, one without, plus a day with no blocks at all (pure legacy shape).
- Unit test for the vault-wide image resolver: finds a file by basename regardless of subfolder depth; missing file returns `None` and logs, doesn't raise.
- Manual: run `make build`, open Route tab locally, verify carousel swipe on a narrow viewport (browser devtools mobile emulation).
