from datetime import UTC, datetime
from uuid import UUID

from dishka import Provider, Scope, provide


class MockGeneralProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def get_uuid(self) -> UUID:
        return UUID("12345678-1234-5678-1234-567812345678")

    @provide(scope=Scope.REQUEST)
    def get_current_datetime(self) -> datetime:
        return datetime(2026, 1, 1, tzinfo=UTC)
