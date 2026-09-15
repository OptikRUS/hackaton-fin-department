from fastapi import APIRouter

from src.infra.api.common import endpoints as common

root_router = APIRouter()
root_router.include_router(router=common.router, include_in_schema=False)
