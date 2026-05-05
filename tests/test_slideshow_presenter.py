from app.modules.slideshow.internal.infrastructure.presenter import render_slide_fragment


def test_render_slide_fragment_with_error():
    html = render_slide_fragment(img_url=None, error_msg="No slide available")
    assert "No slide available" in html


def test_render_slide_fragment_with_image():
    url = "https://example.com/slide.jpg"
    html = render_slide_fragment(img_url=url, error_msg=None)
    assert "<img" in html
    assert url in html
