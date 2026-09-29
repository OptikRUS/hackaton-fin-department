from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Depends, Path

from src.core.parents.use_cases import GetParentReportUseCase
from src.infra.api.parents.schemas import ParentResponse
from src.infra.api.parents.skill_content import ParentMaterialsResponse, load_parent_materials

router = APIRouter(prefix="/api/parents", tags=["parents"], route_class=DishkaRoute)


@router.get(path="/{petId}")
async def get_parent_report(
    pet_id: Annotated[str, Path(alias="petId", min_length=1)],
    materials: Annotated[ParentMaterialsResponse, Depends(load_parent_materials)],
    use_case: FromDishka[GetParentReportUseCase],
) -> ParentResponse:
    report = await use_case.execute(device_id=pet_id)
    return ParentResponse.from_domain(report=report, materials=materials)


materials_router = APIRouter(prefix="/v1/parent-materials", tags=["Parent materials"])


@materials_router.get("")
async def get_parent_materials(
    materials: Annotated[ParentMaterialsResponse, Depends(load_parent_materials)],
) -> ParentMaterialsResponse:
    return materials
