from app.modules.media.internal.infrastructure.presenter import render_gallery_fragment


def test_render_gallery_no_presets():
    data = {"presets": [], "selected_preset": None}
    html = render_gallery_fragment(data)
    assert "No Presets Available" in html


def test_render_gallery_selected_no_photos():
    data = {
        "presets": [{"id": 1, "name": "Default"}],
        "selected_preset": {"id": 1, "name": "Default"},
        "photos": [],
    }
    html = render_gallery_fragment(data)
    assert "No photos in this preset yet." in html
    assert "Upload to:" in html
