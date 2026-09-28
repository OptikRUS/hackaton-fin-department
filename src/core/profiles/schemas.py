import json
from dataclasses import asdict, dataclass
from hashlib import sha256
from typing import Literal
from uuid import NAMESPACE_URL, UUID, uuid5

from src.core.profiles.exceptions import InvalidRegistrationError

type PetAge = Literal["CUB", "TEEN", "ADULT", "SENIOR"]
type PetColor = Literal["COPPER", "SAND", "DARK_RUSSET"]
type PetTemperament = Literal["Curious", "Confident", "Joyful"] | None


@dataclass(frozen=True, slots=True, kw_only=True)
class DeviceId:
    value: str

    def validate(self) -> None:
        if not self.value.strip() or "\x00" in self.value:
            raise InvalidRegistrationError
        try:
            self.value.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise InvalidRegistrationError from exc

    @property
    def profile_id(self) -> UUID:
        self.validate()
        try:
            legacy_profile_id = UUID(self.value)
        except ValueError:
            pass
        else:
            if str(legacy_profile_id) == self.value:
                return legacy_profile_id
        return uuid5(NAMESPACE_URL, f"lct-device:{self.value}")


@dataclass(frozen=True, slots=True, kw_only=True)
class RegisteredPet:
    name: str
    age: PetAge
    color: PetColor
    temperament: PetTemperament
    selected_look_id: str


@dataclass(frozen=True, slots=True, kw_only=True)
class RegisterProfileParams:
    device_id: str
    pet: RegisteredPet
    schema_version: int = 1

    @property
    def profile_id(self) -> UUID:
        return DeviceId(value=self.device_id).profile_id

    def validate(self, *, idempotency_key: str) -> None:
        DeviceId(value=self.device_id).validate()
        if not idempotency_key or self.schema_version != 1:
            raise InvalidRegistrationError
        if not self.pet.name.strip() or not self.pet.name.isprintable():
            raise InvalidRegistrationError
        if not self.pet.selected_look_id.strip() or not self.pet.selected_look_id.isprintable():
            raise InvalidRegistrationError
        try:
            idempotency_bytes = idempotency_key.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise InvalidRegistrationError from exc
        max_key_bytes = 255
        if "\x00" in idempotency_key or len(idempotency_bytes) > max_key_bytes:
            raise InvalidRegistrationError

    def request_digest(self) -> str:
        return sha256(
            json.dumps(
                asdict(self),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
            ).encode("utf-8"),
        ).hexdigest()


@dataclass(frozen=True, slots=True, kw_only=True)
class RegisterProfileResult:
    device_id: str
    created: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class RegisteredProfile:
    profile_id: UUID
    device_id: str
    pet: RegisteredPet


@dataclass(frozen=True, slots=True, kw_only=True)
class RegistrationReceipt:
    profile_id: UUID
    idempotency_key: str
    request_digest: str
    result: RegisterProfileResult
