from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Paramètres centralisés ; vider le cache dans les tests après modification des variables d'environnement.
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg://localhost:5432/life_epm"
    jwt_secret: str = ""
    frontend_origin: str = "http://localhost:3000"
    cookie_secure: bool = False
    church_name: str = "Église Pentecôte Missionnaire"
    church_initials: str = "EPM"
    church_city: str = "Abidjan"
    bootstrap_admin_username: str = "pasteur.bobou"
    bootstrap_admin_password: str = ""
    bootstrap_admin_full_name: str = "Pasteur BOBOU Josué E."
    demo_data_enabled: bool = False
    sms_provider: str = "disabled"
    sms_username: str = ""
    sms_api_key: str = ""
    sms_sender: str | None = None
    sms_sandbox: bool = True
    celery_broker_url: str = "redis://localhost:6379/0"
    celery_result_backend: str = "redis://localhost:6379/1"
    access_token_minutes: int = Field(default=30, ge=5, le=1440)


@lru_cache
def get_settings() -> Settings:
    return Settings()
