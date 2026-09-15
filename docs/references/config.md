# Reference: Configuration

## Runtime settings

[settings.py](../../src/config/settings.py) содержит только APP и CORS:

```python
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
```

Группы читают process environment с префиксами `APP_` и `CORS_`.
`VERSION` — `ClassVar`, версия синхронизирована с `pyproject.toml`: `0.1.0`.
По умолчанию адрес — `127.0.0.1`, порт — `8080`, все три CORS-списка — `["*"]`.
Значения списков в environment передаются как JSON.

`env_file` в settings не задан. Для локального файла используется:

```bash
cp .env.example .env
uv run --env-file .env python -m src.main
```

[.env.example](../../.env.example) задаёт `APP_ADDRESS=0.0.0.0`, что отличается от default класса.
Compose передаёт environment из файла и принудительно задаёт адрес `0.0.0.0`, порт `8080` внутри
контейнера. Детали — [корневой README](../../README.md).

## Paths and constants

[constants.py](../../src/config/constants.py) хранит пути отдельно:

```python
import pathlib

from pydantic_settings import BaseSettings, SettingsConfigDict


class DirSettings(BaseSettings):
    ROOT: pathlib.Path = pathlib.Path(__file__).resolve().parent.parent.parent
    SRC: pathlib.Path = ROOT / "src"

    model_config = SettingsConfigDict(env_prefix="DIR_")


class Constants(BaseSettings):
    DIRS: DirSettings = DirSettings()


constants = Constants()
```

`constants.DIRS.ROOT` указывает на корень текущего проекта; `SRC` — на его каталог `src`.
Группы AUTH, POSTGRES, CLICKHOUSE, EMAIL, CPA_GATEWAY и KAFKA отсутствуют.
Будущий PostgreSQL-паттерн — [postgres_settings.md](postgres_settings.md).
