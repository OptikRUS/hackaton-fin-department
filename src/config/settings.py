from typing import ClassVar

from pydantic import SecretStr
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


class PostgresSettings(BaseSettings):
    PROTOCOL: str = "postgresql+asyncpg"
    HOST: str = "localhost"
    PORT: int = 5432
    USER: str = "postgres"
    PASSWORD: SecretStr = SecretStr("postgres")
    NAME: str = "hackaton_fin_department"

    model_config = SettingsConfigDict(env_prefix="POSTGRES_")

    @property
    def DSN(self) -> SecretStr:  # noqa: N802
        return SecretStr(
            f"{self.PROTOCOL}://{self.USER}:{self.PASSWORD.get_secret_value()}"
            f"@{self.HOST}:{self.PORT}/{self.NAME}",
        )


class Settings(BaseSettings):
    APP: AppSettings = AppSettings()
    CORS: CORSSettings = CORSSettings()
    POSTGRES: PostgresSettings = PostgresSettings()


settings = Settings()
