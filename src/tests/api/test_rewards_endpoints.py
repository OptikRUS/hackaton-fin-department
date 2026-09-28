from datetime import UTC, datetime
from uuid import UUID

import pytest
from httpx2 import codes

from src.core.profiles.schemas import DeviceId
from src.core.rewards.schemas import (
    AckRewardsParams,
    AckRewardsResult,
    CoinReward,
    IssuedReward,
    Reward,
    RewardReceipt,
    RewardsPage,
)
from src.core.rewards.use_cases import AckRewardsUseCase, IssueRewardUseCase, ListRewardsUseCase
from src.tests.fixtures import APIFixture, ContainerFixture, FactoryFixture


class TestIssueRewardAPI(APIFixture, ContainerFixture, FactoryFixture):
    @pytest.fixture(autouse=True)
    async def setup(self) -> None:
        self.use_case = await self.container_helper.override_use_case(
            use_case_type=IssueRewardUseCase,
        )

    async def test_issue_returns_exact_grant(self) -> None:
        self.use_case.execute.return_value = IssuedReward(
            reward=Reward(
                reward_id=UUID("5488c280-7f73-44e4-93a2-74d46e21a2e3"),
                profile_id=DeviceId(value="9f1c2d3e4a5b6078").profile_id,
                game_run_id="run-1",
                sequence=1,
                reward=CoinReward(amount=20),
                created_at=datetime(2026, 9, 27, 12, tzinfo=UTC),
            ),
            created=True,
        )

        response = await self.api.issue_reward(
            device_id="9f1c2d3e4a5b6078",
            idempotency_key="request-1",
            game_run_id="run-1",
            reward_type="COINS",
            amount=20,
        )

        assert response.status_code == codes.CREATED
        assert response.json() == {
            "rewardId": "5488c280-7f73-44e4-93a2-74d46e21a2e3",
            "profileId": "9f1c2d3e4a5b6078",
            "gameRunId": "run-1",
            "sequence": 1,
            "reward": {"type": "COINS", "amount": 20},
            "createdAt": "2026-09-27T12:00:00Z",
        }
        self.use_case.execute.assert_awaited_once_with(
            profile_id=DeviceId(value="9f1c2d3e4a5b6078").profile_id,
            game_run_id="run-1",
            reward=CoinReward(amount=20),
            idempotency_key="request-1",
        )

    async def test_issue_replay_returns_original_grant(self) -> None:
        self.use_case.execute.return_value = IssuedReward(
            reward=self.factory.rewards.grant(
                profile_id=DeviceId(value="9f1c2d3e4a5b6078").profile_id,
            ),
            created=False,
        )

        response = await self.api.issue_reward(
            device_id="9f1c2d3e4a5b6078",
            idempotency_key="request-1",
            game_run_id="run-1",
            reward_type="COINS",
            amount=20,
        )

        assert response.status_code == codes.CREATED
        assert response.json() == {
            "rewardId": "5488c280-7f73-44e4-93a2-74d46e21a2e3",
            "profileId": "9f1c2d3e4a5b6078",
            "gameRunId": "run-1",
            "sequence": 1,
            "reward": {"type": "COINS", "amount": 20},
            "createdAt": "2026-09-27T12:00:00Z",
        }
        self.use_case.execute.assert_awaited_once_with(
            profile_id=DeviceId(value="9f1c2d3e4a5b6078").profile_id,
            game_run_id="run-1",
            reward=CoinReward(amount=20),
            idempotency_key="request-1",
        )


class TestListRewardAPI(APIFixture, ContainerFixture, FactoryFixture):
    @pytest.fixture(autouse=True)
    async def setup(self) -> None:
        self.use_case = await self.container_helper.override_use_case(
            use_case_type=ListRewardsUseCase,
        )

    async def test_list_returns_exact_replayable_page(self) -> None:
        self.use_case.execute.return_value = RewardsPage(
            profile_id=DeviceId(value="9f1c2d3e4a5b6078").profile_id,
            game_run_id="run-1",
            rewards=(
                Reward(
                    reward_id=UUID("5488c280-7f73-44e4-93a2-74d46e21a2e3"),
                    profile_id=DeviceId(value="9f1c2d3e4a5b6078").profile_id,
                    game_run_id="run-1",
                    sequence=1,
                    reward=CoinReward(amount=20),
                    created_at=datetime(2026, 9, 27, 12, tzinfo=UTC),
                ),
            ),
            next_after_sequence=1,
            has_more=False,
        )

        response = await self.api.list_rewards(
            device_id="9f1c2d3e4a5b6078",
            game_run_id="run-1",
            after_sequence=0,
            limit=50,
        )

        assert response.status_code == codes.OK
        assert response.json() == {
            "schemaVersion": 1,
            "profileId": "9f1c2d3e4a5b6078",
            "gameRunId": "run-1",
            "rewards": [
                {
                    "rewardId": "5488c280-7f73-44e4-93a2-74d46e21a2e3",
                    "profileId": "9f1c2d3e4a5b6078",
                    "gameRunId": "run-1",
                    "sequence": 1,
                    "reward": {"type": "COINS", "amount": 20},
                    "createdAt": "2026-09-27T12:00:00Z",
                }
            ],
            "nextAfterSequence": 1,
            "hasMore": False,
        }
        self.use_case.execute.assert_awaited_once_with(
            profile_id=DeviceId(value="9f1c2d3e4a5b6078").profile_id,
            game_run_id="run-1",
            after_sequence=0,
            limit=50,
        )


class TestAckRewardAPI(APIFixture, ContainerFixture, FactoryFixture):
    @pytest.fixture(autouse=True)
    async def setup(self) -> None:
        self.use_case = await self.container_helper.override_use_case(
            use_case_type=AckRewardsUseCase,
        )

    async def test_ack_returns_exact_accepted_application_ids(self) -> None:
        self.use_case.execute.return_value = AckRewardsResult(
            game_run_id="run-1",
            accepted_application_ids=("parent-application:7e0f74aa-9354-47f4-a2a6-3857bf3b7571",),
        )

        response = await self.api.ack_rewards(
            device_id="9f1c2d3e4a5b6078",
            idempotency_key="ack-1",
            game_run_id="run-1",
            receipts=[
                {
                    "rewardId": "5488c280-7f73-44e4-93a2-74d46e21a2e3",
                    "applicationId": "parent-application:7e0f74aa-9354-47f4-a2a6-3857bf3b7571",
                    "historyEntryId": "reward-application:7e0f74aa-9354-47f4-a2a6-3857bf3b7571",
                    "historySequence": 18,
                    "outcome": "APPLIED",
                }
            ],
        )

        assert response.status_code == codes.OK
        assert response.json() == {
            "schemaVersion": 1,
            "gameRunId": "run-1",
            "acceptedApplicationIds": ["parent-application:7e0f74aa-9354-47f4-a2a6-3857bf3b7571"],
        }
        self.use_case.execute.assert_awaited_once_with(
            profile_id=DeviceId(value="9f1c2d3e4a5b6078").profile_id,
            idempotency_key="ack-1",
            params=AckRewardsParams(
                game_run_id="run-1",
                receipts=(
                    RewardReceipt(
                        reward_id=UUID("5488c280-7f73-44e4-93a2-74d46e21a2e3"),
                        application_id="parent-application:7e0f74aa-9354-47f4-a2a6-3857bf3b7571",
                        history_entry_id="reward-application:7e0f74aa-9354-47f4-a2a6-3857bf3b7571",
                        history_sequence=18,
                        outcome="APPLIED",
                    ),
                ),
            ),
        )
