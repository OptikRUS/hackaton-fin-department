import json
from pathlib import Path
from uuid import UUID

import pytest
from pydantic import ValidationError

from src.core.analytics.exceptions import InvalidAnalyticsError, UnsupportedAnalyticsSchemaError
from src.core.analytics.schemas import SkillAssessment, SkillAssessments
from src.core.parents.schemas import ParentPet, ParentReport, ParentSkillStatus
from src.infra.api.analytics.schemas import AnalyticsUploadRequest, SkillAssessmentsResponse
from src.infra.api.parents.schemas import ParentResponse
from src.infra.api.parents.skill_content import ParentMaterialsResponse
from src.infra.storages.postgres.models import SkillAssessmentModel


def test_mobile_explanation_survives_analytics_request_boundary() -> None:
    body = json.loads(
        (Path(__file__).parents[1] / "data/android-analytics-upload.json").read_text()
    )
    explanation = {
        "version": 1,
        "description": "Учится сравнивать суммы.",
        "summary": "Пока мало данных.",
        "evidence": [],
    }
    for skill in body["skills"]:
        skill["explanation"] = explanation

    params = AnalyticsUploadRequest.parse(body).to_domain()
    params.validate(idempotency_key=body["batchId"])

    assert all(skill["explanation"] == explanation for skill in params.skills)
    assert (
        params.request_digest()
        != AnalyticsUploadRequest
        .parse({
            **body,
            "skills": [
                {key: value for key, value in skill.items() if key != "explanation"}
                for skill in body["skills"]
            ],
        })
        .to_domain()
        .request_digest()
    )


def test_skill_explanation_evidence_must_match_an_observation() -> None:
    body = json.loads(
        (Path(__file__).parents[1] / "data/android-analytics-upload.json").read_text()
    )
    body["skills"][0]["explanation"] = {
        "version": 1,
        "description": "Учится сравнивать суммы.",
        "summary": "Пока мало данных.",
        "evidence": [
            {
                "episodeId": "missing",
                "sourceEventIds": ["missing"],
                "text": "Сравнил суммы.",
            }
        ],
    }

    with pytest.raises(InvalidAnalyticsError):
        AnalyticsUploadRequest.parse(body).to_domain().validate(idempotency_key=body["batchId"])


def test_skill_explanation_is_returned_with_assessment() -> None:
    explanation = {
        "version": 1,
        "description": "Учится сравнивать суммы.",
        "summary": "Пока мало данных.",
        "evidence": [],
    }
    assessment = SkillAssessments(
        game_run_id="run-1",
        based_on_history_sequence=1,
        skills=tuple(
            SkillAssessment(
                skill_id=f"FIN-{index:02}",
                status="NO_DATA",
                policy_version="skills-mvp-v1",
                explanation=explanation,
            )
            for index in range(1, 13)
        ),
    )
    stored = SkillAssessmentModel.from_domain(profile_id=UUID(int=1), assessment=assessment)

    response = SkillAssessmentsResponse.from_domain(assessment=stored.to_domain())

    assert all(skill.explanation is not None for skill in response.skills)
    assert response.skills[0].explanation is not None
    assert response.skills[0].explanation.dict() == explanation


def test_unsupported_saved_explanation_is_omitted_without_losing_status() -> None:
    assessment = SkillAssessments(
        game_run_id="run-1",
        based_on_history_sequence=1,
        skills=tuple(
            SkillAssessment(
                skill_id=f"FIN-{index:02}",
                status="PRACTICING",
                policy_version="skills-mvp-v1",
                explanation={
                    "version": 2,
                    "description": "Описание.",
                    "summary": "Сводка.",
                    "evidence": [],
                }
                if index == 1
                else None,
            )
            for index in range(1, 13)
        ),
    )

    response = SkillAssessmentsResponse.from_domain(assessment=assessment)

    assert response.skills[0].status == "PRACTICING"
    assert "explanation" not in response.skills[0].dict()
    assert "explanation" not in response.skills[1].dict()


