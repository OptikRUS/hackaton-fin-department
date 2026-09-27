from typing import cast
from unittest.mock import AsyncMock

from dishka import Provider, Scope, provide

from src.core.rewards.use_cases import AckRewardsUseCase, IssueRewardUseCase, ListRewardsUseCase


class MockRewardsUseCaseProvider(Provider):
    @provide(scope=Scope.APP)
    def get_issue_reward_use_case(self) -> IssueRewardUseCase:
        return cast("IssueRewardUseCase", AsyncMock(spec=IssueRewardUseCase))

    @provide(scope=Scope.APP)
    def get_list_rewards_use_case(self) -> ListRewardsUseCase:
        return cast("ListRewardsUseCase", AsyncMock(spec=ListRewardsUseCase))

    @provide(scope=Scope.APP)
    def get_ack_rewards_use_case(self) -> AckRewardsUseCase:
        return cast("AckRewardsUseCase", AsyncMock(spec=AckRewardsUseCase))
