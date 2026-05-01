from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from app.db.session import get_session
from app.modules.media.api.interfaces import IMediaService, get_media_service

router = APIRouter()

UPLOAD_DIR = Path("data/uploads")


@router.get("/images/{photo_id}")
async def get_image(
    photo_id: int,
    mode: str = "modern",
    session: Session = Depends(get_session),
    media_service: IMediaService = Depends(get_media_service),
):
    """
    Serves the image file.
    If mode='legacy', resizes it on the fly.
    """

    try:
        photo_data = await media_service.get_photo_for_download(session, photo_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Photo not found") from None

    photo = photo_data["photo"]
    preset_name = photo_data["preset_name"]
    file_path = UPLOAD_DIR / preset_name / photo.filename
    # Security: Prevent path traversal by ensuring resolved path is within UPLOAD_DIR
    if not file_path.resolve().is_relative_to(UPLOAD_DIR.resolve()):
        raise HTTPException(status_code=403, detail="Forbidden")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    optimized_bytes = media_service.optimize_path(file_path)
    if mode == "legacy":
        return StreamingResponse(BytesIO(optimized_bytes), media_type="image/jpeg")

    return Response(content=optimized_bytes, media_type="image/jpeg")
