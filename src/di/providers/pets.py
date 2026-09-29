from dishka import Provider, Scope, provide

from src.core.pets.storages import PetStorage
from src.core.pets.use_cases import CreatePetUseCase
from src.infra.observability.business_metrics import BusinessMetrics


class PetsProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def get_create_pet_use_case(
        self,
        pet_storage: PetStorage,
        metrics: BusinessMetrics,
    ) -> CreatePetUseCase:
        return CreatePetUseCase(pet_storage=pet_storage, metrics=metrics)
