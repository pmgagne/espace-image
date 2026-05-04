from app.modules.weather.internal.infrastructure.presenter import render_weather_fragment


def test_render_weather_fragment_no_location():
    html = render_weather_fragment(has_location=False)
    assert "No location defined" in html


def test_render_weather_fragment_with_data():
    weather = {"temp": 12, "condition": "Sunny"}
    html = render_weather_fragment(has_location=True, weather=weather)
    assert "12°C" in html
    assert "Sunny" in html
