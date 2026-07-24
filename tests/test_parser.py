"""Tests for markdown parser (app.content.parser)."""

from pathlib import Path

import pytest

from app.content.parser import (
    _extract_title,
    _resolve_wikilinks,
    _slugify,
    parse_markdown_file,
)


class TestSlugify:
    """Test URL slug generation from note names."""

    def test_simple_name(self):
        assert _slugify("Safety Briefing") == "safety-briefing"

    def test_with_emoji(self):
        assert _slugify("Route 🗺️") == "route-"

    def test_with_special_chars(self):
        assert _slugify("Day 1 - Marina") == "day-1---marina"

    def test_russian_text(self):
        # Cyrillic characters should be preserved
        result = _slugify("Привет Мир")
        assert "привет" in result
        assert "мир" in result

    def test_empty_string(self):
        assert _slugify("") == ""


class TestResolveWikilinks:
    """Test wiki-link resolution to HTML anchor tags."""

    def test_simple_wikilink(self):
        text = "See [[Safety Briefing]] for details."
        result = _resolve_wikilinks(text)
        assert '<a href="#page-safety-briefing" class="wikilink">Safety Briefing</a>' in result

    def test_wikilink_with_alias(self):
        text = "Check [[Safety Briefing|safety info]] first."
        result = _resolve_wikilinks(text)
        assert '<a href="#page-safety-briefing" class="wikilink">safety info</a>' in result

    def test_wikilink_with_section(self):
        text = "See [[Route#Day 1]] for waypoints."
        result = _resolve_wikilinks(text)
        # Should strip section anchor from URL but keep in display
        assert '<a href="#page-route" class="wikilink">Route#Day 1</a>' in result

    def test_wikilink_with_section_and_alias(self):
        text = "Check [[Route#Day 1|first day]] plan."
        result = _resolve_wikilinks(text)
        assert '<a href="#page-route" class="wikilink">first day</a>' in result

    def test_multiple_wikilinks(self):
        text = "Read [[Safety]] then [[Checklist]] before departure."
        result = _resolve_wikilinks(text)
        assert result.count('<a href="#page-') == 2
        assert "Safety</a>" in result
        assert "Checklist</a>" in result

    def test_no_wikilinks(self):
        text = "Plain text without links."
        result = _resolve_wikilinks(text)
        assert result == text

    def test_empty_string(self):
        assert _resolve_wikilinks("") == ""


class TestExtractTitle:
    """Test title extraction from markdown content."""

    def test_extract_from_h1(self):
        text = "# Main Title\n\nSome content here."
        assert _extract_title(text, "fallback") == "Main Title"

    def test_extract_with_emoji(self):
        text = "# Safety Briefing 🛟\n\n## Details"
        assert _extract_title(text, "fallback") == "Safety Briefing 🛟"

    def test_ignore_h2(self):
        text = "## Subtitle\n\nNo H1 here."
        assert _extract_title(text, "fallback") == "fallback"

    def test_fallback_to_filename(self):
        text = "No headers here, just plain text."
        assert _extract_title(text, "my_file") == "my_file"

    def test_empty_content(self):
        assert _extract_title("", "filename") == "filename"

    def test_h1_with_leading_whitespace(self):
        text = "   # Whitespace Title  \n\nContent"
        assert _extract_title(text, "fallback") == "Whitespace Title"

    def test_multiple_h1_takes_first(self):
        text = "# First Title\n\n# Second Title"
        assert _extract_title(text, "fallback") == "First Title"


