import json
from dataclasses import dataclass
from hashlib import sha256
from typing import Any
from uuid import UUID

from src.core.analytics.enums import FactDetailType, ObservationReason
from src.core.analytics.exceptions import (
    InvalidAnalyticsError,
    InvalidAnalyticsRequestError,
    UnsupportedAnalyticsSchemaError,
)


@dataclass(frozen=True, slots=True, kw_only=True)
class AnalyticsUploadParams:
    profile_id: UUID
    batch_id: str
    game_run_id: str
    through_history_sequence: int
    projection_version: int
    evaluator_version: int
    facts: list[dict[str, Any]]
    skills: list[dict[str, Any]]
    schema_version: int = 1

    @staticmethod
    def _nonempty(value: object) -> bool:
        return isinstance(value, str) and bool(value.strip()) and "\x00" not in value

    @staticmethod
    def digest_value(value: object) -> str:
        return sha256(
            json.dumps(
                value, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
            ).encode("utf-8"),
        ).hexdigest()

    def validate(self, *, idempotency_key: str) -> None:
        self._validate_header(idempotency_key=idempotency_key)
        fact_ids = self._validate_facts()
        self._validate_skills(fact_ids=fact_ids)

    def _validate_header(self, *, idempotency_key: str) -> None:
        max_batch_id_bytes = 255
        if not self._nonempty(self.batch_id) or idempotency_key != self.batch_id:
            raise InvalidAnalyticsRequestError
        if len(self.batch_id.encode("utf-8")) > max_batch_id_bytes or not self._nonempty(
            self.game_run_id
        ):
            raise InvalidAnalyticsRequestError
        if (self.schema_version, self.projection_version, self.evaluator_version) != (1, 4, 1):
            raise UnsupportedAnalyticsSchemaError
        if type(self.through_history_sequence) is not int or self.through_history_sequence < 0:
            raise InvalidAnalyticsError
        if not isinstance(self.facts, list) or not isinstance(self.skills, list):
            raise InvalidAnalyticsError

    def _validate_facts(self) -> set[str]:
        fact_ids: set[str] = set()
        for fact in self.facts:
            if not isinstance(fact, dict):
                raise InvalidAnalyticsError
            event_id = fact.get("eventId")
            if (
                not isinstance(event_id, str)
                or not self._nonempty(event_id)
                or event_id in fact_ids
            ):
                raise InvalidAnalyticsError
            fact_ids.add(event_id)
            if event_id.startswith("derived:") and not event_id.startswith(
                f"derived:{self.projection_version}:{self.game_run_id}:"
            ):
                raise InvalidAnalyticsError
            if (
                fact.get("gameRunId") != self.game_run_id
                or not self._nonempty(fact.get("episodeId"))
                or not self._nonempty(fact.get("actionId"))
                or type(fact.get("sequence")) is not int
                or not 0 <= fact["sequence"] <= self.through_history_sequence
            ):
                raise InvalidAnalyticsError
            detail = fact.get("detail")
            if (
                not isinstance(detail, dict)
                or not isinstance(detail.get("_type"), str)
                or detail["_type"] not in FactDetailType
            ):
                raise UnsupportedAnalyticsSchemaError
            if fact.get("schemaVersion", 1) != 1:
                raise UnsupportedAnalyticsSchemaError
            self._validate_detail(detail)
        return fact_ids

    @staticmethod
    def _validate_detail(detail: dict[str, Any]) -> None:
        required_by_type = {
            FactDetailType.INTERACTION: ("name",),
            FactDetailType.TIME_MACHINE_LIFECYCLE: (
                "event",
                "simulationId",
                "resultHash",
                "sourceEntryId",
                "requestedSequence",
                "reachedSequence",
                "status",
            ),
            FactDetailType.PRACTICE_ANSWER: (
                "questionId",
                "kind",
                "selectedAnswerId",
                "expectedAnswerId",
                "attempt",
                "guidedRecovery",
            ),
            FactDetailType.BUDGET_CONFIRMED: (
                "planId",
                "planVersion",
                "allocationBase",
                "needs",
                "wants",
                "savings",
                "reserve",
                "cause",
            ),
            FactDetailType.OPTIONAL_PURCHASE: ("itemId", "price", "purchased"),
            FactDetailType.INCOME_WINDOW: (
                "windowId",
                "closed",
                "historyComplete",
                "managedDecisionIds",
                "knownNeedsMet",
            ),
            FactDetailType.SAVING_MOVEMENT: (
                "operationId",
                "goalId",
                "incomeWindowId",
                "kind",
                "amount",
            ),
            FactDetailType.SAVING_CYCLE_CLOSED: ("goalId", "historyComplete"),
            FactDetailType.SAVING_INTENTION_RESOLVED: (
                "goalId",
                "opportunityId",
                "promisedAmount",
                "depositedAmount",
                "priorityUnchanged",
                "deliberatelySkipped",
            ),
            FactDetailType.DESIRE_DEFERRED: (
                "itemId",
                "price",
                "desireDeclared",
                "priorityId",
            ),
            FactDetailType.PRIORITY_APPLIED: ("priorityId", "operationId", "amount"),
            FactDetailType.PRIORITY_CONFLICT: (
                "priorityId",
                "conditionsUnchanged",
                "alternativePreservedPriority",
                "explanation",
            ),
            FactDetailType.RESERVE_DECISION: (
                "intentionId",
                "declaredAmount",
                "remainingAmount",
                "usedForUnexpectedExpense",
                "intervalClosed",
            ),
            FactDetailType.UNEXPECTED_EXPENSE: (
                "operationId",
                "amount",
                "previouslyDisclosed",
            ),
            FactDetailType.RECOVERY_ACTION: (
                "expenseOperationId",
                "selectedActionId",
                "completed",
            ),
            FactDetailType.RESOURCE_CHOICE: (
                "chosenOptionId",
                "chosenCost",
                "alternativeCost",
                "energyBefore",
                "availableTimeBefore",
                "priorityId",
                "priorityMoney",
                "priorityEnergy",
                "priorityTime",
            ),
            FactDetailType.EARNING_PLAN: (
                "offerId",
                "priorityId",
                "startedDay",
                "deadlineDay",
                "effortRequired",
                "availableEffortAtChoice",
                "maximumReward",
            ),
            FactDetailType.EARNING_COMPLETED: (
                "offerId",
                "day",
                "actualReward",
                "actualRewardAccountedFor",
            ),
            FactDetailType.QUESTION_ANSWER: ("questionId", "attempt", "task"),
            FactDetailType.COMPARABLE_APPLICATION: (
                "comparisonFamily",
                "sourceActionId",
                "priorityPreserved",
            ),
        }
        detail_type = FactDetailType(detail["_type"])
        optional_by_type = {
            FactDetailType.TIME_MACHINE_LIFECYCLE: ("questionId", "submissionId", "attempt"),
            FactDetailType.INCOME_WINDOW: (
                "avoidableUncoveredNeedIds",
                "availableRemedyWasShown",
            ),
            FactDetailType.RESERVE_DECISION: ("applications",),
            FactDetailType.RESOURCE_CHOICE: (
                "chosenPriorityFeasible",
                "alternativePriorityFeasible",
            ),
            FactDetailType.QUESTION_ANSWER: (
                "answerWasRevealed",
                "seriesClosed",
                "comparisonFamily",
                "simulationId",
            ),
        }
        required = set(required_by_type[detail_type])
        allowed = required | set(optional_by_type.get(detail_type, ())) | {"_type"}
        if not required <= detail.keys() or not detail.keys() <= allowed:
            raise InvalidAnalyticsError
        if not AnalyticsUploadParams._detail_primitives_valid(detail, detail_type):
            raise InvalidAnalyticsError
        if not AnalyticsUploadParams._detail_nested_valid(detail):
            raise InvalidAnalyticsError

    @staticmethod
    def _detail_primitives_valid(detail: dict[str, Any], detail_type: FactDetailType) -> bool:
        strings = {
            "name",
            "event",
            "simulationId",
            "resultHash",
            "sourceEntryId",
            "status",
            "questionId",
            "submissionId",
            "kind",
            "selectedAnswerId",
            "expectedAnswerId",
            "planId",
            "cause",
            "itemId",
            "windowId",
            "operationId",
            "goalId",
            "incomeWindowId",
            "opportunityId",
            "priorityId",
            "intentionId",
            "expenseOperationId",
            "selectedActionId",
            "chosenOptionId",
            "offerId",
            "comparisonFamily",
            "sourceActionId",
        }
        nonempty = {
            "simulationId",
            "resultHash",
            "sourceEntryId",
            "status",
            "questionId",
            "selectedAnswerId",
            "expectedAnswerId",
            "planId",
            "itemId",
            "operationId",
            "goalId",
            "incomeWindowId",
            "opportunityId",
            "priorityId",
        }
        nonempty -= {
            FactDetailType.TIME_MACHINE_LIFECYCLE: {"questionId"},
            FactDetailType.QUESTION_ANSWER: {"simulationId"},
            FactDetailType.SAVING_CYCLE_CLOSED: {"goalId"},
        }.get(detail_type, set())
        if detail_type is not FactDetailType.PRIORITY_APPLIED:
            nonempty -= {"priorityId"}
        integers = {
            "requestedSequence",
            "reachedSequence",
            "attempt",
            "planVersion",
            "allocationBase",
            "needs",
            "wants",
            "savings",
            "reserve",
            "price",
            "amount",
            "promisedAmount",
            "depositedAmount",
            "declaredAmount",
            "remainingAmount",
            "usedForUnexpectedExpense",
            "energyBefore",
            "availableTimeBefore",
            "priorityMoney",
            "priorityEnergy",
            "priorityTime",
            "startedDay",
            "deadlineDay",
            "effortRequired",
            "availableEffortAtChoice",
            "maximumReward",
            "day",
            "actualReward",
        }
        positive = {
            "requestedSequence",
            "attempt",
            "planVersion",
            "amount",
            "promisedAmount",
            "startedDay",
            "deadlineDay",
            "day",
        }
        booleans = {
            "guidedRecovery",
            "purchased",
            "closed",
            "historyComplete",
            "knownNeedsMet",
            "availableRemedyWasShown",
            "priorityUnchanged",
            "deliberatelySkipped",
            "desireDeclared",
            "conditionsUnchanged",
            "alternativePreservedPriority",
            "intervalClosed",
            "previouslyDisclosed",
            "completed",
            "chosenPriorityFeasible",
            "alternativePriorityFeasible",
            "actualRewardAccountedFor",
            "answerWasRevealed",
            "seriesClosed",
            "priorityPreserved",
        }
        nullable = {
            "priorityId",
            "explanation",
            "chosenPriorityFeasible",
            "alternativePriorityFeasible",
            "comparisonFamily",
            "simulationId",
        }
        if detail_type is FactDetailType.TIME_MACHINE_LIFECYCLE:
            nullable |= {"questionId", "submissionId", "attempt"}
        enumerations = {
            "event": {
                "time_machine_simulation_started",
                "time_machine_simulation_completed",
                "time_machine_simulation_diverged",
                "time_machine_simulation_unavailable",
                "time_machine_question_presented",
                "time_machine_explanation_shown",
            },
            "kind": (
                {"PLAN_REVIEW", "SAVINGS_REHEARSAL"}
                if detail_type is FactDetailType.PRACTICE_ANSWER
                else {"DEPOSIT", "WITHDRAWAL", "GOAL_PURCHASE"}
            ),
            "cause": {
                "INITIAL",
                "KNOWN_NEED_OMITTED",
                "UNEXPECTED_EXPENSE",
                "NEW_INCOME",
                "UNSPECIFIED",
            },
        }
        for field, value in detail.items():
            if field == "_type" or (value is None and field in nullable):
                continue
            if field in strings and (
                type(value) is not str or (field in nonempty and not value.strip())
            ):
                return False
            if field in integers and (type(value) is not int or value < int(field in positive)):
                return False
            if field in booleans and type(value) is not bool:
                return False
            if field in enumerations and value not in enumerations[field]:
                return False
        return True

    @staticmethod
    def _detail_nested_valid(detail: dict[str, Any]) -> bool:
        for field in ("managedDecisionIds", "avoidableUncoveredNeedIds"):
            if field in detail and (
                not isinstance(detail[field], list)
                or any(type(item) is not str for item in detail[field])
            ):
                return False
        for field in ("chosenCost", "alternativeCost"):
            if field in detail:
                cost = detail[field]
                if (
                    not isinstance(cost, dict)
                    or cost.keys() != {"money", "energy", "time"}
                    or any(type(value) is not int or value < 0 for value in cost.values())
                ):
                    return False
        if "explanation" in detail and detail["explanation"] is not None:
            explanation = detail["explanation"]
            if not AnalyticsUploadParams._explain_cause_valid(explanation):
                return False
        if "applications" in detail:
            applications = detail["applications"]
            if not isinstance(applications, list) or any(
                not isinstance(item, dict)
                or item.keys() != {"expenseOperationId", "amount"}
                or not AnalyticsUploadParams._nonempty(item["expenseOperationId"])
                or type(item["amount"]) is not int
                or item["amount"] < 1
                for item in applications
            ):
                return False
        return "task" not in detail or AnalyticsUploadParams._assessment_task_valid(detail["task"])

    @staticmethod
    def _explain_cause_valid(value: object) -> bool:
        if not isinstance(value, dict) or value.get("_type") != "explain_cause":
            return False
        if not {"_type", "expectedOptionId", "chosenOptionId", "sourceFactIds"} <= value.keys():
            return False
        if not value.keys() <= {
            "_type",
            "expectedOptionId",
            "chosenOptionId",
            "sourceFactIds",
            "purpose",
        }:
            return False
        sources = value["sourceFactIds"]
        return bool(
            AnalyticsUploadParams._nonempty(value["expectedOptionId"])
            and AnalyticsUploadParams._nonempty(value["chosenOptionId"])
            and isinstance(sources, list)
            and bool(sources)
            and all(type(source) is str for source in sources)
            and value.get("purpose", "EXPLAIN_CAUSE") == "EXPLAIN_CAUSE"
        )

    @staticmethod
    def _assessment_task_valid(value: object) -> bool:
        if not isinstance(value, dict):
            return False
        if value.get("_type") == "explain_cause":
            return AnalyticsUploadParams._explain_cause_valid(value)
        if value.get("_type") == "compare_amounts":
            return bool(
                {"_type", "left", "right", "chosen"} <= value.keys()
                and value.keys() <= {"_type", "left", "right", "chosen", "purpose"}
                and all(
                    type(value[field]) is int and value[field] >= 0 for field in ("left", "right")
                )
                and type(value["chosen"]) is str
                and value["chosen"] in {"LEFT", "RIGHT", "EQUAL"}
                and value.get("purpose", "COMPARE_AMOUNTS") == "COMPARE_AMOUNTS"
            )
        if value.get("_type") == "read_ledger":
            required = {
                "_type",
                "openingAvailable",
                "openingSavings",
                "entries",
                "question",
                "answer",
            }
            if not required <= value.keys() or not value.keys() <= required | {"purpose"}:
                return False
            entries = value["entries"]
            return bool(
                type(value["openingAvailable"]) is int
                and value["openingAvailable"] >= 0
                and type(value["openingSavings"]) is int
                and value["openingSavings"] >= 0
                and type(value["answer"]) is int
                and type(value["question"]) is str
                and value["question"]
                in {
                    "INCOME",
                    "EXPENSE",
                    "DEPOSIT",
                    "WITHDRAWAL",
                    "AVAILABLE_REMAINDER",
                    "SAVINGS_REMAINDER",
                }
                and value.get("purpose", "READ_LEDGER") == "READ_LEDGER"
                and isinstance(entries, list)
                and all(
                    isinstance(entry, dict)
                    and entry.keys() == {"operationId", "kind", "amount"}
                    and AnalyticsUploadParams._nonempty(entry["operationId"])
                    and type(entry["kind"]) is str
                    and entry["kind"]
                    in {"INCOME", "AVAILABLE_EXPENSE", "SAVINGS_EXPENSE", "DEPOSIT", "WITHDRAWAL"}
                    and type(entry["amount"]) is int
                    and entry["amount"] >= 0
                    for entry in entries
                )
            )
        return False

    def _validate_skills(self, *, fact_ids: set[str]) -> None:
        skill_ids = {f"FIN-{number:02}" for number in range(1, 13)}
        if (
            len(self.skills) != len(skill_ids)
            or any(not isinstance(skill, dict) for skill in self.skills)
            or {skill.get("skillId") for skill in self.skills} != skill_ids
        ):
            raise InvalidAnalyticsError
        if len({skill["skillId"] for skill in self.skills}) != len(skill_ids):
            raise InvalidAnalyticsError
        counter_names = (
            "completedEpisodes",
            "supportedEpisodes",
            "difficultyEpisodes",
            "neutralEpisodes",
            "pendingEpisodes",
            "incompleteEpisodes",
            "supportedWithoutGameHints",
            "assistedEpisodes",
        )
        for skill in self.skills:
            observations = skill.get("observations")
            if not isinstance(observations, list) or any(
                type(skill.get(name)) is not int or skill[name] < 0 for name in counter_names
            ):
                raise InvalidAnalyticsError
            for observation in observations:
                self._validate_observation(
                    observation, skill_id=skill["skillId"], fact_ids=fact_ids
                )
            self._validate_counters(skill, observations)

    def _validate_observation(
        self,
        observation: dict[str, Any],
        *,
        skill_id: str,
        fact_ids: set[str],
    ) -> None:
        if not isinstance(observation, dict):
            raise InvalidAnalyticsError
        if (
            observation.get("gameRunId") != self.game_run_id
            or observation.get("skill") != skill_id
            or not self._nonempty(observation.get("episodeId"))
        ):
            raise InvalidAnalyticsError
        if (
            not isinstance(observation.get("reason"), str)
            or observation["reason"] not in ObservationReason
        ):
            raise UnsupportedAnalyticsSchemaError
        if any(
            field not in observation
            for field in (
                "outcome",
                "eligibility",
                "completion",
                "sourceEventIds",
                "assistance",
                "adultHelpKnown",
                "learningContexts",
                "contextFamilies",
            )
        ):
            raise InvalidAnalyticsError
        sources = observation.get("sourceEventIds")
        if not isinstance(sources, list) or any(source not in fact_ids for source in sources):
            raise InvalidAnalyticsError
        if observation.get("ruleVersion", 1) != 1:
            raise UnsupportedAnalyticsSchemaError

    @staticmethod
    def _validate_counters(skill: dict[str, Any], observations: list[dict[str, Any]]) -> None:
        direct = {
            "completedEpisodes": sum(
                o["completion"] == "COMPLETE" and o["eligibility"] == "ELIGIBLE"
                for o in observations
            ),
            "supportedEpisodes": sum(o["outcome"] == "SUPPORTED" for o in observations),
            "difficultyEpisodes": sum(o["outcome"] == "DIFFICULTY" for o in observations),
            "neutralEpisodes": sum(o["outcome"] == "NEUTRAL" for o in observations),
            "pendingEpisodes": sum(o["completion"] == "PENDING" for o in observations),
            "incompleteEpisodes": sum(o["outcome"] == "INSUFFICIENT_DATA" for o in observations),
            "supportedWithoutGameHints": sum(
                o["outcome"] == "SUPPORTED"
                and all(a == "INFORMATION_ONLY" for a in o["assistance"])
                for o in observations
            ),
            "assistedEpisodes": sum(
                any(a != "INFORMATION_ONLY" for a in o["assistance"]) for o in observations
            ),
        }
        if any(skill[name] != value for name, value in direct.items()):
            raise InvalidAnalyticsError

    def request_digest(self) -> str:
        return self.digest_value({
            "profileId": str(self.profile_id),
            "batchId": self.batch_id,
            "gameRunId": self.game_run_id,
            "throughHistorySequence": self.through_history_sequence,
            "projectionVersion": self.projection_version,
            "evaluatorVersion": self.evaluator_version,
            "schemaVersion": self.schema_version,
            "facts": self.facts,
            "skills": self.skills,
        })

    def original_digests(self) -> dict[str, str]:
        return {
            fact["eventId"]: self.digest_value(fact)
            for fact in self.facts
            if not fact["eventId"].startswith("derived:")
        }


@dataclass(frozen=True, slots=True, kw_only=True)
class AnalyticsUploadResult:
    batch_id: str
    game_run_id: str
    accepted_through_history_sequence: int
    accepted_event_ids: tuple[str, ...]
    created: bool


@dataclass(frozen=True, slots=True, kw_only=True)
class StoredBatch:
    profile_id: UUID
    request_digest: str
    result: AnalyticsUploadResult


@dataclass(frozen=True, slots=True, kw_only=True)
class SkillAssessment:
    skill_id: str
    status: str
    policy_version: str


@dataclass(frozen=True, slots=True, kw_only=True)
class SkillAssessments:
    game_run_id: str
    based_on_history_sequence: int
    skills: tuple[SkillAssessment, ...]
