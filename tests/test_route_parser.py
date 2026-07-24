"""Tests for route/waypoint parser (app.content.route_parser)."""

from pathlib import Path

import pytest

from app.content.route_parser import (
    _parse_frontmatter_waypoints,
    _parse_markdown_waypoints,
    extract_waypoints,
)


class TestParseFrontmatterWaypoints:
    """Test waypoint extraction from YAML frontmatter."""

    def test_valid_frontmatter_waypoints(self):
        data = {
            "waypoints": [
                {"name": "Start", "lat": 43.5, "lng": 16.4, "description": "Starting point"},
                {"name": "End", "lat": 43.2, "lng": 16.1, "description": "Finish"},
            ]
        }
        waypoints = _parse_frontmatter_waypoints(data)

        assert len(waypoints) == 2
        assert waypoints[0].name == "Start"
        assert waypoints[0].lat == 43.5
        assert waypoints[0].lng == 16.4
        assert waypoints[0].description == "Starting point"
        assert waypoints[1].name == "End"

    def test_waypoints_without_description(self):
        data = {
            "waypoints": [
                {"name": "Point A", "lat": 43.0, "lng": 16.0},
            ]
        }
        waypoints = _parse_frontmatter_waypoints(data)

        assert len(waypoints) == 1
        assert waypoints[0].description == ""

    def test_empty_waypoints_list(self):
        data = {"waypoints": []}
        waypoints = _parse_frontmatter_waypoints(data)
        assert waypoints == []

    def test_no_waypoints_key(self):
        data = {"title": "Route"}
        waypoints = _parse_frontmatter_waypoints(data)
        assert waypoints == []

    def test_waypoints_not_list(self):
        data = {"waypoints": "not a list"}
        waypoints = _parse_frontmatter_waypoints(data)
        assert waypoints == []

    def test_invalid_waypoint_missing_lat(self):
        data = {
            "waypoints": [
                {"name": "Valid", "lat": 43.0, "lng": 16.0},
                {"name": "Missing lat", "lng": 16.0},  # No lat
            ]
        }
        waypoints = _parse_frontmatter_waypoints(data)
        # Should skip invalid, keep valid
        assert len(waypoints) == 1
        assert waypoints[0].name == "Valid"

    def test_invalid_waypoint_missing_lng(self):
        data = {
            "waypoints": [
                {"name": "Missing lng", "lat": 43.0},  # No lng
            ]
        }
        waypoints = _parse_frontmatter_waypoints(data)
        assert waypoints == []

    def test_invalid_waypoint_wrong_type(self):
        data = {
            "waypoints": [
                {"name": "Bad coords", "lat": "not a number", "lng": 16.0},
            ]
        }
        waypoints = _parse_frontmatter_waypoints(data)
        assert waypoints == []

    def test_waypoint_as_dict_not_list_item(self):
        """Each waypoint should be a dict in a list."""
        data = {
            "waypoints": [
                "string instead of dict",
            ]
        }
        waypoints = _parse_frontmatter_waypoints(data)
        assert waypoints == []

    def test_negative_coordinates(self):
        """Support negative coordinates (western/southern hemisphere)."""
        data = {
            "waypoints": [
                {"name": "South West", "lat": -33.8, "lng": -70.6},
            ]
        }
        waypoints = _parse_frontmatter_waypoints(data)

        assert len(waypoints) == 1
        assert waypoints[0].lat == -33.8
        assert waypoints[0].lng == -70.6


