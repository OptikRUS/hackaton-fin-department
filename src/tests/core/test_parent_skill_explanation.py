from dataclasses import replace
from unittest.mock import AsyncMock

import pytest

from src.core.analytics.storages import AnalyticsStorage
from src.core.parents.use_cases import GetParentReportUseCase
from src.core.profiles.schemas import DeviceId
from src.core.profiles.storages import ProfileStorage
from src.core.snapshots.storages import SnapshotStorage
from src.tests.helpers.factory import FactoryHelper


@pytest.mark.asyncio
async def test_parent_report_uses_assessment_for_latest_snapshot_run() -> None:
    factory = FactoryHelper()
    device_id = "device-1"
    profile_id = DeviceId(value=device_id).profile_id
    explanation = {
        "version": 1,
        "description": "Учится сравнивать суммы.",
        "summary": "Есть наблюдение.",
        "evidence": [],
    }
    profile_storage = AsyncMock(spec=ProfileStorage)
    profile_storage.get_profile.return_value = factory.profiles.registered_profile(
        profile_id=profile_id, device_id=device_id
    )
    snapshot_storage = AsyncMock(spec=SnapshotStorage)
    snapshot_storage.get_latest.return_value = factory.snapshots.snapshot(
        profile_id=profile_id, game_run_id="current-run"
    )
    analytics_storage = AsyncMock(spec=AnalyticsStorage)
    assessment = factory.analytics.assessment(status="PRACTICING")
    analytics_storage.get_assessment.return_value = replace(
        assessment,
        game_run_id="current-run",
        skills=(
            replace(assessment.skills[0], explanation=explanation),
            *assessment.skills[1:],
        ),
    )
    use_case = GetParentReportUseCase(
        profile_storage=profile_storage,
        snapshot_storage=snapshot_storage,
        analytics_storage=analytics_storage,
    )

    report = await use_case.execute(device_id=device_id)

    analytics_storage.get_assessment.assert_awaited_once_with(
        profile_id=profile_id, game_run_id="current-run"
    )
    assert report.skill_statuses[0].status == "PRACTICING"
    assert report.skill_statuses[0].explanation == explanation
    assert report.skill_statuses[1].explanation is None
