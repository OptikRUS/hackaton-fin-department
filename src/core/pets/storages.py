from abc import ABCMeta, abstractmethod

from src.core.pets.schemas import Pet


class PetStorage(metaclass=ABCMeta):
    @abstractmethod
    async def create_pet(self, *, pet: Pet) -> Pet:
        raise NotImplementedError
