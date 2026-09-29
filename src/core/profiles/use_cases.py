from dataclasses import dataclass

from src.core.metrics import MetricsSink
from src.core.profiles.exceptions import (
    ProfileConflictError,
    RegistrationIdempotencyConflictError,
)
from src.core.profiles.schemas import (
    RegisteredProfile,
    RegisterProfileParams,
    RegisterProfileResult,
    RegistrationReceipt,
)
from src.core.profiles.storages import ProfileStorage
from src.core.use_case import UseCase


@dataclass(frozen=True, slots=True, kw_only=True)
class RegisterProfileUseCase(UseCase):
    storage: ProfileStorage
    metrics: MetricsSink | None = None

    async def execute(
        self,
        *,
        params: RegisterProfileParams,
        idempotency_key: str,
    ) -> RegisterProfileResult:
        params.validate(idempotency_key=idempotency_key)
        request_digest = params.request_digest()
        created_profile = await self.storage.create_profile(
            profile=RegisteredProfile(
                profile_id=params.profile_id,
                device_id=params.device_id,
                pet=params.pet,
            ),
        )
        profile = await self.storage.get_profile(profile_id=params.profile_id)
        receipt = await self.storage.get_registration(
            profile_id=params.profile_id,
            idempotency_key=idempotency_key,
        )
        if receipt is not None:
            if receipt.request_digest != request_digest:
                raise RegistrationIdempotencyConflictError
            return receipt.result
        if profile is None or profile.device_id != params.device_id or profile.pet != params.pet:
            raise ProfileConflictError
        result = RegisterProfileResult(
            device_id=params.device_id, created=created_profile is not None
        )
        await self.storage.insert_registration(
            receipt=RegistrationReceipt(
                profile_id=params.profile_id,
                idempotency_key=idempotency_key,
                request_digest=request_digest,
                result=result,
            ),
        )
        if self.metrics is not None:
            self.metrics.observe_profile_registration(created=result.created)
        return result
