from typing import Annotated, Any, Literal, Self

from pydantic import ConfigDict, Field, field_validator

from src.core.analytics.enums import FactDetailType, ObservationReason
from src.core.analytics.schemas import (
    AnalyticsUploadParams,
    AnalyticsUploadResult,
    SkillAssessments,
)
from src.core.profiles.schemas import DeviceId
from src.infra.api.boundary import BoundaryModel

type SkillId = Literal[
    "FIN-01",
    "FIN-02",
    "FIN-03",
    "FIN-04",
    "FIN-05",
    "FIN-06",
    "FIN-07",
    "FIN-08",
    "FIN-09",
    "FIN-10",
    "FIN-11",
    "FIN-12",
]


class StrictBoundaryModel(BoundaryModel):
    model_config = ConfigDict(extra="forbid")


class AnalyticsFactRequest(StrictBoundaryModel):
    event_id: Annotated[str, Field(min_length=1)]
    game_run_id: Annotated[str, Field(min_length=1)]
    episode_id: Annotated[str, Field(min_length=1)]
    action_id: Annotated[str, Field(min_length=1)]
    sequence: Annotated[int, Field(ge=0)]
    detail: dict[str, Any]
    context: dict[str, Any] = Field(default_factory=dict)
    mode: Literal["REAL", "DEMO", "SIMULATION"] = "REAL"
    actor: Literal["CHILD", "SYSTEM", "PARENT"] = "CHILD"
    learning_context: Literal["GAME", "COUNTERFACTUAL", "TRAINING"] = "GAME"
    context_family: Annotated[str, Field(min_length=1)] = "unspecified"
    content_version: Annotated[str, Field(min_length=1)] = "1"
    game_rules_version: Annotated[str, Field(min_length=1)] = "1"
    schema_version: Annotated[int, Field(ge=1)] = 1

    @field_validator("detail")
    @classmethod
    def known_detail_type(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(value.get("_type"), str) or value["_type"] not in FactDetailType:
            message = "Unsupported fact detail type"
            raise ValueError(message)
        return value


class SkillObservationRequest(StrictBoundaryModel):
    game_run_id: str
    skill: SkillId
    episode_id: str
    outcome: Literal["SUPPORTED", "DIFFICULTY", "NEUTRAL", "INSUFFICIENT_DATA"]
    eligibility: Literal["ELIGIBLE", "NOT_ELIGIBLE", "UNDETERMINED"]
    completion: Literal["COMPLETE", "PENDING"]
    reason: ObservationReason
    source_event_ids: list[str]
    assistance: list[
        Literal[
            "INFORMATION_ONLY",
            "HINT",
            "WORKED_EXAMPLE",
            "ANSWER_REVEALED",
            "ADULT_REPORTED",
        ]
    ]
    adult_help_known: bool
    learning_contexts: list[Literal["GAME", "COUNTERFACTUAL", "TRAINING"]]
    context_families: list[str]
    measures: dict[str, int] = Field(default_factory=dict)
    rule_version: Annotated[int, Field(ge=1)] = 1


class SkillEvidenceRequest(StrictBoundaryModel):
    skill_id: SkillId
    completed_episodes: Annotated[int, Field(ge=0)]
    supported_episodes: Annotated[int, Field(ge=0)]
    difficulty_episodes: Annotated[int, Field(ge=0)]
    neutral_episodes: Annotated[int, Field(ge=0)]
    pending_episodes: Annotated[int, Field(ge=0)]
    incomplete_episodes: Annotated[int, Field(ge=0)]
    supported_without_game_hints: Annotated[int, Field(ge=0)]
    assisted_episodes: Annotated[int, Field(ge=0)]
    observations: list[SkillObservationRequest]


class AnalyticsUploadRequest(StrictBoundaryModel):
    device_id: Annotated[str, Field(min_length=1)]
    batch_id: Annotated[str, Field(min_length=1, max_length=255)]
    game_run_id: Annotated[str, Field(min_length=1)]
    through_history_sequence: Annotated[int, Field(ge=0)]
    facts: list[AnalyticsFactRequest]
    skills: Annotated[list[SkillEvidenceRequest], Field(min_length=12, max_length=12)]
    schema_version: Annotated[int, Field(ge=1)] = 1
    projection_version: Annotated[int, Field(ge=1)] = 4
    evaluator_version: Annotated[int, Field(ge=1)] = 1

    def to_domain(self) -> AnalyticsUploadParams:
        return AnalyticsUploadParams(
            profile_id=DeviceId(value=self.device_id).profile_id,
            batch_id=self.batch_id,
            game_run_id=self.game_run_id,
            through_history_sequence=self.through_history_sequence,
            projection_version=self.projection_version,
            evaluator_version=self.evaluator_version,
            facts=[fact.dict(exclude_unset=True) for fact in self.facts],
            skills=[skill.dict(exclude_unset=True) for skill in self.skills],
            schema_version=self.schema_version,
        )


class AnalyticsUploadResponse(BoundaryModel):
    batch_id: str
    game_run_id: str
    accepted_through_history_sequence: int
    accepted_event_ids: list[str]
    schema_version: Literal[1] = 1

    @classmethod
    def from_domain(cls, *, result: AnalyticsUploadResult) -> Self:
        return cls(
            batch_id=result.batch_id,
            game_run_id=result.game_run_id,
            accepted_through_history_sequence=result.accepted_through_history_sequence,
            accepted_event_ids=list(result.accepted_event_ids),
        )


class SkillAssessmentsRequest(StrictBoundaryModel):
    device_id: Annotated[str, Field(min_length=1)]
    game_run_id: Annotated[str, Field(min_length=1)]
    schema_version: Literal[1] = 1


class SkillAssessmentResponse(BoundaryModel):
    skill_id: SkillId
    status: Literal["MASTERED", "PRACTICING", "NO_DATA", "HAS_PROBLEM"]
    policy_version: str


class SkillAssessmentsResponse(BoundaryModel):
    game_run_id: str
    based_on_history_sequence: int
    skills: Annotated[list[SkillAssessmentResponse], Field(min_length=12, max_length=12)]
    schema_version: Literal[1] = 1

    @classmethod
    def from_domain(cls, *, assessment: SkillAssessments) -> Self:
        return cls(
            game_run_id=assessment.game_run_id,
            based_on_history_sequence=assessment.based_on_history_sequence,
            skills=[
                SkillAssessmentResponse.parse({
                    "skillId": skill.skill_id,
                    "status": skill.status,
                    "policyVersion": skill.policy_version,
                })
                for skill in assessment.skills
            ],
        )


class AnalyticsError(BoundaryModel):
    code: str
    message: str | None = None
    request_id: str | None = None
