from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import selectinload
from sqlmodel import Session, select

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
    # Eager-load the preset relationship to avoid N+1 queries
    statement = select(Photo).where(Photo.id == photo_id).options(selectinload(Photo.preset))
    photo = session.exec(statement).first()
    if not photo:
        raise HTTPException(status_code=404, detail="Photo not found")

    # Construct path: data/uploads/{preset_name}/{filename}
    preset_name = photo.preset.name if photo.preset else "Default"
    file_path = UPLOAD_DIR / preset_name / photo.filename

    # Security: Prevent path traversal by ensuring resolved path is within UPLOAD_DIR
    if not file_path.resolve().is_relative_to(UPLOAD_DIR.resolve()):
        raise HTTPException(status_code=403, detail="Forbidden")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    optimized_bytes = ImageOptimizer.optimize_path(file_path)
    if mode == "legacy":
        return StreamingResponse(BytesIO(optimized_bytes), media_type="image/jpeg")

    return Response(content=optimized_bytes, media_type="image/jpeg")
