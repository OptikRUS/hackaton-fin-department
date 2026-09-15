from dishka import AsyncContainer, make_async_container
from dishka.integrations.fastapi import FastapiProvider

from src.di.providers.general import GeneralProvider


def create_container() -> AsyncContainer:
    return make_async_container(
        FastapiProvider(),
        GeneralProvider(),
    )
