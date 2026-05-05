"""Atomic JSON routes for media operations."""

from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.modules.media.api.interfaces import IMediaService, get_media_service

router = APIRouter(prefix="/api/v1", tags=["api-media"])


class CreatePresetRequest(BaseModel):
    """Request payload for creating a media preset."""

    name: str = Field(min_length=1)


@router.post("/presets")
async def create_preset(
    payload: CreatePresetRequest,
    media_service: IMediaService = Depends(get_media_service),
) -> JSONResponse:
    """Create a preset and return the created resource as JSON."""
    preset = await media_service.create_preset(payload.name)
    return JSONResponse(status_code=status.HTTP_201_CREATED, content=jsonable_encoder(preset))


@router.get("/presets")
async def list_presets(
    media_service: IMediaService = Depends(get_media_service),
) -> JSONResponse:
    """List all presets."""
    presets = await media_service.list_presets()
    return JSONResponse(content=jsonable_encoder(presets))


@router.get("/presets/{preset_id}/images")
async def list_images_for_preset(
    preset_id: int,
    page: int = 1,
    size: int = 50,
    media_service: IMediaService = Depends(get_media_service),
) -> JSONResponse:
    """List images for a given preset (paged)."""
    photos, total = await media_service.list_photos_for_preset(preset_id, page=page, size=size)
    return JSONResponse(
        content=jsonable_encoder({"items": photos, "page": page, "size": size, "total": total})
    )


@router.post("/presets/{preset_id}/images")
async def add_images(
    preset_id: int,
    files: list[UploadFile] = File(...),
    media_service: IMediaService = Depends(get_media_service),
) -> JSONResponse:
    """Upload one or more images to a preset and return created photo metadata."""
    try:
        photos = await media_service.upload_photos(preset_id, files)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return JSONResponse(status_code=status.HTTP_201_CREATED, content=jsonable_encoder(photos))


@router.get("/images/{image_id}/metadata")
async def get_image_metadata(
    image_id: int,
    media_service: IMediaService = Depends(get_media_service),
) -> JSONResponse:
    """Return JSON metadata for a single image."""
    photo = await media_service.get_photo_by_id(image_id)
    if photo is None:
        raise HTTPException(status_code=404, detail="Photo not found")
    return JSONResponse(content=jsonable_encoder(photo))


@router.delete("/images/{image_id}")
async def delete_image(
    image_id: int,
    media_service: IMediaService = Depends(get_media_service),
) -> Response:
    """Delete a single image resource."""
    deleted = await media_service.delete_photo_from_db(image_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Photo not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/presets/{preset_id}")
async def delete_preset(
    preset_id: int,
    media_service: IMediaService = Depends(get_media_service),
) -> Response:
    """Delete a preset and its associated photos."""
    deleted = await media_service.delete_preset(preset_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Preset not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
