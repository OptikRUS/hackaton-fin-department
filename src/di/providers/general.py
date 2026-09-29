from datetime import UTC, datetime
from uuid import UUID, uuid4

from dishka import Provider, Scope, provide

from src.infra.observability.business_metrics import BusinessMetrics, get_business_metrics


class GeneralProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def get_uuid(self) -> UUID:
        return uuid4()

    @provide(scope=Scope.REQUEST)
    def get_current_datetime(self) -> datetime:
        return datetime.now(tz=UTC)

    @provide(scope=Scope.APP)
    def get_business_metrics(self) -> BusinessMetrics:
        return get_business_metrics()
