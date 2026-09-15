# Reference: PostgresSettings

## Статус в проекте

В [Settings](../../src/config/settings.py) только APP и CORS. `PostgresSettings`, `settings.POSTGRES` и database consumers отсутствуют.

Ниже приведён паттерн для будущего расширения, а не существующие классы, пути
или обязательство добавить подсистему. Imports могут
быть опущены; вспомогательные типы и методы нужно определить под выбранный контракт.
`Entity*` в разных документах показывает роли, а не единую готовую модель проекта.

## REUSABLE PATTERN: PostgreSQL settings

```python
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
```

При добавлении PostgreSQL эта группа включается в root Settings полем `POSTGRES` с префиксом
`POSTGRES_`. DSN раскрывается через `get_secret_value()` на infrastructure boundary. Значения
в примере предназначены для локальной разработки; имя БД согласуется с Compose и миграциями.
