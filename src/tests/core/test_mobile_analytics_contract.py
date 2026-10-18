import json
from pathlib import Path
from uuid import UUID

import pytest

from src.core.analytics.exceptions import InvalidAnalyticsError
from src.core.analytics.schemas import SkillAssessment, SkillAssessments
from src.infra.api.analytics.schemas import AnalyticsUploadRequest, SkillAssessmentsResponse
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
