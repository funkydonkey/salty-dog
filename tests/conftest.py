"""Shared pytest fixtures for Salty Dog tests."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def sample_markdown() -> str:
    """Sample markdown with frontmatter, headers, tables, checkboxes, wiki-links, emoji."""
    return """---
title: Sample Document
tags: [test, sample]
---

# Sample Header 🌊

This is a paragraph with a [[Wiki Link]] and [[Another Note|custom text]].

## Table Example

| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Value A  | Value B  | Value C  |
| Value D  | Value E  | Value F  |

## Checklist

- [x] Completed task
- [ ] Pending task

## Russian Text

Привет мир! Это тестовый текст на русском языке.

## Link to Section

Check out [[Sample Document#Table Example]] for details.
"""


@pytest.fixture
def sample_route_markdown() -> str:
    """Markdown with waypoints in `- **Name** | lat, lng | description` format."""
    return """---
title: Route Plan
---

# Daily Route

## Day 1 - Marina to Island

- **Marina Kastela** | 43.508, 16.440 | Starting point
- **Maslinica** | 43.286, 16.183 | Lunch stop with tavern
- **Vis Town** | 43.063, 16.183 | Overnight anchorage

## Day 2 - Island Hopping

- Hvar Harbor | 43.173, 16.441 | Popular destination
- **Palmižana** | 43.156, 16.397 | Beautiful bay with restaurant
"""


@pytest.fixture
def sample_route_frontmatter() -> str:
    """Markdown with waypoints in frontmatter."""
    return """---
title: Route with Frontmatter
waypoints:
  - name: "Start Point"
    lat: 43.5
    lng: 16.4
    description: "Starting location"
  - name: "Destination"
    lat: 43.2
    lng: 16.1
    description: "Final destination"
---

# Route Overview

This route has waypoints in frontmatter.
"""


@pytest.fixture
def vault_dir(tmp_path: Path) -> Path:
    """Create a minimal vault with _app.yaml and sample markdown files."""
    vault = tmp_path / "test_vault"
    vault.mkdir()

    # Create _app.yaml config
    app_config = """trip:
  name: "Test Charter"
  boat: "Beneteau Oceanis 46.1"
  dates: "July 1-8, 2026"

sections:
  - id: "prep"
    title: "Preparation"
    icon: "📋"
    tab: "prep"
    files:
      - "safety"
      - "checklist"

  - id: "route"
    title: "Route"
    icon: "🗺️"
    tab: "route"
    files:
      - "daily_plan"

  - id: "missing_section"
    title: "Missing Files"
    icon: "❓"
    tab: "test"
    files:
      - "nonexistent_file"
"""
    (vault / "_app.yaml").write_text(app_config, encoding="utf-8")

    # Create sample markdown files
    safety_md = """---
title: Safety Briefing
---

# Safety Briefing 🛟

## Emergency Contacts

- Coast Guard: 155
- Marina: +385 21 123 456

## Safety Equipment

| Item | Location | Quantity |
|------|----------|----------|
| Life jackets | Cockpit locker | 8 |
| Fire extinguisher | Galley | 2 |

See also [[Checklist]] for pre-departure checks.
"""
    (vault / "safety.md").write_text(safety_md, encoding="utf-8")

    checklist_md = """# Pre-Departure Checklist

- [x] Check weather forecast
- [x] File float plan
- [ ] Check engine oil
- [ ] Test VHF radio

Refer to [[Safety Briefing]] for emergency procedures.
"""
    (vault / "checklist.md").write_text(checklist_md, encoding="utf-8")

    daily_plan_md = """---
title: Daily Route Plan
---

# Daily Itinerary

## Day 1

- **Trogir Marina** | 43.508, 16.440 | Departure point with fuel dock
- **Maslinica Bay** | 43.286, 16.183 | Lunch anchorage

## Day 2

- **Vis Town** | 43.063, 16.183 | Historic port town
"""
    (vault / "daily_plan.md").write_text(daily_plan_md, encoding="utf-8")

    return vault


@pytest.fixture
def app_client():
    """FastAPI TestClient for API endpoint testing."""
    from app.main import app

    return TestClient(app)
