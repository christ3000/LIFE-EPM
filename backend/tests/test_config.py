from app.config import Settings


def test_settings_load_life_epm_environment_variables(monkeypatch) -> None:
    monkeypatch.setenv("LIFE_EPM_JWT_SECRET", "test-jwt-secret")
    monkeypatch.setenv("LIFE_EPM_ADMIN_USERNAME", "test-admin")
    monkeypatch.setenv("LIFE_EPM_ADMIN_PASSWORD", "test-admin-password")
    monkeypatch.setenv("LIFE_EPM_COOKIE_SECURE", "true")
    monkeypatch.setenv("LIFE_EPM_FRONTEND_ORIGIN", "https://example.test")

    settings = Settings(_env_file=None)

    assert settings.jwt_secret == "test-jwt-secret"
    assert settings.bootstrap_admin_username == "test-admin"
    assert settings.bootstrap_admin_password == "test-admin-password"
    assert settings.cookie_secure is True
    assert settings.frontend_origin == "https://example.test"
