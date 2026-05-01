from io import BytesIO

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse

from app.modules.media.api.interfaces import IMediaService, get_media_service

router = APIRouter()


@router.get("/images/{photo_id}")
async def get_image(
    photo_id: int,
    mode: str = "modern",
    media_service: IMediaService = Depends(get_media_service),
):
    """
    Serves the image file.
    If `mode=='legacy'`, return a compatibility streaming response used by
    older clients (legacy mode) which expect an on-the-fly resized JPEG.
    """

    try:
        photo_data = await media_service.get_image_payload(photo_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Photo not found") from None
    except PermissionError:
        raise HTTPException(status_code=403, detail="Forbidden") from None
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found on disk") from None

    optimized_bytes = photo_data["bytes"]
    if mode == "legacy":
        return StreamingResponse(BytesIO(optimized_bytes), media_type="image/jpeg")

    return Response(content=optimized_bytes, media_type="image/jpeg")
