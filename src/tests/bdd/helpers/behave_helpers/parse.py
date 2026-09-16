from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from uuid import UUID

from behave.runner import Context

from src.core.pets.schemas import CreatePetParams, Pet
from src.tests.helpers.factory import FactoryHelper


@dataclass(frozen=True, slots=True, kw_only=True)
class BehaveParseHelper:
    context: Context
    factory: FactoryHelper

    def create_pet_params(self) -> CreatePetParams:
        values = self._table_values()
        self._require_exact_fields(values=values, expected_fields={"id", "name", "temper"})
        return self.factory.pets.create_pet_params(
            pet_id=self.uuid(value=values["id"]),
            name=values["name"],
            temper=values["temper"],
        )

    def pet(self) -> Pet:
        return self._pet(values=self._table_values())

    def pets(self) -> list[Pet]:
        return [
            self._pet(values=values)
            for values in self._collection_values(
                expected_fields={"id", "name", "temper", "balance"},
            )
        ]

    def uuid(self, *, value: str) -> UUID:
        try:
            return UUID(value)
        except ValueError as error:
            msg = f"Expected UUID BDD value, got {value!r}"
            raise ValueError(msg) from error

    def decimal(self, *, value: str) -> Decimal:
        try:
            return Decimal(value)
        except InvalidOperation as error:
            msg = f"Expected decimal BDD value, got {value!r}"
            raise ValueError(msg) from error

    def _pet(self, *, values: dict[str, str]) -> Pet:
        self._require_exact_fields(
            values=values,
            expected_fields={"id", "name", "temper", "balance"},
        )
        return self.factory.pets.create_pet(
            pet_id=self.uuid(value=values["id"]),
            name=values["name"],
            temper=values["temper"],
            balance=self.decimal(value=values["balance"]),
        )

    def _table_values(self) -> dict[str, str]:
        if self.context.table is None:
            msg = "BDD step requires a data table"
            raise ValueError(msg)
        return dict(self.context.table)

    def _collection_values(self, *, expected_fields: set[str]) -> list[dict[str, str]]:
        if self.context.table is None:
            return []
        self._require_exact_fields(
            values=dict.fromkeys(self.context.table.headings, ""),
            expected_fields=expected_fields,
        )
        return [dict(row.items()) for row in self.context.table.rows]

    @staticmethod
    def _require_exact_fields(
        *,
        values: dict[str, str],
        expected_fields: set[str],
    ) -> None:
        actual_fields = set(values)
        if actual_fields != expected_fields:
            msg = f"Expected BDD fields {expected_fields}, got {actual_fields}"
            raise ValueError(msg)
