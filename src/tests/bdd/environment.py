from unittest.mock import AsyncMock

from behave.model import Scenario, Table
from behave.runner import Context as BehaveContext

from src.core.analytics.storages import AnalyticsStorage
from src.core.parents.exceptions import ParentReportNotFoundError
from src.core.parents.schemas import ParentReport
from src.core.pets.schemas import Pet
from src.core.pets.storages import PetStorage
from src.core.profiles.storages import ProfileStorage
from src.core.snapshots.storages import SnapshotStorage
from src.tests.bdd.helpers.bdd import BehaveHelper
from src.tests.bdd.helpers.behave_helpers.asserts import BehaveAssertsHelper
from src.tests.bdd.helpers.behave_helpers.parse import BehaveParseHelper
from src.tests.bdd.helpers.storage import PetStorageHelper
from src.tests.helpers.factory import FactoryHelper
from src.tests.mocks.pets.storages import MockPetStorage


class Context(BehaveContext):
    table: Table
    factory: FactoryHelper
    bdd: BehaveHelper
    pet_result: Pet | None
    pet_storage: AsyncMock
    pet_storage_fake: MockPetStorage
    pet_storage_helper: PetStorageHelper
    parent_profile_storage: AsyncMock
    parent_snapshot_storage: AsyncMock
    parent_analytics_storage: AsyncMock
    parent_report: ParentReport | None
    parent_error: ParentReportNotFoundError | None
    parent_device_id: str | None


def before_scenario(context: Context, _: Scenario) -> None:
    context.factory = FactoryHelper()
    context.bdd = BehaveHelper(
        context=context,
        factory=context.factory,
        asserts=BehaveAssertsHelper(context=context),
        parse=BehaveParseHelper(context=context, factory=context.factory),
    )
    context.pet_storage_fake = MockPetStorage()
    context.pet_storage_helper = PetStorageHelper(
        context=context,
        storage=context.pet_storage_fake,
    )
    context.pet_storage = AsyncMock(spec=PetStorage, wraps=context.pet_storage_fake)
    context.pet_result = None
    context.parent_profile_storage = AsyncMock(spec=ProfileStorage)
    context.parent_snapshot_storage = AsyncMock(spec=SnapshotStorage)
    context.parent_analytics_storage = AsyncMock(spec=AnalyticsStorage)
    context.parent_profile_storage.get_profile.return_value = None
    context.parent_snapshot_storage.get_latest.return_value = None
    context.parent_analytics_storage.get_assessment.return_value = None
    context.parent_report = None
    context.parent_error = None
    context.parent_device_id = None
