from dishka import Provider, Scope, provide

from src.core.rewards.storages import RewardStorage
from src.core.rewards.use_cases import AckRewardsUseCase, IssueRewardUseCase, ListRewardsUseCase
from src.infra.observability.business_metrics import BusinessMetrics


class RewardsProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def get_issue_reward_use_case(
        self,
        storage: RewardStorage,
        metrics: BusinessMetrics,
    ) -> IssueRewardUseCase:
        return IssueRewardUseCase(storage=storage, metrics=metrics)

    @provide(scope=Scope.REQUEST)
    def get_list_rewards_use_case(self, storage: RewardStorage) -> ListRewardsUseCase:
        return ListRewardsUseCase(storage=storage)

    @provide(scope=Scope.REQUEST)
    def get_ack_rewards_use_case(
        self,
        storage: RewardStorage,
        metrics: BusinessMetrics,
    ) -> AckRewardsUseCase:
        return AckRewardsUseCase(storage=storage, metrics=metrics)
