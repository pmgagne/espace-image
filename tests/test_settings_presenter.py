from app.modules.settings.internal.infrastructure.presenter import render_settings_fragment


def test_render_settings_no_location():
    settings = {
        "weather_latitude": None,
        "weather_longitude": None,
        "active_preset_id": None,
        "slideshow_duration": None,
    }
    presets = []
    html = render_settings_fragment(settings, presets, location_name=None)
    assert "General Settings" in html
    assert "Backend timezone" in html
    assert "Detected:" not in html


def test_render_settings_with_location_and_presets():
    settings = {
        "weather_latitude": 45.5,
        "weather_longitude": -73.5,
        "active_preset_id": None,
        "slideshow_duration": 20,
    }
    presets = [{"id": 1, "name": "MyPreset", "photos": []}]
    html = render_settings_fragment(settings, presets, location_name="Montreal, QC")
    assert "Detected:" in html
    assert "Montreal, QC" in html
    assert "MyPreset" in html
