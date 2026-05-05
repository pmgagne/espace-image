from app.main import app
from app.modules.settings.api.interfaces import get_settings_service

print("override present?", get_settings_service in app.dependency_overrides)
print("overrides count:", len(app.dependency_overrides))
for k in list(app.dependency_overrides.keys()):
    print(k)
