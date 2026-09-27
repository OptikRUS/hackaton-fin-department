from uuid import UUID

import pytest
from httpx2 import codes

from src.core.analytics.exceptions import (
    AnalyticsFactConflictError,
    AnalyticsStaleError,
    AssessmentNotReadyError,
    UnsupportedAnalyticsSchemaError,
)
from src.core.analytics.schemas import (
    AnalyticsUploadParams,
    AnalyticsUploadResult,
    SkillAssessment,
    SkillAssessments,
)
from src.core.analytics.use_cases import GetSkillAssessmentsUseCase, UploadAnalyticsUseCase
from src.core.profiles.schemas import DeviceId
from src.tests.fixtures import APIFixture, ContainerFixture, FactoryFixture


class TestUploadAnalyticsAPI(APIFixture, ContainerFixture, FactoryFixture):
    @pytest.fixture(autouse=True)
    async def setup(self) -> None:
        self.use_case = await self.container_helper.override_use_case(
            use_case_type=UploadAnalyticsUseCase,
        )

    async def test_upload_returns_ack_with_exact_ids_and_invokes_use_case(self) -> None:
        self.use_case.execute.return_value = AnalyticsUploadResult(
            batch_id="batch-1",
            game_run_id="run-1",
            accepted_through_history_sequence=0,
            accepted_event_ids=(),
            created=True,
        )
        skills = self.factory.analytics.upload_params(profile_id=UUID(int=1)).skills

        response = await self.api.upload_analytics(
            device_id="9f1c2d3e4a5b6078",
            idempotency_key="batch-1",
            batch_id="batch-1",
            game_run_id="run-1",
            through_history_sequence=0,
            facts=[],
            skills=skills,
        )

        assert response.status_code == codes.OK
        assert response.json() == {
            "schemaVersion": 1,
            "batchId": "batch-1",
            "gameRunId": "run-1",
            "acceptedThroughHistorySequence": 0,
            "acceptedEventIds": [],
        }
        self.use_case.execute.assert_awaited_once_with(
            params=AnalyticsUploadParams(
                profile_id=DeviceId(value="9f1c2d3e4a5b6078").profile_id,
                batch_id="batch-1",
                game_run_id="run-1",
                through_history_sequence=0,
                projection_version=4,
                evaluator_version=1,
                facts=[],
                skills=skills,
                schema_version=1,
            ),
            idempotency_key="batch-1",
        )

    async def test_replay_ack_returns_ok(self) -> None:
        self.use_case.execute.return_value = AnalyticsUploadResult(
            batch_id="batch-1",
            game_run_id="run-1",
            accepted_through_history_sequence=0,
            accepted_event_ids=(),
            created=False,
        )

        response = await self.api.upload_analytics(
            device_id="9f1c2d3e4a5b6078",
            idempotency_key="batch-1",
            batch_id="batch-1",
            game_run_id="run-1",
            through_history_sequence=0,
            facts=[],
            skills=self.factory.analytics.upload_params(profile_id=UUID(int=1)).skills,
        )

        assert response.status_code == codes.OK
        assert response.json() == {
            "schemaVersion": 1,
            "batchId": "batch-1",
            "gameRunId": "run-1",
            "acceptedThroughHistorySequence": 0,
            "acceptedEventIds": [],
        }

    async def test_malformed_body_is_rejected_before_use_case(self) -> None:
        skills = self.factory.analytics.upload_params(profile_id=UUID(int=1)).skills[:-1]

        response = await self.api.upload_analytics(
            device_id="9f1c2d3e4a5b6078",
            idempotency_key="batch-1",
            batch_id="batch-1",
            game_run_id="run-1",
            through_history_sequence=0,
            facts=[],
            skills=skills,
        )

        assert response.status_code == codes.BAD_REQUEST
        assert response.json() == {"code": "INVALID_REQUEST"}
        self.use_case.execute.assert_not_awaited()

    async def test_unknown_skill_code_is_unsupported_schema(self) -> None:
        skills = self.factory.analytics.upload_params(profile_id=UUID(int=1)).skills
        skills[0]["skillId"] = "FIN-99"

        response = await self.api.upload_analytics(
            device_id="9f1c2d3e4a5b6078",
            idempotency_key="batch-1",
            batch_id="batch-1",
            game_run_id="run-1",
            through_history_sequence=0,
            facts=[],
            skills=skills,
        )

        assert response.status_code == codes.UNPROCESSABLE_CONTENT
        assert response.json() == {"code": "UNSUPPORTED_SCHEMA"}
        self.use_case.execute.assert_not_awaited()

    async def test_invalid_reason_type_is_invalid_request(self) -> None:
        skills = self.factory.analytics.upload_params(profile_id=UUID(int=1)).skills
        skills[0]["observations"] = [
            {
                "gameRunId": "run-1",
                "skill": "FIN-01",
                "episodeId": "episode-1",
                "outcome": "SUPPORTED",
                "eligibility": "ELIGIBLE",
                "completion": "COMPLETE",
                "reason": 7,
                "sourceEventIds": [],
                "assistance": [],
                "adultHelpKnown": False,
                "learningContexts": ["GAME"],
                "contextFamilies": ["lesson-1"],
            }
        ]

        response = await self.api.upload_analytics(
            device_id="9f1c2d3e4a5b6078",
            idempotency_key="batch-1",
            batch_id="batch-1",
            game_run_id="run-1",
            through_history_sequence=0,
            facts=[],
            skills=skills,
        )

        assert response.status_code == codes.BAD_REQUEST
        assert response.json() == {"code": "INVALID_REQUEST"}
        self.use_case.execute.assert_not_awaited()

    async def test_fact_conflict_maps_to_contract_error(self) -> None:
        self.use_case.execute.side_effect = AnalyticsFactConflictError

        response = await self.api.upload_analytics(
            device_id="9f1c2d3e4a5b6078",
            idempotency_key="batch-1",
            batch_id="batch-1",
            game_run_id="run-1",
            through_history_sequence=0,
            facts=[],
            skills=self.factory.analytics.upload_params(profile_id=UUID(int=1)).skills,
        )

        assert response.status_code == codes.CONFLICT
        assert response.json() == {"code": "FACT_CONFLICT"}

    async def test_stale_projection_maps_to_contract_error(self) -> None:
        self.use_case.execute.side_effect = AnalyticsStaleError

        response = await self.api.upload_analytics(
            device_id="9f1c2d3e4a5b6078",
            idempotency_key="batch-1",
            batch_id="batch-1",
            game_run_id="run-1",
            through_history_sequence=0,
            facts=[],
            skills=self.factory.analytics.upload_params(profile_id=UUID(int=1)).skills,
        )

        assert response.status_code == codes.CONFLICT
        assert response.json() == {"code": "STALE_ANALYTICS"}

    async def test_unsupported_version_returns_schema_error(self) -> None:
        self.use_case.execute.side_effect = UnsupportedAnalyticsSchemaError

        response = await self.api.upload_analytics(
            device_id="9f1c2d3e4a5b6078",
            idempotency_key="batch-1",
            batch_id="batch-1",
            game_run_id="run-1",
            through_history_sequence=0,
            facts=[],
            skills=self.factory.analytics.upload_params(profile_id=UUID(int=1)).skills,
            projection_version=5,
        )

        assert response.status_code == codes.UNPROCESSABLE_CONTENT
        assert response.json() == {"code": "UNSUPPORTED_SCHEMA"}
        self.use_case.execute.assert_awaited_once()


