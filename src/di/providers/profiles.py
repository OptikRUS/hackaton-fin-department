from dishka import Provider, Scope, provide

from src.core.profiles.storages import ProfileStorage
from src.core.profiles.use_cases import RegisterProfileUseCase
from src.infra.observability.business_metrics import BusinessMetrics


class ProfilesProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def get_register_profile_use_case(
        self,
        storage: ProfileStorage,
        metrics: BusinessMetrics,
    ) -> RegisterProfileUseCase:
        return RegisterProfileUseCase(storage=storage, metrics=metrics)
