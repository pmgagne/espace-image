import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.db.engine import create_db_and_tables
from app.routers import admin, dashboard, media


@asynccontextmanager
async def lifespan(_app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(title="Espace-Image", lifespan=lifespan)

# Ensure static directory exists
os.makedirs("app/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

# Debug mode flag
DEBUG_MODE = os.getenv("WEBAPP_DEBUG", "").lower() in ("true", "1", "yes")
templates.env.globals["debug_mode"] = DEBUG_MODE

# Include Routers
app.include_router(dashboard.router)
app.include_router(media.router)
app.include_router(admin.router)


@app.get("/health")
async def health_check():
    return {"status": "ok"}
