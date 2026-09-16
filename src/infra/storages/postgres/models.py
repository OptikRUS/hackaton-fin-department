from decimal import Decimal
from typing import Self
from uuid import UUID

from sqlalchemy import MetaData, Numeric, String, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from src.core.pets.schemas import Pet


class Base(DeclarativeBase):
    metadata = MetaData(
        naming_convention={
            "ix": "ix_%(column_0_label)s",
            "uq": "uq_%(table_name)s_%(column_0_name)s",
            "ck": "ck_%(table_name)s_%(constraint_name)s",
            "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
            "pk": "pk_%(table_name)s",
        },
    )


class PetModel(Base):
    __tablename__ = "pets"

    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True)
    name: Mapped[str] = mapped_column(String(), nullable=False)
    temper: Mapped[str] = mapped_column(String(), nullable=False)
    balance: Mapped[Decimal] = mapped_column(Numeric, nullable=False)

    def to_domain(self) -> Pet:
        return Pet(
            id=self.id,
            name=self.name,
            temper=self.temper,
            balance=self.balance,
        )

    @classmethod
    def from_domain(cls, *, pet: Pet) -> Self:
        return cls(
            id=pet.id,
            name=pet.name,
            temper=pet.temper,
            balance=pet.balance,
        )
