import pytest
from app.db.models import Preset, AppSettings, Photo

def test_dashboard_modern(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "info-box-container" in response.text
    
def test_dashboard_legacy(client):
    response = client.get("/legacy")
    assert response.status_code == 200
    assert "Legacy" in response.text
    assert "display: grid" not in response.text # Ensure no grid CSS

def test_admin_page(client):
    response = client.get("/admin/")
    assert response.status_code == 200
    assert "Admin Panel" in response.text

def test_create_preset(client, session):
    response = client.post("/admin/presets", data={"name": "New Preset"})
    assert response.status_code == 200
    assert "New Preset" in response.text
    
    # Check DB
    presets = session.exec(select(Preset).where(Preset.name == "New Preset")).all()
    assert len(presets) == 1

def test_components_weather(client, session):
    # Seed settings with new coordinates
    settings = AppSettings(weather_latitude=45.5, weather_longitude=-73.5)
    session.add(settings)
    session.commit()
    
    response = client.get("/components/weather")
    assert response.status_code == 200
    assert "weather-info" in response.text

# We need to import select for the test function above
from sqlmodel import select
