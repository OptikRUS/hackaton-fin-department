from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.profiles.schemas import RegisteredPet, RegisteredProfile, RegistrationReceipt
from src.core.profiles.storages import ProfileStorage
from src.infra.storages.postgres.models import ProfileModel, ProfileRegistrationModel


@dataclass(kw_only=True, slots=True)
class PostgresProfileStorage(ProfileStorage):
    session: AsyncSession

    async def get_profile(self, *, profile_id: UUID) -> RegisteredProfile | None:
        model = await self.session.scalar(
            select(ProfileModel)
            .where(ProfileModel.profile_id == profile_id)
            .execution_options(populate_existing=True)
            .with_for_update(),
        )
        return model.to_domain() if model is not None else None

    async def create_profile(self, *, profile: RegisteredProfile) -> RegisteredProfile | None:
        value = ProfileModel.from_domain(profile=profile)
        model = await self.session.scalar(
            insert(ProfileModel)
            .values(
                profile_id=value.profile_id,
                device_id=value.device_id,
                pet_json=value.pet_json,
            )
            .on_conflict_do_nothing()
            .returning(ProfileModel),
        )
        return model.to_domain() if model is not None else None

    async def update_pet(self, *, profile_id: UUID, pet: RegisteredPet) -> None:
        await self.session.execute(
            update(ProfileModel)
            .where(ProfileModel.profile_id == profile_id)
            .values(
                pet_json={
                    "name": pet.name,
                    "age": pet.age,
                    "color": pet.color,
                    "temperament": pet.temperament,
                    "selectedLookId": pet.selected_look_id,
                }
            )
        )

    async def get_registration(
        self,
        *,
        profile_id: UUID,
        idempotency_key: str,
    ) -> RegistrationReceipt | None:
        model = await self.session.scalar(
            select(ProfileRegistrationModel)
            .where(
                ProfileRegistrationModel.profile_id == profile_id,
                ProfileRegistrationModel.idempotency_key == idempotency_key,
            )
            .execution_options(populate_existing=True),
        )
        return model.to_domain() if model is not None else None

    async def insert_registration(self, *, receipt: RegistrationReceipt) -> RegistrationReceipt:
        model = (
            await self.session.scalars(
                insert(ProfileRegistrationModel)
                .values(
                    profile_id=receipt.profile_id,
                    idempotency_key=receipt.idempotency_key,
                    request_digest=receipt.request_digest,
                    device_id=receipt.result.device_id,
                    created=receipt.result.created,
                )
                .returning(ProfileRegistrationModel),
            )
        ).one()
        return model.to_domain()
