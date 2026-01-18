from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlmodel import Session, select
from app.db.session import get_session
from app.db.models import Preset, Photo, AppSettings
from app.services.image_service import GalleryManager
from typing import List

router = APIRouter(prefix="/admin", tags=["admin"])
templates = Jinja2Templates(directory="app/templates")
gallery_manager = GalleryManager()

@router.get("/")
async def admin_dashboard(request: Request, session: Session = Depends(get_session)):
    """Admin Dashboard View"""
    presets = session.exec(select(Preset)).all()
    settings = session.exec(select(AppSettings)).first()
    
    return templates.TemplateResponse(request, "admin.html", {
        "presets": presets,
        "settings": settings
    })

@router.post("/presets")
async def create_preset(name: str = Form(...), session: Session = Depends(get_session)):
    """Create a new preset."""
    preset = Preset(name=name)
    session.add(preset)
    session.commit()
    return RedirectResponse(url="/admin", status_code=303)

@router.post("/upload")
async def upload_photo(
    preset_id: int = Form(...), 
    files: List[UploadFile] = File(...), 
    session: Session = Depends(get_session)
):
    """Upload photos to a preset."""
    preset = session.get(Preset, preset_id)
    if not preset:
        raise HTTPException(status_code=404, detail="Preset not found")
        
    for file in files:
        if not file.filename:
            continue
            
        content = await file.read()
        # Save to disk
        gallery_manager.save_upload(content, file.filename, preset.name)
        
        # Save to DB
        photo = Photo(filename=file.filename, preset_id=preset.id)
        session.add(photo)
        
    session.commit()
    return RedirectResponse(url="/admin", status_code=303)

@router.post("/settings/active-preset")
async def set_active_preset(preset_id: int = Form(...), session: Session = Depends(get_session)):
    """Set the active preset for the slideshow."""
    settings = session.exec(select(AppSettings)).first()
    if settings:
        settings.active_preset_id = preset_id
        session.add(settings)
        session.commit()
        
    return RedirectResponse(url="/admin", status_code=303)
