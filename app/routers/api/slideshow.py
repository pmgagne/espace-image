"""Read-only JSON routes for slideshow selection operations."""

from fastapi import APIRouter, Depends, Query
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from app.modules.slideshow.api.interfaces import ISlideshowService, get_slideshow_service

router = APIRouter(prefix="/api/v1/slideshow", tags=["api-slideshow"])


@router.get("/current")
async def get_current_slide(
    mode: str = Query("modern"),
    slideshow_service: ISlideshowService = Depends(get_slideshow_service),
) -> JSONResponse:
    """Return current slide selection payload for a rendering mode."""
    slide = slideshow_service.select_next_slide(mode=mode)
    return JSONResponse(content=jsonable_encoder(slide))


@router.get("/next")
async def get_next_slide(
    mode: str = Query("modern"),
    slideshow_service: ISlideshowService = Depends(get_slideshow_service),
) -> JSONResponse:
    """Return next slide selection payload for a rendering mode."""
    slide = slideshow_service.select_next_slide(mode=mode)
    return JSONResponse(content=jsonable_encoder(slide))
