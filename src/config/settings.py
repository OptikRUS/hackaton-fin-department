from typing import ClassVar

from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    NAME: str = "hackaton-fin-department"
    ADDRESS: str = "127.0.0.1"
    PORT: int = 8080
    VERSION: ClassVar[str] = "0.1.0"

    model_config = SettingsConfigDict(env_prefix="APP_")


class CORSSettings(BaseSettings):
    ALLOW_ORIGINS: list[str] = ["*"]
    ALLOW_METHODS: list[str] = ["*"]
    ALLOW_HEADERS: list[str] = ["*"]

    model_config = SettingsConfigDict(env_prefix="CORS_")


class Settings(BaseSettings):
    APP: AppSettings = AppSettings()
    CORS: CORSSettings = CORSSettings()


settings = Settings()
