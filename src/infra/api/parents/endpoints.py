from typing import Annotated

from fastapi import APIRouter, Path

from src.infra.api.parents.schemas import ParentPetResponse, ParentResponse, demo_skills

router = APIRouter(prefix="/api/parents", tags=["parents"])


@router.get(path="/{petId}")
async def get_parent_report(
    pet_id: Annotated[str, Path(alias="petId", min_length=1)],
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
        skills=demo_skills(),
        is_demo=True,
    )
