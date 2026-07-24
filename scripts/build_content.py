#!/usr/bin/env python3
"""CLI-скрипт сборки контента: читает Obsidian vault и генерирует content.json для фронтенда."""

import argparse
import sys
from pathlib import Path

# Добавляем корень проекта в PYTHONPATH для импортов app.*
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.content.builder import build_content, write_content_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Сборка контента из Obsidian vault")
    parser.add_argument(
        "--vault-path",
        type=str,
        default=None,
        help="Путь к Obsidian vault (по умолчанию из .env VAULT_PATH)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Директория для content.json (по умолчанию app/static/)",
    )
    args = parser.parse_args()

    # Vault path: аргумент CLI > переменная окружения
    vault_path = args.vault_path
    if not vault_path:
        from app.config import settings
        vault_path = settings.VAULT_PATH

    if not vault_path:
        print("Ошибка: не указан VAULT_PATH (через --vault-path или .env)")
        sys.exit(1)

    vault = Path(vault_path)
    if not vault.is_dir():
        print(f"Ошибка: директория vault не найдена: {vault}")
        sys.exit(1)

    if not (vault / "_app.yaml").exists():
        print(f"Ошибка: _app.yaml не найден в {vault}")
        sys.exit(1)

    output_dir = Path(args.output) if args.output else PROJECT_ROOT / "app" / "static"

    print(f"Vault: {vault}")
    print(f"Output: {output_dir}")
    print("---")

    bundle = build_content(vault)
    output_file = write_content_json(bundle, output_dir)

    # Итоги сборки
    total_pages = sum(len(s.pages) for s in bundle.sections)
    waypoint_count = len(bundle.route.waypoints)

    print(f"Секций: {len(bundle.sections)}")
    for section in bundle.sections:
        pages_list = ", ".join(p.filename for p in section.pages)
        print(f"  [{section.id}] {section.title} — {len(section.pages)} стр. ({pages_list})")
    print(f"Всего страниц: {total_pages}")
    print(f"Waypoints: {waypoint_count}")
    print(f"Хеш: {bundle.content_hash}")
    print(f"Записано: {output_file}")


if __name__ == "__main__":
    main()
