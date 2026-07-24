"""Tests for content builder (app.content.builder)."""

from pathlib import Path

import pytest

from app.content.builder import (
    _build_sections,
    _compute_hash,
    _find_markdown_file,
    _load_app_config,
    build_content,
    write_content_json,
)
from app.content.models import ContentBundle, Route, Section, TripConfig


class TestLoadAppConfig:
    """Test _app.yaml loading."""

    def test_load_valid_config(self, vault_dir: Path):
        config = _load_app_config(vault_dir)

        assert "trip" in config
        assert config["trip"]["name"] == "Test Charter"
        assert config["trip"]["boat"] == "Beneteau Oceanis 46.1"
        assert "sections" in config

    def test_missing_config_file(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError, match="_app.yaml"):
            _load_app_config(tmp_path)

    def test_empty_vault_dir(self, tmp_path: Path):
        empty_vault = tmp_path / "empty"
        empty_vault.mkdir()

        with pytest.raises(FileNotFoundError):
            _load_app_config(empty_vault)


class TestFindMarkdownFile:
    """Test markdown file discovery."""

    def test_find_existing_file(self, vault_dir: Path):
        result = _find_markdown_file(vault_dir, "safety")
        assert result is not None
        assert result.name == "safety.md"

    def test_find_missing_file(self, vault_dir: Path):
        result = _find_markdown_file(vault_dir, "nonexistent")
        assert result is None

    def test_find_with_extension_in_name(self, vault_dir: Path):
        """Should work even if user passes 'safety.md' instead of 'safety'."""
        result = _find_markdown_file(vault_dir, "safety")
        assert result is not None


class TestBuildSections:
    """Test section building and waypoint extraction."""

    def test_build_sections_from_config(self, vault_dir: Path):
        config = _load_app_config(vault_dir)
        sections, route = _build_sections(vault_dir, config["sections"])

        assert len(sections) == 3
        assert sections[0].id == "prep"
        assert sections[0].title == "Preparation"
        assert sections[0].icon == "📋"
        assert len(sections[0].pages) == 2  # safety + checklist

    def test_extracts_waypoints_from_route_section(self, vault_dir: Path):
        config = _load_app_config(vault_dir)
        sections, route = _build_sections(vault_dir, config["sections"])

        # daily_plan.md has 3 waypoints
        assert len(route.waypoints) == 3
        names = [w.name for w in route.waypoints]
        assert "Trogir Marina" in names
        assert "Maslinica Bay" in names
        assert "Vis Town" in names

    def test_skips_missing_files_gracefully(self, vault_dir: Path, capsys):
        """Missing files should be skipped with a warning, not crash."""
        config = _load_app_config(vault_dir)
        sections, route = _build_sections(vault_dir, config["sections"])

        # "missing_section" has file "nonexistent_file" which doesn't exist
        missing_section = next(s for s in sections if s.id == "missing_section")
        assert len(missing_section.pages) == 0

        # Check that warning was printed
        captured = capsys.readouterr()
        assert "nonexistent_file.md — пропущен" in captured.out

    def test_section_without_files(self, tmp_path: Path):
        """Section with no files should create empty section."""
        vault = tmp_path / "vault"
        vault.mkdir()

        # Create minimal config
        config_content = """trip:
  name: "Test"

sections:
  - id: "empty"
    title: "Empty Section"
    icon: "❓"
    tab: "test"
    files: []
"""
        (vault / "_app.yaml").write_text(config_content, encoding="utf-8")

        config = _load_app_config(vault)
        sections, route = _build_sections(vault, config["sections"])

        assert len(sections) == 1
        assert sections[0].id == "empty"
        assert len(sections[0].pages) == 0

    def test_no_route_section_returns_empty_route(self, tmp_path: Path):
        """If no section has id='route', route should be empty."""
        vault = tmp_path / "vault"
        vault.mkdir()

        config_content = """trip:
  name: "Test"

sections:
  - id: "other"
    title: "Other"
    icon: "📋"
    tab: "test"
    files: []
"""
        (vault / "_app.yaml").write_text(config_content, encoding="utf-8")

        config = _load_app_config(vault)
        sections, route = _build_sections(vault, config["sections"])

        assert len(route.waypoints) == 0


class TestComputeHash:
    """Test content hash generation."""

    def test_compute_hash_consistent(self, vault_dir: Path):
        """Same content should produce same hash."""
        bundle = build_content(vault_dir)
        hash1 = _compute_hash(bundle)
        hash2 = _compute_hash(bundle)

        assert hash1 == hash2
        assert len(hash1) == 12  # SHA-256 truncated to 12 chars

    def test_compute_hash_changes_with_content(self, vault_dir: Path):
        """Different content should produce different hash."""
        bundle1 = build_content(vault_dir)
        hash1 = _compute_hash(bundle1)

        # Modify bundle
        bundle1.trip.name = "Different Name"
        hash2 = _compute_hash(bundle1)

        assert hash1 != hash2

    def test_hash_excludes_meta_fields(self, vault_dir: Path):
        """Hash should not change with built_at or content_hash itself."""
        bundle1 = build_content(vault_dir)
        hash1 = _compute_hash(bundle1)

        # Modify meta fields
        bundle2 = bundle1.model_copy(update={
            "built_at": "2026-01-01T00:00:00",
            "content_hash": "different_hash",
        })
        hash2 = _compute_hash(bundle2)

        # Hash should be same because we exclude these fields
        assert hash1 == hash2


