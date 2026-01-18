from sqlmodel import Session, select
from app.db.engine import create_db_and_tables, engine
from app.db.models import Preset, AppSettings

def init():
    print("Initializing database...")
    create_db_and_tables()
    
    with Session(engine) as session:
        # Check for existing default preset to avoid duplicates
        statement = select(Preset).where(Preset.name == "Default")
        results = session.exec(statement)
        preset = results.first()
        
        if not preset:
            print("Seeding default preset...")
            preset = Preset(name="Default")
            session.add(preset)
            session.commit()
            session.refresh(preset)
            print(f"Created Default Preset ID: {preset.id}")
            
        # Ensure AppSettings exists
        settings = session.exec(select(AppSettings)).first()
        if not settings:
            print("Seeding AppSettings...")
            settings = AppSettings(active_preset_id=preset.id)
            session.add(settings)
            session.commit()
            print("AppSettings created.")
        else:
            print("AppSettings already exist.")

if __name__ == "__main__":
    init()
