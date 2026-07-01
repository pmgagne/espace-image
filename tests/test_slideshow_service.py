"""Tests for SlideshowModuleService.select_next_slide.

Uses the shared in-memory SQLite fixtures (session / session_factory) to seed
Preset / Photo / AppSettings rows and exercise all three selection branches.
Pattern follows test_alarm_purge_old.py.
"""

from app.db.models import AppSettings, Photo, Preset
from app.modules.slideshow.internal.application.service import (
    SlideshowModuleService,
    create_slideshow_service,
)
from app.modules.slideshow.internal.infrastructure.repository import SlideshowRepository


def _make_service(session_factory):
    """Build a SlideshowModuleService wired to the test session_factory."""
    return SlideshowModuleService(
        repository=SlideshowRepository(),
        session_factory=session_factory,
    )


# ---------------------------------------------------------------------------
# Branch 1 — no settings row at all
# ---------------------------------------------------------------------------


def test_select_next_slide_returns_error_when_no_settings(session, session_factory):
    # session is empty — no AppSettings row exists
    service = _make_service(session_factory)
    result = service.select_next_slide(session=session)

    assert result.img_url is None
    assert result.error_msg == "No Preset Active. Please configure in Admin."


# ---------------------------------------------------------------------------
# Branch 2 — settings present but active_preset_id is None
# ---------------------------------------------------------------------------


def test_select_next_slide_returns_error_when_no_active_preset(session, session_factory):
    settings = AppSettings(active_preset_id=None)
    session.add(settings)
    session.commit()

    service = _make_service(session_factory)
    result = service.select_next_slide(session=session)

    assert result.img_url is None
    assert result.error_msg == "No Preset Active. Please configure in Admin."


# ---------------------------------------------------------------------------
# Branch 3 — active preset exists but has no photos
# ---------------------------------------------------------------------------


def test_select_next_slide_returns_error_when_preset_has_no_photos(session, session_factory):
    preset = Preset(name="Empty Preset")
    session.add(preset)
    session.commit()
    session.refresh(preset)

    settings = AppSettings(active_preset_id=preset.id)
    session.add(settings)
    session.commit()

    service = _make_service(session_factory)
    result = service.select_next_slide(session=session)

    assert result.img_url is None
    assert result.error_msg == "No Photos found in the active preset."


# ---------------------------------------------------------------------------
# Branch 4 — happy path (single photo → deterministic URL)
# ---------------------------------------------------------------------------


def test_select_next_slide_returns_photo_url(session, session_factory):
    preset = Preset(name="My Preset")
    session.add(preset)
    session.commit()
    session.refresh(preset)

    photo = Photo(filename="cat.jpg", preset_id=preset.id)
    session.add(photo)
    session.commit()
    session.refresh(photo)

    settings = AppSettings(active_preset_id=preset.id)
    session.add(settings)
    session.commit()

    service = _make_service(session_factory)
    result = service.select_next_slide(mode="modern", session=session)

    assert result.error_msg is None
    assert result.img_url == f"/images/{photo.id}?mode=modern"


# ---------------------------------------------------------------------------
# Mode propagation
# ---------------------------------------------------------------------------


def test_select_next_slide_propagates_legacy_mode(session, session_factory):
    preset = Preset(name="Legacy Preset")
    session.add(preset)
    session.commit()
    session.refresh(preset)

    photo = Photo(filename="old.jpg", preset_id=preset.id)
    session.add(photo)
    session.commit()
    session.refresh(photo)

    settings = AppSettings(active_preset_id=preset.id)
    session.add(settings)
    session.commit()

    service = _make_service(session_factory)
    result = service.select_next_slide(mode="legacy", session=session)

    assert result.img_url == f"/images/{photo.id}?mode=legacy"


# ---------------------------------------------------------------------------
# _session_scope path — no session passed, service opens its own
# ---------------------------------------------------------------------------


def test_select_next_slide_opens_own_session_via_factory(session, session_factory):
    """Exercise the _session_scope branch where no session is passed in."""
    preset = Preset(name="Factory Preset")
    session.add(preset)
    session.commit()
    session.refresh(preset)

    photo = Photo(filename="sunset.jpg", preset_id=preset.id)
    session.add(photo)
    session.commit()
    session.refresh(photo)

    settings = AppSettings(active_preset_id=preset.id)
    session.add(settings)
    session.commit()

    # Use the factory function (mirrors conftest wiring) and pass NO session
    service = create_slideshow_service(session_factory, SlideshowRepository())
    result = service.select_next_slide(mode="modern")  # no session= kwarg

    assert result.error_msg is None
    assert result.img_url == f"/images/{photo.id}?mode=modern"


# ---------------------------------------------------------------------------
# Repository thin tests (mirrors test_alarm_purge_old.py pattern)
# ---------------------------------------------------------------------------


def test_repository_get_settings_returns_none_when_empty(session):
    result = SlideshowRepository().get_settings(session)
    assert result is None


def test_repository_get_settings_returns_row(session):
    preset = Preset(name="P")
    session.add(preset)
    session.commit()
    session.refresh(preset)

    settings = AppSettings(active_preset_id=preset.id)
    session.add(settings)
    session.commit()

    result = SlideshowRepository().get_settings(session)
    assert result is not None
    assert result.active_preset_id == preset.id


def test_repository_list_photos_for_preset_returns_only_matching_photos(session):
    preset_a = Preset(name="A")
    preset_b = Preset(name="B")
    session.add_all([preset_a, preset_b])
    session.commit()
    session.refresh(preset_a)
    session.refresh(preset_b)

    photo_a = Photo(filename="a.jpg", preset_id=preset_a.id)
    photo_b = Photo(filename="b.jpg", preset_id=preset_b.id)
    session.add_all([photo_a, photo_b])
    session.commit()
    session.refresh(photo_a)

    photos = SlideshowRepository().list_photos_for_preset(session, preset_a.id)
    assert len(photos) == 1
    assert photos[0].filename == "a.jpg"
