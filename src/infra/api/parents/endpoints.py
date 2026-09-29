from typing import Annotated

from fastapi import APIRouter, Depends, Path

from src.infra.api.parents.schemas import ParentPetResponse, ParentResponse, demo_skills
from src.infra.api.parents.skill_content import ParentMaterialsResponse, load_parent_materials

router = APIRouter(prefix="/api/parents", tags=["parents"])


@router.get(path="/{petId}")
async def get_parent_report(
    pet_id: Annotated[str, Path(alias="petId", min_length=1)],
    materials: Annotated[ParentMaterialsResponse, Depends(load_parent_materials)],
) -> ParentResponse:
    return ParentResponse(
        pet=ParentPetResponse(
            id=pet_id,
            name="Рыжик",
            temper="playful",
            balance=100,
            selected_look_id="BACKPACK",
            visual_state="NORMAL",
        ),
        skills=demo_skills(materials),
        is_demo=True,
    )


materials_router = APIRouter(prefix="/v1/parent-materials", tags=["Parent materials"])


@materials_router.get("")
async def get_parent_materials(
    materials: Annotated[ParentMaterialsResponse, Depends(load_parent_materials)],
) -> ParentMaterialsResponse:
    return materials
