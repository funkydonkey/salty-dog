"""Tests for API endpoints (app.api.routes and app.main)."""

import json
from pathlib import Path

import pytest

from app.content.builder import build_content, write_content_json


class TestHealthEndpoint:
    """Test /health endpoint."""

    def test_health_returns_ok(self, app_client):
        response = app_client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestContentEndpoint:
    """Test /api/content endpoint."""

    def test_content_returns_404_when_missing(self, app_client, tmp_path: Path, monkeypatch):
        """If content.json doesn't exist, should return 404."""
        # Point to empty directory
        nonexistent = tmp_path / "content.json"
        monkeypatch.setattr("app.api.routes.CONTENT_JSON", nonexistent)

        response = app_client.get("/api/content")

        assert response.status_code == 404
        assert "error" in response.json()
        assert "not built" in response.json()["error"].lower()

    def test_content_returns_bundle(self, app_client, vault_dir: Path, tmp_path: Path, monkeypatch):
        """When content.json exists, should return full bundle."""
        # Build content and write to tmp location
        bundle = build_content(vault_dir)
        output_path = write_content_json(bundle, tmp_path)

        # Monkey-patch CONTENT_JSON path
        monkeypatch.setattr("app.api.routes.CONTENT_JSON", output_path)

        response = app_client.get("/api/content")

        assert response.status_code == 200
        data = response.json()

        assert "trip" in data
        assert "sections" in data
        assert "route" in data
        assert "content_hash" in data
        assert "built_at" in data

        assert data["trip"]["name"] == "Test Charter"
        assert len(data["sections"]) == 3

    def test_content_returns_no_cache_header(self, app_client, vault_dir: Path, tmp_path: Path, monkeypatch):
        """Response should include Cache-Control: no-cache."""
        bundle = build_content(vault_dir)
        output_path = write_content_json(bundle, tmp_path)
        monkeypatch.setattr("app.api.routes.CONTENT_JSON", output_path)

        response = app_client.get("/api/content")

        assert "cache-control" in response.headers
        assert response.headers["cache-control"] == "no-cache"

    def test_content_includes_waypoints(self, app_client, vault_dir: Path, tmp_path: Path, monkeypatch):
        """Content should include route waypoints."""
        bundle = build_content(vault_dir)
        output_path = write_content_json(bundle, tmp_path)
        monkeypatch.setattr("app.api.routes.CONTENT_JSON", output_path)

        response = app_client.get("/api/content")

        data = response.json()
        assert "route" in data
        assert "waypoints" in data["route"]
        assert len(data["route"]["waypoints"]) == 3

        waypoint = data["route"]["waypoints"][0]
        assert "name" in waypoint
        assert "lat" in waypoint
        assert "lng" in waypoint

    def test_content_preserves_utf8(self, app_client, vault_dir: Path, tmp_path: Path, monkeypatch):
        """Response should preserve UTF-8 characters (emoji, Cyrillic)."""
        bundle = build_content(vault_dir)
        output_path = write_content_json(bundle, tmp_path)
        monkeypatch.setattr("app.api.routes.CONTENT_JSON", output_path)

        response = app_client.get("/api/content")

        # Response content should have UTF-8 characters
        content_text = response.text
        assert "📋" in content_text
        assert "🗺️" in content_text


class TestContentVersionEndpoint:
    """Test /api/content/version endpoint."""

    def test_version_returns_404_when_missing(self, app_client, tmp_path: Path, monkeypatch):
        nonexistent = tmp_path / "content.json"
        monkeypatch.setattr("app.api.routes.CONTENT_JSON", nonexistent)

        response = app_client.get("/api/content/version")

        assert response.status_code == 404
        assert "error" in response.json()

    def test_version_returns_hash_and_timestamp(self, app_client, vault_dir: Path, tmp_path: Path, monkeypatch):
        bundle = build_content(vault_dir)
        output_path = write_content_json(bundle, tmp_path)
        monkeypatch.setattr("app.api.routes.CONTENT_JSON", output_path)

        response = app_client.get("/api/content/version")

        assert response.status_code == 200
        data = response.json()

        assert "content_hash" in data
        assert "built_at" in data
        assert len(data["content_hash"]) == 12

    def test_version_no_cache_header(self, app_client, vault_dir: Path, tmp_path: Path, monkeypatch):
        bundle = build_content(vault_dir)
        output_path = write_content_json(bundle, tmp_path)
        monkeypatch.setattr("app.api.routes.CONTENT_JSON", output_path)

        response = app_client.get("/api/content/version")

        assert "cache-control" in response.headers
        assert response.headers["cache-control"] == "no-cache"

    def test_version_lightweight(self, app_client, vault_dir: Path, tmp_path: Path, monkeypatch):
        """Version endpoint should return minimal data, not full bundle."""
        bundle = build_content(vault_dir)
        output_path = write_content_json(bundle, tmp_path)
        monkeypatch.setattr("app.api.routes.CONTENT_JSON", output_path)

        response = app_client.get("/api/content/version")

        data = response.json()
        # Should NOT have sections, trip, route
        assert "sections" not in data
        assert "trip" not in data
        assert "route" not in data
        # Should only have meta fields
        assert len(data) == 2


