from app.modules.alarms.internal.infrastructure.presenter import render_debug_fragment


def test_render_debug_fragment_no_message():
    html = render_debug_fragment()
    assert "Debug Panel" in html


def test_render_debug_fragment_with_message():
    html = render_debug_fragment(success_message="Simulated alarms created")
    assert "Success" in html or "✓ Success" in html
    assert "Simulated alarms created" in html
