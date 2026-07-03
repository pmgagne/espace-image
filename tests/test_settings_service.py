"""Tests for SettingsModuleService / SettingsRepository preset photo counts."""

from app.db.models import Photo, Preset
from app.modules.settings.internal.application.service import create_settings_service
from app.modules.settings.internal.infrastructure.repository import SettingsRepository


def test_list_presets_returns_correct_photo_count(session, session_factory):
    """Each preset's DTO should reflect the actual number of photos it has."""
    preset_with_photos = Preset(name="With Photos")
    preset_without_photos = Preset(name="Empty")
    session.add(preset_with_photos)
    session.add(preset_without_photos)
    session.commit()
    session.refresh(preset_with_photos)
    session.refresh(preset_without_photos)

    session.add_all(
        [
            Photo(filename="a.jpg", preset_id=preset_with_photos.id),
            Photo(filename="b.jpg", preset_id=preset_with_photos.id),
        ]
    )
    session.commit()

    service = create_settings_service(session_factory, SettingsRepository())
    presets = {p.id: p for p in service.list_presets(session=session)}

    assert presets[preset_with_photos.id].photo_count == 2
    assert presets[preset_without_photos.id].photo_count == 0


def test_get_preset_returns_correct_photo_count(session, session_factory):
    """A single preset lookup should also carry its photo count."""
    preset = Preset(name="Solo")
    session.add(preset)
    session.commit()
    session.refresh(preset)

    session.add(Photo(filename="only.jpg", preset_id=preset.id))
    session.commit()

    service = create_settings_service(session_factory, SettingsRepository())
    dto = service.get_preset(preset.id, session=session)

    assert dto is not None
    assert dto.photo_count == 1