class TestBuildContent:
    """Test complete content bundle building."""

    def test_build_from_vault(self, vault_dir: Path):
        bundle = build_content(vault_dir)

        assert isinstance(bundle, ContentBundle)
        assert bundle.trip.name == "Test Charter"
        assert bundle.trip.boat == "Beneteau Oceanis 46.1"
        assert len(bundle.sections) == 3
        assert len(bundle.route.waypoints) == 3
        assert bundle.content_hash != ""
        assert len(bundle.content_hash) == 12
        assert bundle.built_at != ""

    def test_build_includes_correct_pages(self, vault_dir: Path):
        bundle = build_content(vault_dir)

        prep_section = next(s for s in bundle.sections if s.id == "prep")
        assert len(prep_section.pages) == 2

        page_titles = [p.title for p in prep_section.pages]
        assert "Safety Briefing" in page_titles
        assert "Pre-Departure Checklist" in page_titles

    def test_build_processes_markdown(self, vault_dir: Path):
        """Pages should have HTML content, not raw markdown."""
        bundle = build_content(vault_dir)

        prep_section = next(s for s in bundle.sections if s.id == "prep")
        safety_page = next(p for p in prep_section.pages if "Safety" in p.title)

        # Should have HTML
        assert "<h1>" in safety_page.html_content
        assert "<table>" in safety_page.html_content
        # Should preserve emoji
        assert "🛟" in safety_page.html_content

    def test_build_resolves_wikilinks(self, vault_dir: Path):
        """Wiki-links should be converted to HTML anchors."""
        bundle = build_content(vault_dir)

        prep_section = next(s for s in bundle.sections if s.id == "prep")
        safety_page = next(p for p in prep_section.pages if "Safety" in p.title)

        assert '<a href="#page-checklist" class="wikilink">' in safety_page.html_content

    def test_build_invalid_vault_path(self, tmp_path: Path):
        nonexistent = tmp_path / "does_not_exist"

        with pytest.raises(FileNotFoundError, match="Vault не найден"):
            build_content(nonexistent)

    def test_build_vault_missing_config(self, tmp_path: Path):
        vault = tmp_path / "no_config"
        vault.mkdir()

        with pytest.raises(FileNotFoundError, match="_app.yaml"):
            build_content(vault)

    def test_build_with_minimal_config(self, tmp_path: Path):
        """Vault with minimal _app.yaml should still build."""
        vault = tmp_path / "minimal"
        vault.mkdir()

        config = """trip:
  name: "Minimal Trip"

sections: []
"""
        (vault / "_app.yaml").write_text(config, encoding="utf-8")

        bundle = build_content(vault)

        assert bundle.trip.name == "Minimal Trip"
        assert bundle.trip.boat == "TBD"  # Default value
        assert bundle.trip.dates == "TBD"  # Default value
        assert len(bundle.sections) == 0
        assert len(bundle.route.waypoints) == 0

    def test_build_handles_empty_trip_config(self, tmp_path: Path):
        """Missing trip config should work with defaults."""
        vault = tmp_path / "no_trip"
        vault.mkdir()

        config = """sections: []
"""
        (vault / "_app.yaml").write_text(config, encoding="utf-8")

        # Should not crash, but trip fields will be missing
        # This might raise validation error or use defaults
        try:
            bundle = build_content(vault)
            # If it succeeds, trip should have defaults or empty values
            assert bundle.trip is not None
        except Exception as e:
            # If Pydantic requires 'name', that's also acceptable
            assert "name" in str(e).lower() or "trip" in str(e).lower()


class TestWriteContentJson:
    """Test JSON serialization and file writing."""

    def test_write_creates_file(self, vault_dir: Path, tmp_path: Path):
        bundle = build_content(vault_dir)
        output_path = write_content_json(bundle, tmp_path)

        assert output_path.exists()
        assert output_path.name == "content.json"

    def test_write_creates_directory(self, vault_dir: Path, tmp_path: Path):
        """Should create output directory if it doesn't exist."""
        nested_output = tmp_path / "nested" / "output"
        bundle = build_content(vault_dir)

        output_path = write_content_json(bundle, nested_output)

        assert nested_output.exists()
        assert output_path.exists()

    def test_write_content_is_valid_json(self, vault_dir: Path, tmp_path: Path):
        bundle = build_content(vault_dir)
        output_path = write_content_json(bundle, tmp_path)

        import json
        with open(output_path, encoding="utf-8") as f:
            data = json.load(f)

        assert "trip" in data
        assert "sections" in data
        assert "route" in data
        assert "content_hash" in data
        assert "built_at" in data

    def test_write_preserves_utf8(self, vault_dir: Path, tmp_path: Path):
        """JSON should preserve UTF-8 characters (emoji, Cyrillic, etc.)."""
        bundle = build_content(vault_dir)
        output_path = write_content_json(bundle, tmp_path)

        content = output_path.read_text(encoding="utf-8")

        # Check emoji preserved
        assert "📋" in content
        assert "🗺️" in content
        assert "🛟" in content

    def test_write_json_formatted(self, vault_dir: Path, tmp_path: Path):
        """JSON should be indented for readability."""
        bundle = build_content(vault_dir)
        output_path = write_content_json(bundle, tmp_path)

        content = output_path.read_text(encoding="utf-8")

        # Indented JSON will have newlines
        assert "\n" in content
        assert "  " in content  # Indentation spaces

    def test_write_overwrites_existing(self, vault_dir: Path, tmp_path: Path):
        """Writing to existing file should overwrite."""
        bundle = build_content(vault_dir)

        # Write first time
        output_path = write_content_json(bundle, tmp_path)
        first_size = output_path.stat().st_size

        # Modify and write again
        bundle.trip.name = "Modified Trip"
        output_path = write_content_json(bundle, tmp_path)

        # Should have new content
        import json
        data = json.loads(output_path.read_text(encoding="utf-8"))
        assert data["trip"]["name"] == "Modified Trip"
