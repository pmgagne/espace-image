from contextlib import asynccontextmanager
import os
from fastapi import FastAPI
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from app.db.engine import create_db_and_tables
from app.routers import dashboard, media, admin

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield

app = FastAPI(title="Gemini Dashboard", lifespan=lifespan)

# Ensure static directory exists
os.makedirs("app/static", exist_ok=True)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

templates = Jinja2Templates(directory="app/templates")

# Include Routers
app.include_router(dashboard.router)
app.include_router(media.router)
app.include_router(admin.router)

@app.get("/health")
async def health_check():
    return {"status": "ok"}