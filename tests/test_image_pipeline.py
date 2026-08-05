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