class TestParseMarkdownFile:
    """Test complete markdown file parsing."""

    def test_parse_with_frontmatter(self, tmp_path: Path, sample_markdown: str):
        md_file = tmp_path / "test.md"
        md_file.write_text(sample_markdown, encoding="utf-8")

        page = parse_markdown_file(md_file)

        assert page.filename == "test"
        assert page.title == "Sample Document"  # From frontmatter
        assert page.raw_markdown != ""
        assert "<h1>Sample Header 🌊</h1>" in page.html_content

    def test_parse_without_frontmatter(self, tmp_path: Path):
        content = "# Title From H1\n\nParagraph text."
        md_file = tmp_path / "no_front.md"
        md_file.write_text(content, encoding="utf-8")

        page = parse_markdown_file(md_file)

        assert page.filename == "no_front"
        assert page.title == "Title From H1"

    def test_converts_tables_to_html(self, tmp_path: Path, sample_markdown: str):
        md_file = tmp_path / "tables.md"
        md_file.write_text(sample_markdown, encoding="utf-8")

        page = parse_markdown_file(md_file)

        assert "<table>" in page.html_content
        assert "<th>Column 1</th>" in page.html_content
        assert "<td>Value A</td>" in page.html_content

    def test_resolves_wikilinks(self, tmp_path: Path, sample_markdown: str):
        md_file = tmp_path / "links.md"
        md_file.write_text(sample_markdown, encoding="utf-8")

        page = parse_markdown_file(md_file)

        assert '<a href="#page-wiki-link" class="wikilink">Wiki Link</a>' in page.html_content
        assert '<a href="#page-another-note" class="wikilink">custom text</a>' in page.html_content

    def test_preserves_emoji_in_headers(self, tmp_path: Path):
        content = "# Header with 🌊 Emoji"
        md_file = tmp_path / "emoji.md"
        md_file.write_text(content, encoding="utf-8")

        page = parse_markdown_file(md_file)

        assert "🌊" in page.html_content
        assert page.title == "Header with 🌊 Emoji"

    def test_handles_russian_text(self, tmp_path: Path, sample_markdown: str):
        md_file = tmp_path / "russian.md"
        md_file.write_text(sample_markdown, encoding="utf-8")

        page = parse_markdown_file(md_file)

        assert "Привет мир!" in page.html_content
        assert "Это тестовый текст на русском языке" in page.html_content

    def test_empty_markdown_file(self, tmp_path: Path):
        md_file = tmp_path / "empty.md"
        md_file.write_text("", encoding="utf-8")

        page = parse_markdown_file(md_file)

        assert page.filename == "empty"
        assert page.title == "empty"  # Falls back to filename
        assert page.html_content == ""
        assert page.raw_markdown == ""

    def test_raw_markdown_preserved(self, tmp_path: Path):
        content = """---
title: Test
---

# Header

Paragraph with [[link]]."""
        md_file = tmp_path / "raw.md"
        md_file.write_text(content, encoding="utf-8")

        page = parse_markdown_file(md_file)

        # raw_markdown should NOT have frontmatter, but should keep wiki-links
        assert "---" not in page.raw_markdown
        assert "title: Test" not in page.raw_markdown
        assert "[[link]]" in page.raw_markdown

    def test_handles_checkboxes(self, tmp_path: Path, sample_markdown: str):
        md_file = tmp_path / "checkbox.md"
        md_file.write_text(sample_markdown, encoding="utf-8")

        page = parse_markdown_file(md_file)

        # Markdown library converts checkboxes to list items
        assert "Completed task" in page.html_content
        assert "Pending task" in page.html_content

    def test_title_fallback_order(self, tmp_path: Path):
        """Title priority: frontmatter > H1 > filename."""
        # Case 1: Frontmatter title exists
        content1 = """---
title: Frontmatter Title
---

# H1 Title

Content"""
        md_file1 = tmp_path / "priority1.md"
        md_file1.write_text(content1, encoding="utf-8")
        page1 = parse_markdown_file(md_file1)
        assert page1.title == "Frontmatter Title"

        # Case 2: No frontmatter, use H1
        content2 = "# H1 Title\n\nContent"
        md_file2 = tmp_path / "priority2.md"
        md_file2.write_text(content2, encoding="utf-8")
        page2 = parse_markdown_file(md_file2)
        assert page2.title == "H1 Title"

        # Case 3: No frontmatter or H1, use filename
        content3 = "Just plain content without headers."
        md_file3 = tmp_path / "priority3.md"
        md_file3.write_text(content3, encoding="utf-8")
        page3 = parse_markdown_file(md_file3)
        assert page3.title == "priority3"
