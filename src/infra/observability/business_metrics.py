import json
import math
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any
from weakref import WeakKeyDictionary

from prometheus_client import CollectorRegistry, Gauge
from prometheus_client import Counter as PromCounter

from src.core.metrics import MetricsSink
from src.infra.observability.metrics import REGISTRY

_BALANCE_BUCKETS = (
    0.0,
    100.0,
    250.0,
    500.0,
    1000.0,
    2500.0,
    5000.0,
    10000.0,
    25000.0,
    50000.0,
    math.inf,
)
_COUNT_BUCKETS = (0.0, 1.0, 2.0, 3.0, 5.0, 8.0, 13.0, 21.0, 34.0, math.inf)
_DAY_BUCKETS = (0.0, 1.0, 2.0, 3.0, 5.0, 8.0, 12.0, 17.0, 25.0, 40.0, math.inf)

_SKILL_COUNTERS = (
    "completedEpisodes",
    "supportedEpisodes",
    "difficultyEpisodes",
    "neutralEpisodes",
    "pendingEpisodes",
    "incompleteEpisodes",
    "supportedWithoutGameHints",
    "assistedEpisodes",
)

_PLAN_BUCKETS = ("needs", "wants", "savings", "reserve")


def _format_le(bound: float) -> str:
    return "+Inf" if math.isinf(bound) else str(int(bound))


def _snake_case(name: str) -> str:
    return "".join(f"_{char.lower()}" if char.isupper() else char for char in name).lstrip("_")


def _as_dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_optional_str(value: object) -> str | None:
    return value if isinstance(value, str) else None


def _as_label(value: object) -> str:
    return _as_optional_str(value) or "unknown"


def _as_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _as_float(value: object) -> float:
    return _as_number(value) or 0.0


def _publish_labeled(gauge: Gauge, labelname: str, counts: Mapping[str, float]) -> None:
    gauge.clear()
    for label, count in counts.items():
        gauge.labels(**{labelname: label}).set(count)


class _Distribution:
    """Instant histogram rebuilt every aggregation cycle; safe to re-publish on each scrape."""

    def __init__(
        self,
        *,
        prefix: str,
        documentation: str,
        registry: CollectorRegistry,
        buckets: tuple[float, ...],
    ) -> None:
        self._buckets = buckets
        self._bucket_gauge = Gauge(
            name=f"{prefix}_bucket",
            documentation=f"{documentation} observation bucket (le)",
            labelnames=("le",),
            registry=registry,
        )
        self._sum_gauge = Gauge(
            name=f"{prefix}_sum",
            documentation=f"{documentation} observed sum",
            registry=registry,
        )
        self._count_gauge = Gauge(
            name=f"{prefix}_count",
            documentation=f"{documentation} observed count",
            registry=registry,
        )
        self.reset()

    def observe(self, value: float) -> None:
        self._sum += value
        self._count += 1
        for index, bound in enumerate(self._buckets):
            if value <= bound:
                self._bucket_counts[index] += 1

    def publish(self) -> None:
        self._sum_gauge.set(self._sum)
        self._count_gauge.set(self._count)
        cumulative = 0
        for bound, bucket_count in zip(self._buckets, self._bucket_counts, strict=True):
            cumulative += bucket_count
            self._bucket_gauge.labels(le=_format_le(bound)).set(cumulative)

    def reset(self) -> None:
        self._sum = 0.0
        self._count = 0
        self._bucket_counts = [0] * len(self._buckets)


class WorldSample:
    __slots__ = (
        "act",
        "age",
        "balance",
        "completed_minigames",
        "engine_day",
        "facts",
        "goals",
        "look",
        "owned_items",
        "plan_needs",
        "plan_reserve",
        "plan_savings",
        "plan_wants",
        "savings_balance",
        "temperament",
        "unallocated",
    )

    def __init__(  # noqa: PLR0913
        self,
        *,
        act: str,
        age: str,
        temperament: str,
        look: str,
        balance: float,
        savings_balance: float,
        unallocated: float,
        plan_needs: float,
        plan_wants: float,
        plan_savings: float,
        plan_reserve: float,
        engine_day: float,
        completed_minigames: float,
        owned_items: float,
        goals: tuple[str, ...],
        facts: tuple[dict[str, Any], ...],
    ) -> None:
        self.act = act
        self.age = age
        self.temperament = temperament
        self.look = look
        self.balance = balance
        self.savings_balance = savings_balance
        self.unallocated = unallocated
        self.plan_needs = plan_needs
        self.plan_wants = plan_wants
        self.plan_savings = plan_savings
        self.plan_reserve = plan_reserve
        self.engine_day = engine_day
        self.completed_minigames = completed_minigames
        self.owned_items = owned_items
        self.goals = goals
        self.facts = facts


_ACT_SUFFIX = re.compile(r"act-(\d+):day")


def _story_act(day_id: str | None) -> str:
    if day_id is None:
        return "not_started"
    if "chapter-1" in day_id:
        return "act-1"
    match = _ACT_SUFFIX.search(day_id)
    if match is not None:
        return f"act-{match.group(1)}"
    return "unknown"


def parse_world_sample(snapshot_json: str) -> WorldSample | None:
    """Extract a world sample from a stored snapshot: CURRENT_WORLD (v1) or legacy full archive."""
    try:
        document = json.loads(snapshot_json)
    except json.JSONDecodeError, TypeError, ValueError:
        return None
    if not isinstance(document, dict) or not isinstance(document.get("state"), dict):
        return None
    if "worldFormatVersion" not in document and "formatVersion" not in document:
        return None
    state = document["state"]
    story = _as_dict(state.get("story"))
    economy = _as_dict(state.get("economy"))
    pet = _as_dict(state.get("pet"))
    engine = _as_dict(state.get("engine"))
    plan = _as_dict(economy.get("plan"))
    goals = tuple(
        str(goal.get("goalId"))
        for goal in state.get("completedGoalProjects", [])
        if isinstance(goal, dict) and goal.get("goalId") is not None
    )
    history = document.get("history")
    facts = tuple(
        fact
        for entry in (history if isinstance(history, list) else [])
        if isinstance(entry, dict)
        for fact in entry.get("facts", [])
        if isinstance(fact, dict)
    )
    return WorldSample(
        act=_story_act(_as_optional_str(story.get("currentDayId"))),
        age=_as_label(pet.get("age")),
        temperament=_as_label(pet.get("temperament")),
        look=_as_label(pet.get("selectedLookId")),
        balance=_as_float(economy.get("availableBalance")),
        savings_balance=_as_float(economy.get("savingsBalance")),
        unallocated=_as_float(economy.get("unallocated")),
        plan_needs=_as_float(plan.get("needs")),
        plan_wants=_as_float(plan.get("wants")),
        plan_savings=_as_float(plan.get("savings")),
        plan_reserve=_as_float(plan.get("reserve")),
        engine_day=_as_float(engine.get("day")),
        completed_minigames=_as_float(len(state.get("completedMiniGames", []))),
        owned_items=_as_float(len(state.get("ownedItems", []))),
        goals=goals,
        facts=facts,
    )


class StoredCounts:
    """Per-cycle accumulator of stored analytics facts for the aggregation task."""

    def __init__(self) -> None:
        self.fact_types: Counter[str] = Counter()
        self.interactions: Counter[str] = Counter()
        self.purchases: Counter[str] = Counter()
        self.purchase_amounts: dict[str, float] = {}
        self.desires: Counter[str] = Counter()
        self.savings: Counter[str] = Counter()
        self.saving_amounts: dict[str, float] = {}
        self.budget_amounts: dict[str, float] = {}
        self.practice: Counter[str] = Counter()
        self.reserve: Counter[str] = Counter()
        self.earning_amount = 0.0
        self.unexpected_expense_amount = 0.0

    def add_fact(self, fact: dict[str, Any]) -> None:
        detail = fact.get("detail")
        if not isinstance(detail, dict):
            return
        detail_type = detail.get("_type")
        if not isinstance(detail_type, str):
            return
        self.fact_types[detail_type] += 1
        self._add_detail(detail_type, detail)

    def _add_detail(self, detail_type: str, detail: dict[str, Any]) -> None:
        if detail_type == "interaction":
            self._add_interaction(detail)
        elif detail_type in ("optional_purchase", "desire_deferred", "saving_movement"):
            self._add_money_choice(detail_type, detail)
        elif detail_type == "budget_confirmed":
            for bucket in _PLAN_BUCKETS:
                self._amount(self.budget_amounts, bucket, detail.get(bucket))
        elif detail_type == "reserve_decision":
            self.reserve[str(bool(detail.get("usedForUnexpectedExpense")))] += 1
        elif detail_type == "unexpected_expense":
            self.unexpected_expense_amount += _as_float(detail.get("amount"))
        elif detail_type == "earning_completed":
            self.earning_amount += _as_float(detail.get("actualReward"))
        elif detail_type == "practice_answer":
            correct = detail.get("selectedAnswerId") == detail.get("expectedAnswerId")
            self.practice[str(correct)] += 1

    def _add_interaction(self, detail: dict[str, Any]) -> None:
        name = detail.get("name")
        if isinstance(name, str):
            self.interactions[name] += 1

    def _add_money_choice(self, detail_type: str, detail: dict[str, Any]) -> None:
        if detail_type == "optional_purchase":
            purchased = str(bool(detail.get("purchased")))
            self.purchases[purchased] += 1
            self._amount(self.purchase_amounts, purchased, detail.get("price"))
        elif detail_type == "desire_deferred":
            self.desires[str(bool(detail.get("desireDeclared")))] += 1
        else:
            kind = str(detail.get("kind", "unknown"))
            self.savings[kind] += 1
            self._amount(self.saving_amounts, kind, detail.get("amount"))

    @staticmethod
    def _amount(target: dict[str, float], label: str, value: object) -> None:
        amount = _as_number(value)
        if amount is not None:
            target[label] = target.get(label, 0.0) + amount


class BusinessMetrics(MetricsSink):
    """Prometheus business metrics shared by use-case counters and the world aggregation task."""

    def __init__(self, registry: CollectorRegistry | None = None) -> None:
        self.registry = registry if registry is not None else REGISTRY
        self._build_upload_counters()
        self._build_fact_counters()
        self._build_profile_counters()
        self._build_world_gauges()
        self._build_world_distributions()
        self._build_stored_gauges()

    def _counter(
        self, name: str, documentation: str, labelnames: Sequence[str] = ()
    ) -> PromCounter:
        return PromCounter(
            name=name,
            documentation=documentation,
            labelnames=tuple(labelnames),
            registry=self.registry,
        )

    def _gauge(self, name: str, documentation: str, labelnames: Sequence[str] = ()) -> Gauge:
        return Gauge(
            name=name,
            documentation=documentation,
            labelnames=tuple(labelnames),
            registry=self.registry,
        )

    def _build_upload_counters(self) -> None:
        self._snapshot_uploads = self._counter(
            "fin_snapshot_uploads_total",
            "Accepted snapshot uploads",
            ("created",),
        )
        self._snapshot_downloads = self._counter(
            "fin_snapshot_downloads_total", "Served snapshot downloads"
        )
        self._analytics_batches = self._counter(
            "fin_analytics_batches_total",
            "Accepted analytics batches",
            ("created",),
        )
        self._analytics_facts = self._counter(
            "fin_analytics_facts_total",
            "Accepted analytics facts by detail type",
            ("detail_type", "actor", "mode"),
        )
        self._profiles_registered = self._counter(
            "fin_profile_registrations_total",
            "Registered device profiles",
            ("created",),
        )
        self._pets_created = self._counter("fin_pets_created_total", "Created legacy pets")
        self._rewards_issued = self._counter(
            "fin_rewards_issued_total",
            "Issued parent rewards by type",
            ("reward_type", "created"),
        )
        self._rewards_acknowledged = self._counter(
            "fin_reward_receipts_acknowledged_total",
            "Acknowledged reward receipts by outcome",
            ("outcome",),
        )

    def _build_fact_counters(self) -> None:
        self._interactions = self._counter(
            "fin_interactions_total",
            "Interaction facts by engine command name",
            ("name",),
        )
        self._optional_purchases = self._counter(
            "fin_optional_purchases_total",
            "Optional purchase facts by outcome",
            ("purchased",),
        )
        self._purchase_amounts = self._counter(
            "fin_purchase_amount_total",
            "Optional purchase price sum by outcome",
            ("purchased",),
        )
        self._desires_deferred = self._counter(
            "fin_desires_deferred_total",
            "Deferred desire facts by declaration",
            ("declared",),
        )
        self._saving_movements = self._counter(
            "fin_saving_movements_total",
            "Saving movement facts by operation kind",
            ("kind",),
        )
        self._saving_amounts = self._counter(
            "fin_saving_amount_total",
            "Saving movement amount sum by operation kind",
            ("kind",),
        )
        self._saving_cycles = self._counter("fin_saving_cycles_total", "Closed saving cycles")
        self._saving_intentions = self._counter(
            "fin_saving_intentions_total",
            "Resolved saving intentions by skip outcome",
            ("skipped",),
        )
        self._saving_promised = self._counter(
            "fin_saving_promised_amount_total",
            "Promised saving amount sum",
        )
        self._saving_deposited = self._counter(
            "fin_saving_deposited_amount_total",
            "Deposited saving amount sum",
        )
        self._budget_confirmed = self._counter(
            "fin_budget_confirmations_total", "Confirmed budget plans"
        )
        self._budget_amounts = self._counter(
            "fin_budget_amount_total",
            "Confirmed budget allocation amount sum by plan bucket",
            ("bucket",),
        )
        self._reserve_decisions = self._counter(
            "fin_reserve_decisions_total",
            "Reserve decisions by unexpected expense usage",
            ("used",),
        )
        self._unexpected_expenses = self._counter(
            "fin_unexpected_expenses_total",
            "Unexpected expense facts",
        )
        self._unexpected_expense_amounts = self._counter(
            "fin_unexpected_expense_amount_total",
            "Unexpected expense amount sum",
        )
        self._earning_plans = self._counter("fin_earning_plans_total", "Started earning plans")
        self._earning_completed = self._counter(
            "fin_earning_completed_total", "Completed earning plans"
        )
        self._earning_amounts = self._counter(
            "fin_earning_amount_total",
            "Completed earning reward sum",
        )
        self._practice_answers = self._counter(
            "fin_practice_answers_total",
            "Practice answers by correctness",
            ("correct",),
        )
        self._question_answers = self._counter(
            "fin_question_answers_total",
            "Question answers by reveal outcome",
            ("revealed",),
        )
        self._income_windows = self._counter(
            "fin_income_windows_total",
            "Income window facts by closed state",
            ("closed",),
        )
        self._priorities_applied = self._counter(
            "fin_priorities_applied_total", "Applied priority facts"
        )
        self._priority_conflicts = self._counter(
            "fin_priority_conflicts_total", "Priority conflict facts"
        )
        self._recovery_actions = self._counter(
            "fin_recovery_actions_total",
            "Recovery actions by completion",
            ("completed",),
        )
        self._resource_choices = self._counter(
            "fin_resource_choices_total", "Resource choice facts"
        )
        self._comparables = self._counter(
            "fin_comparables_total",
            "Comparable application facts by priority preservation",
            ("preserved",),
        )
        self._time_machine = self._counter(
            "fin_time_machine_total",
            "Time machine lifecycle facts by event",
            ("event",),
        )

    def _build_profile_counters(self) -> None:
        self._aggregation_errors = self._counter(
            "fin_aggregation_errors_total",
            "World aggregation cycle failures",
        )
        self._aggregation_parse_errors = self._counter(
            "fin_aggregation_parse_errors_total",
            "Unparseable stored snapshots",
        )
        self._aggregation_last_success = self._gauge(
            "fin_aggregation_last_success_unixtime",
            "Unix time of the last successful world aggregation",
        )
        self._aggregation_duration = self._gauge(
            "fin_aggregation_duration_seconds",
            "Duration of the last world aggregation cycle",
        )

    def _build_world_gauges(self) -> None:
        self._worlds = self._gauge("fin_worlds_total", "Stored cloud worlds")
        self._game_runs = self._gauge(
            "fin_game_runs_total", "Distinct game runs across stored worlds"
        )
        self._profiles_total = self._gauge("fin_profiles_total", "Registered profiles")
        self._pets_total = self._gauge("fin_pets_total", "Stored legacy pets")
        self._players_by_act = self._gauge(
            "fin_players_by_story_act",
            "Worlds by story act derived from the current story day",
            ("act",),
        )
        self._players_by_age = self._gauge("fin_players_by_pet_age", "Worlds by pet age", ("age",))
        self._players_by_temperament = self._gauge(
            "fin_players_by_pet_temperament",
            "Worlds by pet temperament",
            ("temperament",),
        )
        self._players_by_look = self._gauge(
            "fin_players_by_pet_look",
            "Worlds by selected pet look",
            ("look",),
        )
        self._goal_projects = self._gauge(
            "fin_goal_projects_completed",
            "Completed goal projects by goal id",
            ("goal",),
        )
        self._skill_assessed_worlds = self._gauge(
            "fin_skill_assessed_worlds_total",
            "Worlds with stored skill projections",
        )
        self._skill_episodes = self._gauge(
            "fin_skill_episodes_avg",
            "Average skill episode counters across assessed worlds",
            ("skill", "counter"),
        )

    def _build_world_distributions(self) -> None:
        self._balance = _Distribution(
            prefix="fin_pet_balance",
            documentation="Pet available balance",
            registry=self.registry,
            buckets=_BALANCE_BUCKETS,
        )
        self._savings_balance = _Distribution(
            prefix="fin_pet_savings_balance",
            documentation="Pet savings balance",
            registry=self.registry,
            buckets=_BALANCE_BUCKETS,
        )
        self._unallocated = _Distribution(
            prefix="fin_pet_unallocated",
            documentation="Pet unallocated balance",
            registry=self.registry,
            buckets=_BALANCE_BUCKETS,
        )
        self._plan_distributions = {
            bucket: _Distribution(
                prefix=f"fin_plan_{bucket}",
                documentation=f"Planned {bucket} amount",
                registry=self.registry,
                buckets=_BALANCE_BUCKETS,
            )
            for bucket in _PLAN_BUCKETS
        }
        self._engine_day = _Distribution(
            prefix="fin_engine_day",
            documentation="Current engine calendar day",
            registry=self.registry,
            buckets=_DAY_BUCKETS,
        )
        self._completed_minigames = _Distribution(
            prefix="fin_completed_minigames",
            documentation="Completed standalone minigames per world",
            registry=self.registry,
            buckets=_COUNT_BUCKETS,
        )
        self._owned_items = _Distribution(
            prefix="fin_owned_items",
            documentation="Owned items per world",
            registry=self.registry,
            buckets=_COUNT_BUCKETS,
        )

    def observe_snapshot_upload(self, *, created: bool) -> None:
        self._snapshot_uploads.labels(created=str(created)).inc()

    def observe_snapshot_download(self) -> None:
        self._snapshot_downloads.inc()

    def observe_analytics_batch(self, *, created: bool, facts: list[dict[str, Any]]) -> None:
        self._analytics_batches.labels(created=str(created)).inc()
        if not created:
            return
        for fact in facts:
            self._observe_fact(fact)

    def observe_profile_registration(self, *, created: bool) -> None:
        self._profiles_registered.labels(created=str(created)).inc()

    def observe_pet_created(self) -> None:
        self._pets_created.inc()

    def observe_reward_issued(self, *, reward_type: str, created: bool) -> None:
        self._rewards_issued.labels(reward_type=reward_type, created=str(created)).inc()

    def observe_rewards_acknowledged(self, *, outcomes: Sequence[str]) -> None:
        for outcome in outcomes:
            self._rewards_acknowledged.labels(outcome=outcome).inc()

    def observe_aggregation_error(self) -> None:
        self._aggregation_errors.inc()

    def observe_aggregation_parse_error(self) -> None:
        self._aggregation_parse_errors.inc()

    def observe_aggregation_success(self, *, duration_seconds: float) -> None:
        self._aggregation_duration.set(duration_seconds)
        self._aggregation_last_success.set_to_current_time()

    def publish_worlds(
        self,
        *,
        samples: Sequence[WorldSample],
        worlds: int,
        runs: int,
        profiles: int,
        pets: int,
        skills: Sequence[Sequence[dict[str, Any]]],
    ) -> None:
        self._worlds.set(worlds)
        self._game_runs.set(runs)
        self._profiles_total.set(profiles)
        self._pets_total.set(pets)
        act_counts: Counter[str] = Counter()
        age_counts: Counter[str] = Counter()
        temperament_counts: Counter[str] = Counter()
        look_counts: Counter[str] = Counter()
        goal_counts: Counter[str] = Counter()
        for sample in samples:
            act_counts[sample.act] += 1
            age_counts[sample.age] += 1
            temperament_counts[sample.temperament] += 1
            look_counts[sample.look] += 1
            goal_counts.update(sample.goals)
            self._observe_sample(sample)
        _publish_labeled(self._players_by_act, "act", act_counts)
        _publish_labeled(self._players_by_age, "age", age_counts)
        _publish_labeled(self._players_by_temperament, "temperament", temperament_counts)
        _publish_labeled(self._players_by_look, "look", look_counts)
        _publish_labeled(self._goal_projects, "goal", goal_counts)
        for distribution in self._distributions():
            distribution.publish()
            distribution.reset()
        self._publish_skills(skills)

    def _distributions(self) -> tuple[_Distribution, ...]:
        return (
            self._balance,
            self._savings_balance,
            self._unallocated,
            *self._plan_distributions.values(),
            self._engine_day,
            self._completed_minigames,
            self._owned_items,
        )

    def _build_stored_gauges(self) -> None:
        self._facts_stored = self._gauge(
            "fin_facts_stored",
            "Stored analytics facts by detail type across all worlds and projections",
            ("detail_type",),
        )
        self._interactions_stored = self._gauge(
            "fin_interactions_stored",
            "Stored interaction facts by engine command name",
            ("name",),
        )
        self._purchases_stored = self._gauge(
            "fin_purchases_stored",
            "Stored optional purchases by outcome",
            ("purchased",),
        )
        self._purchase_amounts_stored = self._gauge(
            "fin_purchase_amount_stored",
            "Stored optional purchase price sum by outcome",
            ("purchased",),
        )
        self._desires_stored = self._gauge(
            "fin_desires_stored",
            "Stored deferred desires by declaration",
            ("declared",),
        )
        self._savings_stored = self._gauge(
            "fin_saving_movements_stored",
            "Stored saving movements by operation kind",
            ("kind",),
        )
        self._saving_amounts_stored = self._gauge(
            "fin_saving_amount_stored",
            "Stored saving movement amount sum by operation kind",
            ("kind",),
        )
        self._budget_amounts_stored = self._gauge(
            "fin_budget_amount_stored",
            "Stored confirmed budget allocation sum by plan bucket",
            ("bucket",),
        )
        self._practice_stored = self._gauge(
            "fin_practice_stored",
            "Stored practice answers by correctness",
            ("correct",),
        )
        self._reserve_stored = self._gauge(
            "fin_reserve_stored",
            "Stored reserve decisions by unexpected expense usage",
            ("used",),
        )
        self._earning_amount_stored = self._gauge(
            "fin_earning_amount_stored",
            "Stored completed earning reward sum",
        )
        self._unexpected_expense_amount_stored = self._gauge(
            "fin_unexpected_expense_amount_stored",
            "Stored unexpected expense amount sum",
        )

    def publish_stored(self, counts: StoredCounts) -> None:
        """Republish accumulated stored-fact aggregates; values are absolute per cycle."""
        _publish_labeled(self._facts_stored, "detail_type", counts.fact_types)
        _publish_labeled(self._interactions_stored, "name", counts.interactions)
        _publish_labeled(self._purchases_stored, "purchased", counts.purchases)
        _publish_labeled(self._purchase_amounts_stored, "purchased", counts.purchase_amounts)
        _publish_labeled(self._desires_stored, "declared", counts.desires)
        _publish_labeled(self._savings_stored, "kind", counts.savings)
        _publish_labeled(self._saving_amounts_stored, "kind", counts.saving_amounts)
        _publish_labeled(self._budget_amounts_stored, "bucket", counts.budget_amounts)
        _publish_labeled(self._practice_stored, "correct", counts.practice)
        _publish_labeled(self._reserve_stored, "used", counts.reserve)
        self._earning_amount_stored.set(counts.earning_amount)
        self._unexpected_expense_amount_stored.set(counts.unexpected_expense_amount)

    def _observe_sample(self, sample: WorldSample) -> None:
        self._balance.observe(sample.balance)
        self._savings_balance.observe(sample.savings_balance)
        self._unallocated.observe(sample.unallocated)
        self._plan_distributions["needs"].observe(sample.plan_needs)
        self._plan_distributions["wants"].observe(sample.plan_wants)
        self._plan_distributions["savings"].observe(sample.plan_savings)
        self._plan_distributions["reserve"].observe(sample.plan_reserve)
        self._engine_day.observe(sample.engine_day)
        self._completed_minigames.observe(sample.completed_minigames)
        self._owned_items.observe(sample.owned_items)

    def _publish_skills(self, skills: Sequence[Sequence[dict[str, Any]]]) -> None:
        self._skill_assessed_worlds.set(len(skills))
        if not skills:
            return
        totals: dict[tuple[str, str], float] = {}
        for world_skills in skills:
            for skill in world_skills:
                skill_id = str(skill.get("skillId", "unknown"))
                for counter in _SKILL_COUNTERS:
                    value = skill.get(counter)
                    if type(value) is int:
                        key = (skill_id, _snake_case(counter))
                        totals[key] = totals.get(key, 0.0) + value
        for (skill_id, counter), total in totals.items():
            self._skill_episodes.labels(skill=skill_id, counter=counter).set(total / len(skills))

    def _observe_fact(self, fact: dict[str, Any]) -> None:
        detail = fact.get("detail")
        if not isinstance(detail, dict):
            return
        detail_type = detail.get("_type")
        if not isinstance(detail_type, str):
            return
        self._analytics_facts.labels(
            detail_type=detail_type,
            actor=str(fact.get("actor", "unknown")),
            mode=str(fact.get("mode", "unknown")),
        ).inc()
        handler = self._detail_handlers.get(detail_type)
        if handler is not None:
            handler(self, detail)

    def _observe_interaction(self, detail: dict[str, Any]) -> None:
        name = detail.get("name")
        if isinstance(name, str):
            self._interactions.labels(name=name).inc()

    def _observe_optional_purchase(self, detail: dict[str, Any]) -> None:
        purchased = str(bool(detail.get("purchased")))
        self._optional_purchases.labels(purchased=purchased).inc()
        amount = _as_number(detail.get("price"))
        if amount is not None:
            self._purchase_amounts.labels(purchased=purchased).inc(amount)

    def _observe_desire_deferred(self, detail: dict[str, Any]) -> None:
        self._desires_deferred.labels(declared=str(bool(detail.get("desireDeclared")))).inc()

    def _observe_saving_movement(self, detail: dict[str, Any]) -> None:
        kind = str(detail.get("kind", "unknown"))
        self._saving_movements.labels(kind=kind).inc()
        amount = _as_number(detail.get("amount"))
        if amount is not None:
            self._saving_amounts.labels(kind=kind).inc(amount)

    def _observe_saving_cycle_closed(self, _detail: dict[str, Any]) -> None:
        self._saving_cycles.inc()

    def _observe_saving_intention(self, detail: dict[str, Any]) -> None:
        self._saving_intentions.labels(skipped=str(bool(detail.get("deliberatelySkipped")))).inc()
        promised = _as_number(detail.get("promisedAmount"))
        deposited = _as_number(detail.get("depositedAmount"))
        if promised is not None:
            self._saving_promised.inc(promised)
        if deposited is not None:
            self._saving_deposited.inc(deposited)

    def _observe_budget_confirmed(self, detail: dict[str, Any]) -> None:
        self._budget_confirmed.inc()
        for bucket in _PLAN_BUCKETS:
            amount = _as_number(detail.get(bucket))
            if amount is not None:
                self._budget_amounts.labels(bucket=bucket).inc(amount)

    def _observe_reserve_decision(self, detail: dict[str, Any]) -> None:
        self._reserve_decisions.labels(used=str(bool(detail.get("usedForUnexpectedExpense")))).inc()

    def _observe_unexpected_expense(self, detail: dict[str, Any]) -> None:
        self._unexpected_expenses.inc()
        amount = _as_number(detail.get("amount"))
        if amount is not None:
            self._unexpected_expense_amounts.inc(amount)

    def _observe_earning_plan(self, _detail: dict[str, Any]) -> None:
        self._earning_plans.inc()

    def _observe_earning_completed(self, detail: dict[str, Any]) -> None:
        self._earning_completed.inc()
        amount = _as_number(detail.get("actualReward"))
        if amount is not None:
            self._earning_amounts.inc(amount)

    def _observe_practice_answer(self, detail: dict[str, Any]) -> None:
        correct = detail.get("selectedAnswerId") == detail.get("expectedAnswerId")
        self._practice_answers.labels(correct=str(correct)).inc()

    def _observe_question_answer(self, detail: dict[str, Any]) -> None:
        self._question_answers.labels(revealed=str(bool(detail.get("answerWasRevealed")))).inc()

    def _observe_income_window(self, detail: dict[str, Any]) -> None:
        self._income_windows.labels(closed=str(bool(detail.get("closed")))).inc()

    def _observe_priority_applied(self, _detail: dict[str, Any]) -> None:
        self._priorities_applied.inc()

    def _observe_priority_conflict(self, _detail: dict[str, Any]) -> None:
        self._priority_conflicts.inc()

    def _observe_recovery_action(self, detail: dict[str, Any]) -> None:
        self._recovery_actions.labels(completed=str(bool(detail.get("completed")))).inc()

    def _observe_resource_choice(self, _detail: dict[str, Any]) -> None:
        self._resource_choices.inc()

    def _observe_comparable(self, detail: dict[str, Any]) -> None:
        self._comparables.labels(preserved=str(bool(detail.get("priorityPreserved")))).inc()

    def _observe_time_machine(self, detail: dict[str, Any]) -> None:
        event = detail.get("event")
        if isinstance(event, str):
            self._time_machine.labels(event=event).inc()

    _detail_handlers: dict[str, Any] = {
        "interaction": _observe_interaction,
        "optional_purchase": _observe_optional_purchase,
        "desire_deferred": _observe_desire_deferred,
        "saving_movement": _observe_saving_movement,
        "saving_cycle_closed": _observe_saving_cycle_closed,
        "saving_intention_resolved": _observe_saving_intention,
        "budget_confirmed": _observe_budget_confirmed,
        "reserve_decision": _observe_reserve_decision,
        "unexpected_expense": _observe_unexpected_expense,
        "earning_plan": _observe_earning_plan,
        "earning_completed": _observe_earning_completed,
        "practice_answer": _observe_practice_answer,
        "question_answer": _observe_question_answer,
        "income_window": _observe_income_window,
        "priority_applied": _observe_priority_applied,
        "priority_conflict": _observe_priority_conflict,
        "recovery_action": _observe_recovery_action,
        "resource_choice": _observe_resource_choice,
        "comparable_application": _observe_comparable,
        "time_machine_lifecycle": _observe_time_machine,
    }


_business_metrics_by_registry: WeakKeyDictionary[CollectorRegistry, BusinessMetrics] = (
    WeakKeyDictionary()
)


def get_business_metrics(registry: CollectorRegistry | None = None) -> BusinessMetrics:
    """Return the per-registry singleton so repeated instantiation never duplicates collectors."""
    target = registry if registry is not None else REGISTRY
    existing = _business_metrics_by_registry.get(target)
    if existing is None:
        existing = BusinessMetrics(registry=target)
        _business_metrics_by_registry[target] = existing
    return existing