def test_unsupported_explanation_version_is_a_schema_error() -> None:
    body = json.loads(
        (Path(__file__).parents[1] / "data/android-analytics-upload.json").read_text()
    )
    body["skills"][0]["explanation"] = {
        "version": 2,
        "description": "Описание.",
        "summary": "Сводка.",
        "evidence": [],
    }

    with pytest.raises(UnsupportedAnalyticsSchemaError):
        AnalyticsUploadRequest.parse(body).to_domain().validate(idempotency_key=body["batchId"])


@pytest.mark.parametrize("text", [" ", "Неверный\u0000текст"])
def test_blank_or_nul_explanation_is_invalid_analytics(text: str) -> None:
    body = json.loads(
        (Path(__file__).parents[1] / "data/android-analytics-upload.json").read_text()
    )
    body["skills"][0]["explanation"] = {
        "version": 1,
        "description": text,
        "summary": "Сводка.",
        "evidence": [],
    }

    with pytest.raises(InvalidAnalyticsError):
        AnalyticsUploadRequest.parse(body).to_domain().validate(idempotency_key=body["batchId"])


def test_missing_explanation_version_is_a_request_error() -> None:
    body = json.loads(
        (Path(__file__).parents[1] / "data/android-analytics-upload.json").read_text()
    )
    body["skills"][0]["explanation"] = {
        "description": "Описание.",
        "summary": "Сводка.",
        "evidence": [],
    }

    with pytest.raises(ValidationError):
        AnalyticsUploadRequest.parse(body)


def test_parent_response_includes_saved_skill_explanation() -> None:
    explanation = {
        "version": 1,
        "description": "Учится сравнивать суммы.",
        "summary": "Пока мало данных.",
        "evidence": [],
    }
    report = ParentReport(
        pet=ParentPet(
            id="device-1",
            name="Лис",
            temper=None,
            balance=None,
            selected_look_id="PLAIN",
            visual_state=None,
        ),
        skill_statuses=tuple(
            ParentSkillStatus(
                skill_id=f"FIN-{index:02}",
                status="NO_DATA",
                explanation=explanation if index == 1 else None,
            )
            for index in range(1, 13)
        ),
    )
    materials = ParentMaterialsResponse.parse({
        "schemaVersion": 1,
        "contentVersion": "unpublished",
        "publicationStatus": "UNPUBLISHED",
        "skills": [],
    })

    response = ParentResponse.from_domain(report=report, materials=materials)

    assert response.skills[0].explanation is not None
    assert response.skills[0].explanation.dict() == explanation
    assert "explanation" not in response.skills[1].dict()


def test_parent_response_omits_unsupported_saved_explanation() -> None:
    report = ParentReport(
        pet=ParentPet(
            id="device-1",
            name="Лис",
            temper=None,
            balance=None,
            selected_look_id="PLAIN",
            visual_state=None,
        ),
        skill_statuses=tuple(
            ParentSkillStatus(
                skill_id=f"FIN-{index:02}",
                status="PRACTICING",
                explanation={
                    "version": 2,
                    "description": "Описание.",
                    "summary": "Сводка.",
                    "evidence": [],
                }
                if index == 1
                else None,
            )
            for index in range(1, 13)
        ),
    )
    materials = ParentMaterialsResponse.parse({
        "schemaVersion": 1,
        "contentVersion": "unpublished",
        "publicationStatus": "UNPUBLISHED",
        "skills": [],
    })

    response = ParentResponse.from_domain(report=report, materials=materials)

    assert response.skills[0].status == "PRACTICING"
    assert "explanation" not in response.skills[0].dict()


def test_explanation_is_optional_in_both_response_schemas() -> None:
    for response_type, skill_name in (
        (SkillAssessmentsResponse, "SkillAssessmentResponse"),
        (ParentResponse, "SkillResponse"),
    ):
        schema = response_type.model_json_schema(by_alias=True)
        skill_schema = schema["$defs"][skill_name]
        explanation_schema = schema["$defs"]["SkillExplanation"]

        assert "explanation" in skill_schema["properties"]
        assert "explanation" not in skill_schema["required"]
        assert "version" in explanation_schema["required"]
