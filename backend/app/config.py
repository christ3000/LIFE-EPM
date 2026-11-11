from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Paramètres centralisés ; vider le cache dans les tests après modification des variables d'environnement.
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg://localhost:5432/life_epm"
    jwt_secret: str = Field(
        default="",
        validation_alias=AliasChoices("LIFE_EPM_JWT_SECRET", "JWT_SECRET"),
    )
    frontend_origin: str = Field(
        default="http://localhost:3000",
        validation_alias=AliasChoices("LIFE_EPM_FRONTEND_ORIGIN", "FRONTEND_ORIGIN"),
    )
    cookie_secure: bool = Field(
        default=False,
        validation_alias=AliasChoices("LIFE_EPM_COOKIE_SECURE", "COOKIE_SECURE"),
    )
    church_name: str = Field(
        default="Église Pentecôte Missionnaire",
        validation_alias=AliasChoices("LIFE_EPM_CHURCH_NAME", "CHURCH_NAME"),
    )
    church_initials: str = Field(
        default="EPM",
        validation_alias=AliasChoices("LIFE_EPM_CHURCH_INITIALS", "CHURCH_INITIALS"),
    )
    church_city: str = Field(
        default="Abidjan",
        validation_alias=AliasChoices("LIFE_EPM_CHURCH_CITY", "CHURCH_CITY"),
    )
    bootstrap_admin_username: str = Field(
        default="pasteur.bobou",
        validation_alias=AliasChoices("LIFE_EPM_ADMIN_USERNAME", "BOOTSTRAP_ADMIN_USERNAME"),
    )
    bootstrap_admin_password: str = Field(
        default="",
        validation_alias=AliasChoices("LIFE_EPM_ADMIN_PASSWORD", "BOOTSTRAP_ADMIN_PASSWORD"),
    )
    bootstrap_admin_full_name: str = Field(
        default="Pasteur BOBOU Josué E.",
        validation_alias=AliasChoices("LIFE_EPM_ADMIN_FULL_NAME", "BOOTSTRAP_ADMIN_FULL_NAME"),
    )
    demo_data_enabled: bool = Field(
        default=False,
        validation_alias=AliasChoices("LIFE_EPM_DEMO_DATA_ENABLED", "DEMO_DATA_ENABLED"),
    )
    sms_provider: str = Field(
        default="disabled",
        validation_alias=AliasChoices("LIFE_EPM_SMS_PROVIDER", "SMS_PROVIDER"),
    )
    sms_username: str = Field(
        default="",
        validation_alias=AliasChoices("LIFE_EPM_SMS_USERNAME", "SMS_USERNAME"),
    )
    sms_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("LIFE_EPM_SMS_API_KEY", "SMS_API_KEY"),
    )
    sms_sender: str | None = Field(
        default=None,
        validation_alias=AliasChoices("LIFE_EPM_SMS_SENDER", "SMS_SENDER"),
    )
    sms_sandbox: bool = Field(
        default=True,
        validation_alias=AliasChoices("LIFE_EPM_SMS_SANDBOX", "SMS_SANDBOX"),
    )
    celery_broker_url: str = Field(
        default="redis://localhost:6379/0",
        validation_alias=AliasChoices("LIFE_EPM_CELERY_BROKER_URL", "CELERY_BROKER_URL"),
    )
    celery_result_backend: str = Field(
        default="redis://localhost:6379/1",
        validation_alias=AliasChoices("LIFE_EPM_CELERY_RESULT_BACKEND", "CELERY_RESULT_BACKEND"),
    )
    access_token_minutes: int = Field(
        default=30,
        ge=5,
        le=1440,
        validation_alias=AliasChoices("LIFE_EPM_ACCESS_TOKEN_MINUTES", "ACCESS_TOKEN_MINUTES"),
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
