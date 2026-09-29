import json
from typing import Any

import pytest
from prometheus_client import CollectorRegistry

from src.infra.observability.business_metrics import (
    BusinessMetrics,
    get_business_metrics,
    parse_world_sample,
)
from src.tests.helpers.worlds import world_snapshot_document, world_snapshot_json


@pytest.fixture
def registry() -> CollectorRegistry:
    return CollectorRegistry()


@pytest.fixture
def metrics(registry: CollectorRegistry) -> BusinessMetrics:
    return BusinessMetrics(registry=registry)


def _fact(detail: dict[str, Any], *, actor: str = "CHILD", mode: str = "REAL") -> dict[str, Any]:
    return {
        "eventId": f"event-{json.dumps(detail, sort_keys=True)}",
        "gameRunId": "run-1",
        "episodeId": "episode-1",
        "actionId": "action-1",
        "sequence": 1,
        "detail": detail,
        "actor": actor,
        "mode": mode,
    }


class TestUseCaseCounters:
    def test_snapshot_upload_counts_created_flag(
        self, registry: CollectorRegistry, metrics: BusinessMetrics
    ) -> None:
        metrics.observe_snapshot_upload(created=True)
        metrics.observe_snapshot_upload(created=True)
        metrics.observe_snapshot_upload(created=False)

        assert registry.get_sample_value("fin_snapshot_uploads_total", {"created": "True"}) == 2
        assert registry.get_sample_value("fin_snapshot_uploads_total", {"created": "False"}) == 1

    def test_analytics_batch_counts_facts_by_type(
        self, registry: CollectorRegistry, metrics: BusinessMetrics
    ) -> None:
        facts = [
            _fact({"_type": "interaction", "name": "RenamePet"}),
            _fact({"_type": "interaction", "name": "BeginDay"}),
            _fact({"_type": "optional_purchase", "itemId": "ball", "price": 50, "purchased": True}),
            _fact(
                {"_type": "optional_purchase", "itemId": "hat", "price": 30, "purchased": False},
                actor="PARENT",
            ),
        ]
        metrics.observe_analytics_batch(created=True, facts=facts)

        assert registry.get_sample_value("fin_analytics_batches_total", {"created": "True"}) == 1
        assert registry.get_sample_value("fin_interactions_total", {"name": "RenamePet"}) == 1
        assert registry.get_sample_value("fin_optional_purchases_total", {"purchased": "True"}) == 1
        assert registry.get_sample_value("fin_purchase_amount_total", {"purchased": "False"}) == 30

    def test_replayed_batch_does_not_double_count(
        self, registry: CollectorRegistry, metrics: BusinessMetrics
    ) -> None:
        metrics.observe_analytics_batch(
            created=False, facts=[_fact({"_type": "interaction", "name": "BeginDay"})]
        )

        assert (
            registry.get_sample_value(
                "fin_analytics_facts_total",
                {"detail_type": "interaction", "actor": "CHILD", "mode": "REAL"},
            )
            is None
        )

    def test_financial_facts_are_observed(
        self, registry: CollectorRegistry, metrics: BusinessMetrics
    ) -> None:
        metrics.observe_analytics_batch(
            created=True,
            facts=[
                _fact({
                    "_type": "budget_confirmed",
                    "planId": "p1",
                    "planVersion": 1,
                    "allocationBase": 1000,
                    "needs": 500,
                    "wants": 200,
                    "savings": 200,
                    "reserve": 100,
                    "cause": "INITIAL",
                }),
                _fact({
                    "_type": "practice_answer",
                    "questionId": "q1",
                    "kind": "choose",
                    "selectedAnswerId": "a1",
                    "expectedAnswerId": "a1",
                    "attempt": 1,
                    "guidedRecovery": False,
                }),
                _fact({
                    "_type": "practice_answer",
                    "questionId": "q2",
                    "kind": "choose",
                    "selectedAnswerId": "a2",
                    "expectedAnswerId": "a1",
                    "attempt": 2,
                    "guidedRecovery": True,
                }),
                _fact({
                    "_type": "saving_movement",
                    "operationId": "op1",
                    "goalId": "g1",
                    "incomeWindowId": "w1",
                    "kind": "DEPOSIT",
                    "amount": 120,
                }),
                _fact({
                    "_type": "desire_deferred",
                    "itemId": "ball",
                    "price": 50,
                    "desireDeclared": True,
                    "priorityId": "pr1",
                }),
            ],
        )

        assert registry.get_sample_value("fin_budget_amount_total", {"bucket": "needs"}) == 500
        assert registry.get_sample_value("fin_practice_answers_total", {"correct": "True"}) == 1
        assert registry.get_sample_value("fin_practice_answers_total", {"correct": "False"}) == 1
        assert registry.get_sample_value("fin_saving_amount_total", {"kind": "DEPOSIT"}) == 120
        assert registry.get_sample_value("fin_desires_deferred_total", {"declared": "True"}) == 1

    def test_rewards_and_profiles_counters(
        self,
        registry: CollectorRegistry,
        metrics: BusinessMetrics,
    ) -> None:
        metrics.observe_reward_issued(reward_type="COINS", created=True)
        metrics.observe_rewards_acknowledged(outcomes=["APPLIED", "ALREADY_OWNED"])
        metrics.observe_profile_registration(created=True)
        metrics.observe_pet_created()
        metrics.observe_snapshot_download()

        assert (
            registry.get_sample_value(
                "fin_rewards_issued_total", {"reward_type": "COINS", "created": "True"}
            )
            == 1
        )
        assert (
            registry.get_sample_value(
                "fin_reward_receipts_acknowledged_total", {"outcome": "APPLIED"}
            )
            == 1
        )
        assert (
            registry.get_sample_value("fin_profile_registrations_total", {"created": "True"}) == 1
        )
        assert registry.get_sample_value("fin_pets_created_total") == 1
        assert registry.get_sample_value("fin_snapshot_downloads_total") == 1


