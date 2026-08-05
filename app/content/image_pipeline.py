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
    # Handle dotfiles and empty stems: if stem is empty or is just a dotfile
    # marker (like ".jpg" where the whole name is the "extension"), default to "photo"
    if not stem or stem.startswith("."):
        return "photo"
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
