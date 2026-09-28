from dishka import AsyncContainer, make_async_container
from dishka.integrations.fastapi import FastapiProvider

from src.di.providers.analytics import AnalyticsProvider
from src.di.providers.general import GeneralProvider
from src.di.providers.pets import PetsProvider
from src.di.providers.postgres import PostgresProvider
from src.di.providers.profiles import ProfilesProvider
from src.di.providers.rewards import RewardsProvider
from src.di.providers.snapshots import SnapshotsProvider


def create_container() -> AsyncContainer:
    return make_async_container(
        FastapiProvider(),
        GeneralProvider(),
        PostgresProvider(),
        ProfilesProvider(),
        AnalyticsProvider(),
        RewardsProvider(),
        PetsProvider(),
        SnapshotsProvider(),
    )