class TestGetSkillAssessmentsAPI(APIFixture, ContainerFixture, FactoryFixture):
    @pytest.fixture(autouse=True)
    async def setup(self) -> None:
        self.use_case = await self.container_helper.override_use_case(
            use_case_type=GetSkillAssessmentsUseCase,
        )

    async def test_get_skills_returns_versioned_assessment(self) -> None:
        self.use_case.execute.return_value = SkillAssessments(
            game_run_id="run-1",
            based_on_history_sequence=8,
            skills=tuple(
                SkillAssessment(
                    skill_id=f"FIN-{number:02}",
                    status="NO_DATA",
                    policy_version="policy-1",
                )
                for number in range(1, 13)
            ),
        )

        response = await self.api.get_skills(
            device_id="9f1c2d3e4a5b6078",
            game_run_id="run-1",
        )

        assert response.status_code == codes.OK
        assert response.json() == {
            "schemaVersion": 1,
            "gameRunId": "run-1",
            "basedOnHistorySequence": 8,
            "skills": [
                {
                    "skillId": f"FIN-{number:02}",
                    "status": "NO_DATA",
                    "policyVersion": "policy-1",
                }
                for number in range(1, 13)
            ],
        }
        self.use_case.execute.assert_awaited_once_with(
            profile_id=DeviceId(value="9f1c2d3e4a5b6078").profile_id,
            game_run_id="run-1",
        )

    async def test_no_policy_is_not_ready(self) -> None:
        self.use_case.execute.side_effect = AssessmentNotReadyError

        response = await self.api.get_skills(
            device_id="9f1c2d3e4a5b6078",
            game_run_id="run-1",
        )

        assert response.status_code == codes.CONFLICT
        assert response.json() == {"code": "ASSESSMENT_NOT_READY"}
        self.use_case.execute.assert_awaited_once_with(
            profile_id=DeviceId(value="9f1c2d3e4a5b6078").profile_id,
            game_run_id="run-1",
        )
