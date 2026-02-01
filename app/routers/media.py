from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlmodel import Session

from app.db.models import Photo
from app.db.session import get_session
from app.services.image_service import ImageOptimizer

router = APIRouter()

UPLOAD_DIR = Path("data/uploads")


@router.get("/images/{photo_id}")
async def get_image(photo_id: int, mode: str = "modern", session: Session = Depends(get_session)):
    """
    Serves the image file.
    If mode='legacy', resizes it on the fly.
    """
    photo = session.get(Photo, photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    # We need to know the path.
    # The Photo model stores 'filename' and 'preset_id'.
    # We need to look up the preset to get the folder name.

    # Eager load preset or fetch it
    if not photo.preset:
        # Should be eager loaded or we fetch
        pass

    # Construct path: data/uploads/{preset_name}/{filename}
    # For now assuming "Default" or looking up preset name
    preset_name = photo.preset.name if photo.preset else "Default"
    file_path = UPLOAD_DIR / preset_name / photo.filename

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    optimized_bytes = ImageOptimizer.optimize_path(file_path)
    if mode == "legacy":
        return StreamingResponse(BytesIO(optimized_bytes), media_type="image/jpeg")

    return Response(content=optimized_bytes, media_type="image/jpeg")
