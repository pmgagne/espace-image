from sqlmodel import Session, select
from app.db.engine import engine
from app.db.models import Preset, Photo, AppSettings
import os

def check_state():
    with Session(engine) as session:
        print("--- Presets ---")
        presets = session.exec(select(Preset)).all()
        for p in presets:
            print(f"ID: {p.id}, Name: {p.name}")
            
        print("\n--- Photos ---")
        photos = session.exec(select(Photo)).all()
        for p in photos:
            print(f"ID: {p.id}, Filename: {p.filename}, Preset ID: {p.preset_id}")
            
        print("\n--- Settings ---")
        settings = session.exec(select(AppSettings)).first()
        if settings:
            print(f"Active Preset ID: {settings.active_preset_id}")
        else:
            print("No Settings found!")

        print("\n--- File System Check ---")
        if photos:
            for p in photos:
                # Find preset name
                preset = session.get(Preset, p.preset_id)
                path = f"data/uploads/{preset.name}/{p.filename}"
                exists = os.path.exists(path)
                print(f"File {path}: {'EXISTS' if exists else 'MISSING'}")

if __name__ == "__main__":
    check_state()
