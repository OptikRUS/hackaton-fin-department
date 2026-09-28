from uuid import UUID

import pytest

from src.core.rewards.schemas import AccessoryReward
from src.infra.storages.postgres.rewards_storage import PostgresRewardStorage
from src.tests.fixtures import FactoryFixture, PostgresFixture


class TestPostgresRewardStorage(FactoryFixture, PostgresFixture):
    @pytest.fixture(autouse=True)
    async def setup(self, reward_storage: PostgresRewardStorage) -> None:
        self.storage = reward_storage

    async def test_issue_and_contiguous_listing(self) -> None:
        profile_id = UUID("344b0765-7318-450f-9576-e3f50e393f38")
        await self.postgres_helper.insert_snapshot(
            snapshot=self.factory.snapshots.snapshot(
                profile_id=profile_id,
                server_revision=1,
                game_run_id="run-1",
                current_content_fingerprint="catalog-v1",
                snapshot_json="{}",
            )
        )

        result = await self.storage.get_registered_run_for_update(profile_id=profile_id)

        assert result == "run-1"
        result = await self.storage.get_registered_run(profile_id=profile_id)

        assert result == "run-1"
        result = await self.storage.last_sequence(profile_id=profile_id, game_run_id="run-1")

        assert result == 0

        first = self.factory.rewards.grant(profile_id=profile_id)
        second = self.factory.rewards.grant(
            profile_id=profile_id,
            reward_id=UUID("9ef5db7d-f333-4f68-ab42-671212b4aa91"),
            sequence=2,
            reward=AccessoryReward(item_id="cosmetic-explorer-hat-v2"),
        )
        result = await self.storage.insert_reward(reward=first, idempotency_key="request-1")

        assert result == first
        result = await self.storage.insert_reward(reward=second, idempotency_key="request-2")

        assert result == second
        result = await self.storage.get_issue_by_key(
            profile_id=profile_id, idempotency_key="request-1"
        )

        assert result == first
        result = await self.storage.last_sequence(profile_id=profile_id, game_run_id="run-1")

        assert result == 2
        result = await self.storage.list_after(
            profile_id=profile_id, game_run_id="run-1", after_sequence=0, limit=2
        )

        assert result == [first, second]
        result = await self.storage.list_after(
            profile_id=profile_id, game_run_id="run-1", after_sequence=1, limit=1
        )

        assert result == [second]

    async def test_ack_receipts_are_immutable_and_allow_restored_application(self) -> None:
        profile_id = UUID("344b0765-7318-450f-9576-e3f50e393f38")
        await self.postgres_helper.insert_snapshot(
            snapshot=self.factory.snapshots.snapshot(
                profile_id=profile_id,
                server_revision=1,
                game_run_id="run-1",
                current_content_fingerprint="catalog-v1",
                snapshot_json="{}",
            )
        )
        reward = self.factory.rewards.grant(profile_id=profile_id)
        result = await self.storage.insert_reward(reward=reward, idempotency_key="request-1")

        assert result == reward
        first = self.factory.rewards.receipt(
            history_entry_id="reward-application:first",
        )
        restored = self.factory.rewards.receipt(
            application_id="parent-application:6a386b6f-a67a-4c31-9a12-3c660271dd32",
            history_entry_id="reward-application:restored",
            history_sequence=4,
        )
        result = await self.storage.get_rewards_by_ids(
            profile_id=profile_id, game_run_id="run-1", reward_ids=[reward.reward_id]
        )

        assert result == {reward.reward_id: reward}
        result = await self.storage.insert_receipts(
            profile_id=profile_id, game_run_id="run-1", receipts=[first, restored]
        )

        assert result == {first.application_id, restored.application_id}
        result = await self.storage.get_receipts_by_application_ids(
            application_ids=[first.application_id, restored.application_id]
        )

        assert result == {
            first.application_id: (first, profile_id, "run-1"),
            restored.application_id: (restored, profile_id, "run-1"),
        }
        result = await self.storage.insert_receipts(
            profile_id=profile_id, game_run_id="run-1", receipts=[first]
        )

        assert result == set()
        await self.storage.insert_ack(
            profile_id=profile_id,
            idempotency_key="ack-1",
            digest="f" * 64,
        )
        result = await self.storage.get_ack_by_key(profile_id=profile_id, idempotency_key="ack-1")

        assert result == "f" * 64
        result = await self.storage.list_after(
            profile_id=profile_id, game_run_id="run-1", after_sequence=0, limit=50
        )

        assert result == [reward]
