from sqlmodel import select

from app.db.models import AppSettings, Preset


def test_dashboard_modern(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "info-box-container" in response.text


def test_dashboard_legacy_redirect(client):
    # iPad 2 iOS 9.3.5 User Agent
    ua = "Mozilla/5.0 (iPad; CPU OS 9_3_5 like Mac OS X) AppleWebKit/601.1.46 (KHTML, like Gecko) Version/9.0 Mobile/13G36 Safari/601.1"
    response = client.get("/", headers={"User-Agent": ua}, follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["location"] == "/legacy"


def test_dashboard_legacy(client):
    response = client.get("/legacy")
    assert response.status_code == 200
    assert "Legacy" in response.text
    assert "display: grid" not in response.text  # Ensure no grid CSS


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
