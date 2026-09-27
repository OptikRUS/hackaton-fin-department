from typing import Annotated
from uuid import UUID

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Header, Path, status
from fastapi.responses import JSONResponse

from src.core.snapshots.use_cases import DownloadSnapshotUseCase, UploadSnapshotUseCase
from src.infra.api.snapshots.schemas import (
    SnapshotDownloadResponse,
    SnapshotError,
    SnapshotUploadRequest,
    SnapshotUploadResponse,
)

router = APIRouter(prefix="/v1/profiles", tags=["World snapshots"], route_class=DishkaRoute)


@router.put(
    path="/{profileId}/snapshot",
    status_code=status.HTTP_200_OK,
    response_model=SnapshotUploadResponse,
    responses={
        status.HTTP_201_CREATED: {"model": SnapshotUploadResponse},
        status.HTTP_400_BAD_REQUEST: {"model": SnapshotError},
        status.HTTP_409_CONFLICT: {"model": SnapshotError},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": SnapshotError},
    },
)
async def upload_snapshot(
    profile_id: Annotated[UUID, Path(alias="profileId")],
    body: SnapshotUploadRequest,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1)],
    use_case: FromDishka[UploadSnapshotUseCase],
) -> JSONResponse:
    result = await use_case.execute(
        params=body.to_domain(profile_id=profile_id),
        idempotency_key=idempotency_key,
    )
    return JSONResponse(
        status_code=status.HTTP_201_CREATED if result.created else status.HTTP_200_OK,
        content=SnapshotUploadResponse.from_domain(result=result).dict(),
    )


@router.get(
    path="/{profileId}/snapshot",
    status_code=status.HTTP_200_OK,
    response_model=SnapshotDownloadResponse,
    responses={status.HTTP_404_NOT_FOUND: {"model": SnapshotError}},
)
async def download_snapshot(
    profile_id: Annotated[UUID, Path(alias="profileId")],
    use_case: FromDishka[DownloadSnapshotUseCase],
) -> SnapshotDownloadResponse:
    snapshot = await use_case.execute(profile_id=profile_id)
    return SnapshotDownloadResponse.from_domain(snapshot=snapshot)