class TestParseMarkdownWaypoints:
    """Test waypoint extraction from markdown list format."""

    def test_parse_bold_format(self):
        text = "- **Marina Kastela** | 43.508, 16.440 | Starting point"
        waypoints = _parse_markdown_waypoints(text)

        assert len(waypoints) == 1
        assert waypoints[0].name == "Marina Kastela"
        assert waypoints[0].lat == 43.508
        assert waypoints[0].lng == 16.440
        assert waypoints[0].description == "Starting point"

    def test_parse_without_bold(self):
        text = "- Marina Plain | 43.5, 16.4 | No bold formatting"
        waypoints = _parse_markdown_waypoints(text)

        assert len(waypoints) == 1
        assert waypoints[0].name == "Marina Plain"

    def test_parse_without_description(self):
        text = "- **Point A** | 43.1, 16.2"
        waypoints = _parse_markdown_waypoints(text)

        assert len(waypoints) == 1
        assert waypoints[0].name == "Point A"
        assert waypoints[0].description == ""

    def test_parse_multiple_waypoints(self, sample_route_markdown: str):
        waypoints = _parse_markdown_waypoints(sample_route_markdown)

        assert len(waypoints) == 5  # 3 bold + 1 plain + 1 bold
        names = [w.name for w in waypoints]
        assert "Marina Kastela" in names
        assert "Maslinica" in names
        assert "Vis Town" in names
        assert "Hvar Harbor" in names
        assert "Palmižana" in names

    def test_parse_negative_coordinates(self):
        text = "- **Southern Point** | -33.123, -70.456 | South America"
        waypoints = _parse_markdown_waypoints(text)

        assert len(waypoints) == 1
        assert waypoints[0].lat == -33.123
        assert waypoints[0].lng == -70.456

    def test_parse_integer_coordinates(self):
        text = "- **Rounded** | 43, 16 | Integer coords"
        waypoints = _parse_markdown_waypoints(text)

        assert len(waypoints) == 1
        assert waypoints[0].lat == 43.0
        assert waypoints[0].lng == 16.0

    def test_ignore_lines_without_coordinates(self):
        text = """- **Header** | No coords here
- Regular bullet point
- **Valid** | 43.5, 16.4 | Good
- Another line without pattern"""
        waypoints = _parse_markdown_waypoints(text)

        assert len(waypoints) == 1
        assert waypoints[0].name == "Valid"

    def test_empty_text(self):
        waypoints = _parse_markdown_waypoints("")
        assert waypoints == []

    def test_no_matching_lines(self):
        text = """# Header

Regular paragraph without waypoints.

- Bullet without coords
- Another plain bullet"""
        waypoints = _parse_markdown_waypoints(text)
        assert waypoints == []

    def test_malformed_coordinates(self):
        """Lines with invalid coordinate format should be skipped."""
        text = """- **Bad1** | abc, def | Invalid
- **Bad2** | 43.5 | Missing lng
- **Good** | 43.5, 16.4 | Valid"""
        waypoints = _parse_markdown_waypoints(text)

        # Should only get the valid one
        assert len(waypoints) == 1
        assert waypoints[0].name == "Good"

    def test_whitespace_tolerance(self):
        """Parser should handle extra whitespace."""
        text = "-   **Spaced**   |   43.5  ,  16.4   |   Description with spaces  "
        waypoints = _parse_markdown_waypoints(text)

        assert len(waypoints) == 1
        assert waypoints[0].name == "Spaced"
        assert waypoints[0].lat == 43.5
        assert waypoints[0].description == "Description with spaces"


class TestExtractWaypoints:
    """Test the main waypoint extraction function (tries frontmatter then markdown)."""

    def test_extract_from_frontmatter(self, tmp_path: Path, sample_route_frontmatter: str):
        md_file = tmp_path / "route_fm.md"
        md_file.write_text(sample_route_frontmatter, encoding="utf-8")

        waypoints = extract_waypoints(md_file)

        assert len(waypoints) == 2
        assert waypoints[0].name == "Start Point"
        assert waypoints[1].name == "Destination"

    def test_extract_from_markdown(self, tmp_path: Path, sample_route_markdown: str):
        md_file = tmp_path / "route_md.md"
        md_file.write_text(sample_route_markdown, encoding="utf-8")

        waypoints = extract_waypoints(md_file)

        assert len(waypoints) == 5
        names = [w.name for w in waypoints]
        assert "Marina Kastela" in names

    def test_frontmatter_takes_priority(self, tmp_path: Path):
        """If frontmatter has waypoints, markdown waypoints are ignored."""
        content = """---
waypoints:
  - name: "FM Point"
    lat: 43.0
    lng: 16.0
---

- **MD Point** | 44.0, 17.0 | Should be ignored"""
        md_file = tmp_path / "priority.md"
        md_file.write_text(content, encoding="utf-8")

        waypoints = extract_waypoints(md_file)

        assert len(waypoints) == 1
        assert waypoints[0].name == "FM Point"

    def test_returns_empty_when_no_coordinates(self, tmp_path: Path):
        content = """# Route Plan

No waypoints here, just text."""
        md_file = tmp_path / "no_coords.md"
        md_file.write_text(content, encoding="utf-8")

        waypoints = extract_waypoints(md_file)
        assert waypoints == []

    def test_empty_file(self, tmp_path: Path):
        md_file = tmp_path / "empty.md"
        md_file.write_text("", encoding="utf-8")

        waypoints = extract_waypoints(md_file)
        assert waypoints == []

    def test_handles_utf8_encoding(self, tmp_path: Path):
        """Ensure UTF-8 characters in waypoint names work."""
        content = """---
waypoints:
  - name: "Залив Šolta"
    lat: 43.4
    lng: 16.3
    description: "Русский и Croatian mix"
---
"""
        md_file = tmp_path / "utf8.md"
        md_file.write_text(content, encoding="utf-8")

        waypoints = extract_waypoints(md_file)

        assert len(waypoints) == 1
        assert "Залив" in waypoints[0].name
        assert "Šolta" in waypoints[0].name
        assert "Русский" in waypoints[0].description
