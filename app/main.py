"""Salty Dog — FastAPI-приложение для яхтенного чартера. Раздаёт контент и фронтенд."""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as api_router

logger = logging.getLogger(__name__)

# Корневые пути проекта
BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"
CONTENT_JSON = BASE_DIR / "app" / "static" / "content.json"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Проверяем наличие content.json при старте."""
    if not CONTENT_JSON.exists():
        logger.warning(
            "content.json не найден (%s). Запустите: make build", CONTENT_JSON
        )
    else:
        size_kb = CONTENT_JSON.stat().st_size / 1024
        logger.info("content.json загружен (%.1f KB)", size_kb)
    yield


app = FastAPI(
    title="Salty Dog",
    description="Sailing charter trip companion",
    lifespan=lifespan,
)

# CORS — экипаж заходит с любых устройств
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# API-роуты
app.include_router(api_router)

# Статика фронтенда: CSS, JS, иконки
app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="frontend_static")

# Ассеты из vault (изображения, вложения)
assets_dir = FRONTEND_DIR / "assets"
if assets_dir.exists():
    app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")


@app.get("/health")
async def health():
    """Эндпоинт для проверки здоровья (Render.com и др.)."""
    return {"status": "ok"}


@app.get("/sw.js")
async def service_worker():
    """Service worker must be served from root scope for full caching coverage."""
    sw_path = FRONTEND_DIR / "sw.js"
    if not sw_path.exists():
        return {"error": "Service worker not found"}
    return FileResponse(
        sw_path,
        media_type="application/javascript",
        headers={"Service-Worker-Allowed": "/"},
    )


@app.get("/manifest.json")
async def manifest():
    """PWA manifest served from root for proper installation prompt."""
    manifest_path = FRONTEND_DIR / "manifest.json"
    if not manifest_path.exists():
        return {"error": "Manifest not found"}
    return FileResponse(manifest_path, media_type="application/manifest+json")


@app.get("/")
async def index():
    """Отдаём главную страницу фронтенда."""
    index_path = FRONTEND_DIR / "index.html"
    if not index_path.exists():
        return {"error": "Frontend not built yet"}
    return FileResponse(index_path)


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
