from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID


@dataclass(frozen=True, slots=True, kw_only=True)
class Pet:
    id: UUID
    name: str
    temper: str
    balance: Decimal


@dataclass(frozen=True, slots=True, kw_only=True)
class CreatePetParams:
    id: UUID
    name: str
    temper: str