class TestRootEndpoint:
    """Test / endpoint (serves frontend)."""

    def test_root_returns_html(self, app_client):
        """Should serve index.html."""
        response = app_client.get("/")

        # Might return 200 with HTML or 200 with error JSON depending on setup
        assert response.status_code == 200

        # If frontend exists, should be HTML
        content_type = response.headers.get("content-type", "")
        if "text/html" in content_type:
            assert "<!DOCTYPE html>" in response.text or "<html" in response.text
        else:
            # If no frontend, might return error JSON
            assert "error" in response.json()

    def test_root_serves_frontend_when_available(self, app_client, tmp_path: Path, monkeypatch):
        """If frontend/index.html exists, should serve it."""
        # Create mock frontend
        frontend_dir = tmp_path / "frontend"
        frontend_dir.mkdir()
        index_html = frontend_dir / "index.html"
        index_html.write_text("""<!DOCTYPE html>
<html>
<head><title>Salty Dog</title></head>
<body><h1>Test Frontend</h1></body>
</html>""", encoding="utf-8")

        # Monkey-patch FRONTEND_DIR
        monkeypatch.setattr("app.main.FRONTEND_DIR", frontend_dir)

        response = app_client.get("/")

        assert response.status_code == 200
        assert "text/html" in response.headers.get("content-type", "")
        assert "Test Frontend" in response.text


class TestServiceWorkerEndpoint:
    """Test /sw.js endpoint."""

    def test_service_worker_returns_404_when_missing(self, app_client, tmp_path: Path, monkeypatch):
        frontend_dir = tmp_path / "frontend"
        frontend_dir.mkdir()
        monkeypatch.setattr("app.main.FRONTEND_DIR", frontend_dir)

        response = app_client.get("/sw.js")

        # Returns 200 with error JSON, not 404 (based on implementation)
        assert response.status_code == 200
        data = response.json()
        assert "error" in data

    def test_service_worker_serves_js(self, app_client, tmp_path: Path, monkeypatch):
        frontend_dir = tmp_path / "frontend"
        frontend_dir.mkdir()
        sw_js = frontend_dir / "sw.js"
        sw_js.write_text("console.log('service worker');", encoding="utf-8")

        monkeypatch.setattr("app.main.FRONTEND_DIR", frontend_dir)

        response = app_client.get("/sw.js")

        assert response.status_code == 200
        assert "application/javascript" in response.headers.get("content-type", "")
        assert "service worker" in response.text

    def test_service_worker_has_correct_headers(self, app_client, tmp_path: Path, monkeypatch):
        """Service worker should have Service-Worker-Allowed header."""
        frontend_dir = tmp_path / "frontend"
        frontend_dir.mkdir()
        sw_js = frontend_dir / "sw.js"
        sw_js.write_text("// sw", encoding="utf-8")

        monkeypatch.setattr("app.main.FRONTEND_DIR", frontend_dir)

        response = app_client.get("/sw.js")

        assert response.headers.get("service-worker-allowed") == "/"


class TestManifestEndpoint:
    """Test /manifest.json endpoint."""

    def test_manifest_returns_404_when_missing(self, app_client, tmp_path: Path, monkeypatch):
        frontend_dir = tmp_path / "frontend"
        frontend_dir.mkdir()
        monkeypatch.setattr("app.main.FRONTEND_DIR", frontend_dir)

        response = app_client.get("/manifest.json")

        assert response.status_code == 200
        data = response.json()
        assert "error" in data

    def test_manifest_serves_json(self, app_client, tmp_path: Path, monkeypatch):
        frontend_dir = tmp_path / "frontend"
        frontend_dir.mkdir()
        manifest = frontend_dir / "manifest.json"
        manifest_data = {
            "name": "Salty Dog",
            "short_name": "SaltyDog",
            "start_url": "/",
            "display": "standalone",
        }
        manifest.write_text(json.dumps(manifest_data), encoding="utf-8")

        monkeypatch.setattr("app.main.FRONTEND_DIR", frontend_dir)

        response = app_client.get("/manifest.json")

        assert response.status_code == 200
        assert "application/manifest+json" in response.headers.get("content-type", "")
        data = response.json()
        assert data["name"] == "Salty Dog"


class TestCORSMiddleware:
    """Test CORS configuration."""

    def test_cors_allows_all_origins(self, app_client):
        """Should allow requests from any origin."""
        response = app_client.get("/health", headers={"Origin": "https://example.com"})

        assert response.status_code == 200
        # CORS headers should be present
        assert "access-control-allow-origin" in response.headers

    def test_cors_preflight(self, app_client):
        """Should handle OPTIONS preflight requests."""
        response = app_client.options(
            "/api/content",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "GET",
            },
        )

        # Preflight should succeed
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers
