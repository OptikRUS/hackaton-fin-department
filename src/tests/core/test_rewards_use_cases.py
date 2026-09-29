from unittest.mock import AsyncMock
from uuid import UUID

import pytest

from src.core.rewards.exceptions import (
    GameRunConflictError,
    GameRunNotRegisteredError,
    InvalidRewardCursorError,
    InvalidRewardReceiptError,
    RewardIdempotencyConflictError,
    RewardReceiptConflictError,
    UnknownAccessoryError,
)
from src.core.rewards.schemas import (
    AccessoryReward,
    AckRewardsParams,
    CoinReward,
    RewardReceipt,
)
from src.core.rewards.storages import RewardStorage
from src.core.rewards.use_cases import AckRewardsUseCase, IssueRewardUseCase, ListRewardsUseCase
from src.infra.api.rewards.schemas import CreateParentRewardRequest, ParentRewardDto
from src.tests.fixtures import FactoryFixture


class TestIssueRewardUseCase(FactoryFixture):
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.storage = AsyncMock(spec=RewardStorage)
        self.storage.get_registered_run_for_update.return_value = "run-1"
        self.storage.get_issue_by_key.return_value = None
        self.storage.last_sequence.return_value = 0
        self.storage.insert_reward.side_effect = lambda **kwargs: kwargs["reward"]
        self.use_case = IssueRewardUseCase(storage=self.storage)

    async def test_issue_creates_next_immutable_grant(self) -> None:
        self.storage.last_sequence.return_value = 4
        self.storage.insert_reward.side_effect = lambda **kwargs: kwargs["reward"]
        result = await self.use_case.execute(
            profile_id=UUID(int=1),
            game_run_id="run-1",
            reward=CoinReward(amount=20),
            idempotency_key="request-1",
        )
        assert result.created is True
        assert result.reward.sequence == 5
        assert result.reward.profile_id == UUID(int=1)
        self.storage.insert_reward.assert_awaited_once()

    @pytest.mark.parametrize(
        "item_id",
        [
            "starter-bandana-v1",
            "starter-backpack-v1",
            "cosmetic-explorer-hat-v2",
            "figma-2164-2-explorer-cap-v1",
            "cosmetic-pilot-goggles-v1",
            "cosmetic-route-patch-v1",
            "cosmetic-compass-v1",
            "cosmetic-binoculars-v1",
            "cosmetic-cap-moscow-blue-v1",
            "cosmetic-cap-moscow-emerald-v1",
            "cosmetic-cap-moscow-burgundy-v1",
            "cosmetic-cap-lct2026-blue-v1",
            "cosmetic-cap-lct2026-emerald-v1",
            "cosmetic-cap-lct2026-burgundy-v1",
        ],
    )
    async def test_issue_accepts_known_pet_cosmetic_ids(self, item_id: str) -> None:
        self.storage.insert_reward.side_effect = lambda **kwargs: kwargs["reward"]
        result = await self.use_case.execute(
            profile_id=UUID(int=1),
            game_run_id="run-1",
            reward=AccessoryReward(item_id=item_id),
            idempotency_key=f"request-{item_id}",
        )
        assert result.reward.reward == AccessoryReward(item_id=item_id)

    @pytest.mark.parametrize(
        "item_id",
        [
            "cosmetic-cap-moscow-blue-v1",
            "cosmetic-cap-moscow-emerald-v1",
            "cosmetic-cap-moscow-burgundy-v1",
            "cosmetic-cap-lct2026-blue-v1",
            "cosmetic-cap-lct2026-emerald-v1",
            "cosmetic-cap-lct2026-burgundy-v1",
        ],
    )
    async def test_cap_contract_roundtrip_and_idempotent_replay(self, item_id: str) -> None:
        body = {
            "deviceId": "9f1c2d3e4a5b6078",
            "gameRunId": "run-1",
            "schemaVersion": 1,
            "reward": {"type": "ACCESSORY", "itemId": item_id},
        }
        request = CreateParentRewardRequest.model_validate(body)
        result = await self.use_case.execute(
            profile_id=UUID(int=1),
            game_run_id=request.game_run_id,
            reward=request.to_domain(),
            idempotency_key="cap-request",
        )
        wire = ParentRewardDto.from_domain(result.reward, device_id=request.device_id).model_dump(
            mode="json",
            by_alias=True,
        )
        assert wire["reward"] == body["reward"]
        assert wire["profileId"] == body["deviceId"]
        assert wire["gameRunId"] == body["gameRunId"]
        assert wire["sequence"] == 1
        self.storage.get_issue_by_key.return_value = result.reward
        replay = await self.use_case.execute(
            profile_id=UUID(int=1),
            game_run_id=request.game_run_id,
            reward=request.to_domain(),
            idempotency_key="cap-request",
        )
        assert replay.reward == result.reward
        assert replay.created is False
        self.storage.insert_reward.assert_awaited_once()
        other = (
            "cosmetic-cap-moscow-blue-v1"
            if "lct2026" in item_id
            else "cosmetic-cap-lct2026-blue-v1"
        )
        with pytest.raises(RewardIdempotencyConflictError):
            await self.use_case.execute(
                profile_id=UUID(int=1),
                game_run_id="run-1",
                reward=AccessoryReward(item_id=other),
                idempotency_key="cap-request",
            )

    async def test_issue_rejects_unknown_cap_without_creating_grant(self) -> None:
        with pytest.raises(UnknownAccessoryError):
            await self.use_case.execute(
                profile_id=UUID(int=1),
                game_run_id="run-1",
                reward=AccessoryReward(item_id="cosmetic-cap-moscow-unknown-v1"),
                idempotency_key="request-unknown-cap",
            )
        self.storage.insert_reward.assert_not_awaited()

    async def test_issue_replays_same_key_without_new_grant(self) -> None:
        self.storage.get_issue_by_key.return_value = self.factory.rewards.grant(
            profile_id=UUID(int=1)
        )
        result = await self.use_case.execute(
            profile_id=UUID(int=1),
            game_run_id="run-1",
            reward=CoinReward(amount=20),
            idempotency_key="request-1",
        )
        assert result.reward == self.factory.rewards.grant(profile_id=UUID(int=1))
        assert result.created is False
        self.storage.insert_reward.assert_not_awaited()

    async def test_issue_replays_existing_accessory_after_catalog_changes(self) -> None:
        accessory = AccessoryReward(item_id="retired-accessory")
        self.storage.get_issue_by_key.return_value = self.factory.rewards.grant(
            profile_id=UUID(int=1), reward=accessory
        )
        result = await self.use_case.execute(
            profile_id=UUID(int=1),
            game_run_id="run-1",
            reward=accessory,
            idempotency_key="request-1",
        )
        assert result.created is False

    async def test_issue_rejects_changed_payload_on_same_key(self) -> None:
        self.storage.get_issue_by_key.return_value = self.factory.rewards.grant(
            profile_id=UUID(int=1), reward=CoinReward(amount=10)
        )
        with pytest.raises(RewardIdempotencyConflictError):
            await self.use_case.execute(
                profile_id=UUID(int=1),
                game_run_id="run-1",
                reward=CoinReward(amount=20),
                idempotency_key="request-1",
            )
        self.storage.insert_reward.assert_not_awaited()

    @pytest.mark.parametrize(
        ("registered", "error"),
        [(None, GameRunNotRegisteredError), ("another-run", GameRunConflictError)],
    )
    async def test_issue_requires_registered_matching_run(
        self,
        registered: str | None,
        error: type[Exception],
    ) -> None:
        self.storage.get_registered_run_for_update.return_value = registered
        with pytest.raises(error):
            await self.use_case.execute(
                profile_id=UUID(int=1),
                game_run_id="run-1",
                reward=CoinReward(amount=20),
                idempotency_key="request-1",
            )


