from datetime import UTC, datetime
from uuid import UUID, uuid4

from dishka import Provider, Scope, provide


class GeneralProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def get_uuid(self) -> UUID:
        return uuid4()

    @provide(scope=Scope.REQUEST)
    def get_current_datetime(self) -> datetime:
        return datetime.now(tz=UTC)