class TestWorldAggregation:
    def test_parse_world_sample_from_current_world(self) -> None:
        sample = parse_world_sample(world_snapshot_json())

        assert sample is not None
        assert sample.act == "act-3"
        assert sample.age == "TEEN"
        assert sample.temperament == "CURIOUS"
        assert sample.look == "BANDANA"
        assert sample.balance == 640
        assert sample.savings_balance == 300
        assert sample.unallocated == 40
        assert sample.plan_needs == 500
        assert sample.engine_day == 7
        assert sample.completed_minigames == 2
        assert sample.owned_items == 1
        assert sample.goals == ("campaign-tower-kit-v1",)

    def test_parse_world_sample_from_legacy_archive(self) -> None:
        legacy = {
            "formatVersion": 5,
            "runId": "run-2",
            "history": [],
            "historySequence": 1,
            "checksum": "c" * 64,
            "state": {
                **world_snapshot_document()["state"],
                "story": {"currentDayId": "figma-chapter-1-day-v1"},
            },
        }

        sample = parse_world_sample(json.dumps(legacy))

        assert sample is not None
        assert sample.act == "act-1"

    def test_parse_world_sample_unknown_day_and_missing_fields(self) -> None:
        sample = parse_world_sample(
            json.dumps({"worldFormatVersion": 1, "runId": "r", "state": {}})
        )

        assert sample is not None
        assert sample.act == "not_started"
        assert sample.balance == 0
        assert sample.age == "unknown"

    def test_parse_world_sample_rejects_garbage(self) -> None:
        assert parse_world_sample("not json") is None
        assert parse_world_sample(json.dumps({"state": {}})) is None
        assert parse_world_sample(json.dumps([1, 2])) is None

    def test_publish_worlds_updates_gauges_and_distributions(
        self,
        registry: CollectorRegistry,
        metrics: BusinessMetrics,
    ) -> None:
        first = parse_world_sample(world_snapshot_json())
        assert first is not None
        metrics.publish_worlds(
            samples=[first],
            worlds=1,
            runs=2,
            profiles=3,
            pets=4,
            skills=[
                [
                    {"skillId": "FIN-01", "completedEpisodes": 3, "pendingEpisodes": 1},
                    {"skillId": "FIN-02", "completedEpisodes": 1, "pendingEpisodes": 0},
                ]
            ],
        )

        assert registry.get_sample_value("fin_worlds_total") == 1
        assert registry.get_sample_value("fin_game_runs_total") == 2
        assert registry.get_sample_value("fin_profiles_total") == 3
        assert registry.get_sample_value("fin_pets_total") == 4
        assert registry.get_sample_value("fin_players_by_story_act", {"act": "act-3"}) == 1
        assert (
            registry.get_sample_value(
                "fin_goal_projects_completed", {"goal": "campaign-tower-kit-v1"}
            )
            == 1
        )
        assert registry.get_sample_value("fin_pet_balance_count") == 1
        assert registry.get_sample_value("fin_pet_balance_sum") == 640
        assert registry.get_sample_value("fin_pet_balance_bucket", {"le": "1000"}) == 1
        assert registry.get_sample_value("fin_skill_assessed_worlds_total") == 1
        assert (
            registry.get_sample_value(
                "fin_skill_episodes_avg", {"skill": "FIN-01", "counter": "completed_episodes"}
            )
            == 3
        )

        metrics.publish_worlds(samples=[], worlds=0, runs=0, profiles=3, pets=4, skills=[])

        assert registry.get_sample_value("fin_worlds_total") == 0
        assert registry.get_sample_value("fin_players_by_story_act", {"act": "act-3"}) is None
        assert registry.get_sample_value("fin_pet_balance_count") == 0

    def test_get_business_metrics_is_singleton_per_registry(
        self, registry: CollectorRegistry
    ) -> None:
        assert get_business_metrics(registry) is get_business_metrics(registry)

    def test_observers_never_raise_on_malformed_facts(self, metrics: BusinessMetrics) -> None:
        metrics.observe_analytics_batch(
            created=True,
            facts=[{"detail": None}, {"detail": {"_type": 1}}],
        )

        assert True
