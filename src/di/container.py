from dishka import AsyncContainer, make_async_container
from dishka.integrations.fastapi import FastapiProvider

from src.di.providers.general import GeneralProvider
from src.di.providers.pets import PetsProvider
from src.di.providers.postgres import PostgresProvider
from src.di.providers.snapshots import SnapshotsProvider


def create_container() -> AsyncContainer:
    return make_async_container(
        FastapiProvider(),
        GeneralProvider(),
        PostgresProvider(),
        PetsProvider(),
        SnapshotsProvider(),
    )
