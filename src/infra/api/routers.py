from fastapi import APIRouter

from src.infra.api.common import endpoints as common
from src.infra.api.pets import endpoints as pets

root_router = APIRouter()
root_router.include_router(router=common.router, include_in_schema=False)
root_router.include_router(router=pets.router)
