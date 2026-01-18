import pytest
from app.db.models import Preset, AppSettings, Photo

def test_dashboard_modern(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "dashboard-grid" in response.text
    
def test_dashboard_legacy(client):
    response = client.get("/legacy")
    assert response.status_code == 200
    assert "Legacy Mode" in response.text
    assert "grid" not in response.text # Ensure no grid CSS

def test_admin_page(client):
    response = client.get("/admin/")
    assert response.status_code == 200
    assert "Admin Panel" in response.text

def test_create_preset(client, session):
    response = client.post("/admin/presets", data={"name": "New Preset"})
    assert response.status_code == 200 # Redirects are followed by TestClient usually? No, TestClient follows redirects by default? 
    # Actually TestClient follows redirects by default if not specified otherwise, so we get the admin page back (200)
    
    # Check DB
    presets = session.exec(select(Preset).where(Preset.name == "New Preset")).all()
    assert len(presets) == 1

def test_components_weather(client, session):
    # Seed settings
    settings = AppSettings(weather_location="Paris", weather_api_key="mock")
    session.add(settings)
    session.commit()
    
    response = client.get("/components/weather")
    assert response.status_code == 200
    assert "weather-widget" in response.text

# We need to import select for the test function above
from sqlmodel import select
