from dataclasses import dataclass
from typing import Never

from behave.runner import Context

from src.core.pets.schemas import Pet


@dataclass(frozen=True, slots=True, kw_only=True)
class BehaveAssertsHelper:
    context: Context

    @staticmethod
    def equals(*, actual: object, expected: object, msg: str = "") -> None:
        assert actual == expected, f"{msg}\n{actual=}\n{expected=}"

    @staticmethod
    def false(*, msg: str = "") -> Never:
        raise AssertionError(msg)

    @staticmethod
    def not_none[T](value: T | None) -> T:
        assert value is not None, "Expected a value, got None"
        return value

    def pet(self, *, actual: Pet, expected: Pet) -> None:
        self.equals(actual=actual, expected=expected)

    def pets(self, *, actual: list[Pet], expected: list[Pet]) -> None:
        self.equals(actual=actual, expected=expected)