class TestListRewardsUseCase(FactoryFixture):
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.storage = AsyncMock(spec=RewardStorage)
        self.storage.get_registered_run.return_value = "run-1"
        self.storage.last_sequence.return_value = 0
        self.storage.list_after.return_value = []
        self.use_case = ListRewardsUseCase(storage=self.storage)

    async def test_list_returns_contiguous_page_and_never_filters_ack(self) -> None:
        self.storage.last_sequence.return_value = 3
        self.storage.list_after.return_value = [
            self.factory.rewards.grant(profile_id=UUID(int=1), sequence=1),
            self.factory.rewards.grant(profile_id=UUID(int=1), sequence=2),
        ]
        page = await self.use_case.execute(
            profile_id=UUID(int=1),
            game_run_id="run-1",
            after_sequence=0,
            limit=2,
        )
        assert [item.sequence for item in page.rewards] == [1, 2]
        assert page.next_after_sequence == 2
        assert page.has_more is True

    async def test_list_rejects_cursor_past_end(self) -> None:
        self.storage.last_sequence.return_value = 2
        with pytest.raises(InvalidRewardCursorError):
            await self.use_case.execute(
                profile_id=UUID(int=1),
                game_run_id="run-1",
                after_sequence=3,
            )


class TestAckRewardsUseCase(FactoryFixture):
    @pytest.fixture(autouse=True)
    def setup(self) -> None:
        self.storage = AsyncMock(spec=RewardStorage)
        self.storage.get_registered_run_for_update.return_value = "run-1"
        self.storage.get_ack_by_key.return_value = None
        self.storage.get_receipts_by_application_ids.return_value = {}
        self.storage.get_rewards_by_ids.return_value = {
            self.factory.rewards.grant(
                profile_id=UUID(int=1)
            ).reward_id: self.factory.rewards.grant(profile_id=UUID(int=1))
        }
        self.storage.insert_receipts.return_value = {"7e0f74aa-9354-47f4-a2a6-3857bf3b7571"}
        self.use_case = AckRewardsUseCase(storage=self.storage)

    async def test_ack_accepts_committed_receipt(self) -> None:
        result = await self.use_case.execute(
            profile_id=UUID(int=1),
            idempotency_key="ack-1",
            params=AckRewardsParams(
                game_run_id="run-1", receipts=(self.factory.rewards.receipt(),)
            ),
        )
        assert result.accepted_application_ids == ("7e0f74aa-9354-47f4-a2a6-3857bf3b7571",)
        self.storage.insert_receipts.assert_awaited_once()
        self.storage.insert_ack.assert_awaited_once()

    async def test_ack_allows_second_application_for_same_grant(self) -> None:
        second = RewardReceipt(
            reward_id=self.factory.rewards.grant(profile_id=UUID(int=1)).reward_id,
            application_id="6a386b6f-a67a-4c31-9a12-3c660271dd32",
            history_entry_id="another",
            history_sequence=4,
            outcome="APPLIED",
        )
        result = await self.use_case.execute(
            profile_id=UUID(int=1),
            idempotency_key="ack-2",
            params=AckRewardsParams(game_run_id="run-1", receipts=(second,)),
        )
        assert result.accepted_application_ids == (second.application_id,)

    async def test_ack_rejects_changed_application_payload(self) -> None:
        self.storage.get_receipts_by_application_ids.return_value = {
            "7e0f74aa-9354-47f4-a2a6-3857bf3b7571": (
                RewardReceipt(
                    reward_id=self.factory.rewards.grant(profile_id=UUID(int=1)).reward_id,
                    application_id="7e0f74aa-9354-47f4-a2a6-3857bf3b7571",
                    history_entry_id="different",
                    history_sequence=18,
                    outcome="APPLIED",
                ),
                UUID(int=1),
                "run-1",
            ),
        }
        with pytest.raises(RewardReceiptConflictError):
            await self.use_case.execute(
                profile_id=UUID(int=1),
                idempotency_key="ack-1",
                params=AckRewardsParams(
                    game_run_id="run-1", receipts=(self.factory.rewards.receipt(),)
                ),
            )

    async def test_ack_rejects_application_id_reused_across_profiles(self) -> None:
        self.storage.get_receipts_by_application_ids.return_value = {
            "7e0f74aa-9354-47f4-a2a6-3857bf3b7571": (
                self.factory.rewards.receipt(),
                UUID(int=2),
                "run-1",
            ),
        }
        with pytest.raises(RewardReceiptConflictError):
            await self.use_case.execute(
                profile_id=UUID(int=1),
                idempotency_key="ack-1",
                params=AckRewardsParams(
                    game_run_id="run-1", receipts=(self.factory.rewards.receipt(),)
                ),
            )

    async def test_ack_reuses_identical_application_in_new_batch(self) -> None:
        self.storage.get_receipts_by_application_ids.return_value = {
            "7e0f74aa-9354-47f4-a2a6-3857bf3b7571": (
                self.factory.rewards.receipt(),
                UUID(int=1),
                "run-1",
            ),
        }
        result = await self.use_case.execute(
            profile_id=UUID(int=1),
            idempotency_key="ack-2",
            params=AckRewardsParams(
                game_run_id="run-1", receipts=(self.factory.rewards.receipt(),)
            ),
        )
        assert result.accepted_application_ids == ("7e0f74aa-9354-47f4-a2a6-3857bf3b7571",)
        self.storage.insert_receipts.assert_not_awaited()

    async def test_ack_rejects_wrong_run_grant(self) -> None:
        self.storage.get_rewards_by_ids.return_value = {}
        with pytest.raises(InvalidRewardReceiptError):
            await self.use_case.execute(
                profile_id=UUID(int=1),
                idempotency_key="ack-1",
                params=AckRewardsParams(
                    game_run_id="run-1", receipts=(self.factory.rewards.receipt(),)
                ),
            )

    async def test_ack_rejects_concurrent_application_id_collision(self) -> None:
        self.storage.insert_receipts.return_value = set()
        self.storage.get_receipts_by_application_ids.side_effect = [
            {},
            {
                "7e0f74aa-9354-47f4-a2a6-3857bf3b7571": (
                    self.factory.rewards.receipt(),
                    UUID(int=2),
                    "run-1",
                )
            },
        ]
        with pytest.raises(RewardReceiptConflictError):
            await self.use_case.execute(
                profile_id=UUID(int=1),
                idempotency_key="ack-1",
                params=AckRewardsParams(
                    game_run_id="run-1", receipts=(self.factory.rewards.receipt(),)
                ),
            )
        self.storage.insert_ack.assert_not_awaited()
