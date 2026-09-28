from dishka import Provider, Scope, provide

from src.core.rewards.storages import RewardStorage
from src.core.rewards.use_cases import AckRewardsUseCase, IssueRewardUseCase, ListRewardsUseCase


class RewardsProvider(Provider):
    @provide(scope=Scope.REQUEST)
    def get_issue_reward_use_case(self, storage: RewardStorage) -> IssueRewardUseCase:
        return IssueRewardUseCase(storage=storage)

    @provide(scope=Scope.REQUEST)
    def get_list_rewards_use_case(self, storage: RewardStorage) -> ListRewardsUseCase:
        return ListRewardsUseCase(storage=storage)

    @provide(scope=Scope.REQUEST)
    def get_ack_rewards_use_case(self, storage: RewardStorage) -> AckRewardsUseCase:
        return AckRewardsUseCase(storage=storage)
