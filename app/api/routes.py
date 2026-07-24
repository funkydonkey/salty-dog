"""API-роуты для раздачи контента. Контент — готовый JSON, собранный из Obsidian-заметок."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")

CONTENT_JSON = Path(__file__).resolve().parent.parent / "static" / "content.json"


@router.get("/content")
async def get_content():
    """Весь контент-бандл одним запросом. Фронтенд кеширует локально."""
    if not CONTENT_JSON.exists():
        return JSONResponse(
            status_code=404,
            content={"error": "Content not built yet. Run: make build"},
        )

    data = json.loads(CONTENT_JSON.read_text(encoding="utf-8"))
    return JSONResponse(
        content=data,
        headers={"Cache-Control": "no-cache"},
    )


@router.get("/content/version")
async def get_content_version():
    """Лёгкий эндпоинт для проверки версии контента (cache invalidation)."""
    if not CONTENT_JSON.exists():
        return JSONResponse(
            status_code=404,
            content={"error": "Content not built yet. Run: make build"},
        )

    data = json.loads(CONTENT_JSON.read_text(encoding="utf-8"))
    return JSONResponse(
        content={
            "content_hash": data.get("content_hash"),
            "built_at": data.get("built_at"),
        },
        headers={"Cache-Control": "no-cache"},
    )
