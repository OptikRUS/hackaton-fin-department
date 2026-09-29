from fastapi import APIRouter

from src.infra.api.analytics import endpoints as analytics
from src.infra.api.common import endpoints as common
from src.infra.api.parents import endpoints as parents
from src.infra.api.pets import endpoints as pets
from src.infra.api.profiles import endpoints as profiles
from src.infra.api.rewards import endpoints as rewards
from src.infra.api.snapshots import endpoints as snapshots

root_router = APIRouter()
root_router.include_router(router=common.router, include_in_schema=False)
root_router.include_router(router=profiles.router)
root_router.include_router(router=pets.router, include_in_schema=False)
root_router.include_router(router=analytics.router)
root_router.include_router(router=rewards.parent_router)
root_router.include_router(router=rewards.device_router)
root_router.include_router(router=parents.router)
root_router.include_router(router=parents.materials_router)
root_router.include_router(router=snapshots.router)
