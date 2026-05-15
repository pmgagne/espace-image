from sqlmodel import select

from app.db.models import AppSettings, CalendarSource, Preset


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
    response = client.post("/api/v1/presets", json={"name": "New Preset"})
    assert response.status_code == 201
    assert response.headers["content-type"].startswith("application/json")
    assert response.json()["name"] == "New Preset"

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


def test_admin_gallery_partial_uses_api_write_controls(client):
    response = client.get("/admin/partials/gallery")
    assert response.status_code == 200
    assert 'id="admin-preset-create-form"' in response.text
    assert 'id="admin-upload-form"' not in response.text
    assert 'hx-post="/admin/presets"' not in response.text
    assert 'hx-post="/admin/upload"' not in response.text


def test_admin_settings_partial_uses_api_write_form(client):
    response = client.get("/admin/partials/settings")
    assert response.status_code == 200
    assert 'id="admin-settings-form"' in response.text
    assert 'hx-post="/admin/settings"' not in response.text


def test_admin_calendars_partial_uses_api_write_controls(client, session):
    source = CalendarSource(label="Home", url="https://example.com/home.ics", color="#123456")
    session.add(source)
    session.commit()

    response = client.get("/admin/partials/calendars")
    assert response.status_code == 200
    assert 'id="admin-calendar-create-form"' in response.text
    assert 'id="btn-sync-calendars"' in response.text
    assert "data-api-calendar-default-source-id" not in response.text
    assert "data-api-delete-calendar-source-id" in response.text
    assert 'hx-post="/admin/calendars"' not in response.text
    assert 'hx-post="/admin/calendars/' not in response.text
    assert 'hx-delete="/admin/calendars/' not in response.text


def test_admin_calendar_mutation_route_is_deprecated(client):
    response = client.post("/admin/calendars")
    assert response.status_code == 410


def test_admin_debug_partial_uses_api_write_form(client):
    response = client.get("/admin/partials/debug")
    assert response.status_code == 200
    assert 'id="admin-simulate-alarm-form"' in response.text
    assert 'hx-post="/admin/debug/simulate-alarm"' not in response.text


def test_admin_debug_simulate_route_is_deprecated(client):
    response = client.post("/admin/debug/simulate-alarm", data={"delay_seconds": 1})
    assert response.status_code == 410


def test_dashboard_legacy_alarm_mutation_route_is_deprecated(client):
    response = client.post("/api/alarms/00000000-0000-0000-0000-000000000000/dismiss")
    assert response.status_code == 410
