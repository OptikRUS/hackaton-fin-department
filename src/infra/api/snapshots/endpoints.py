from typing import Annotated

from dishka import FromDishka
from dishka.integrations.fastapi import DishkaRoute
from fastapi import APIRouter, Header, status

from src.core.profiles.schemas import DeviceId
from src.core.snapshots.use_cases import DownloadSnapshotUseCase, UploadSnapshotUseCase
from src.infra.api.snapshots.schemas import (
    SnapshotDownloadRequest,
    SnapshotDownloadResponse,
    SnapshotError,
    SnapshotUploadRequest,
    SnapshotUploadResponse,
)

router = APIRouter(prefix="/v1/profiles", tags=["World snapshots"], route_class=DishkaRoute)


@router.put(
    path="/snapshot",
    status_code=status.HTTP_200_OK,
    response_model=SnapshotUploadResponse,
    responses={
        status.HTTP_400_BAD_REQUEST: {"model": SnapshotError},
        status.HTTP_409_CONFLICT: {"model": SnapshotError},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"model": SnapshotError},
    },
)
async def upload_snapshot(
    body: SnapshotUploadRequest,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=1)],
    use_case: FromDishka[UploadSnapshotUseCase],
) -> SnapshotUploadResponse:
    result = await use_case.execute(
        params=body.to_domain(),
        idempotency_key=idempotency_key,
    )
    return SnapshotUploadResponse.from_domain(result=result)


@router.post(
    path="/snapshot/download",
    status_code=status.HTTP_200_OK,
    response_model=SnapshotDownloadResponse,
    responses={status.HTTP_404_NOT_FOUND: {"model": SnapshotError}},
)
async def download_snapshot(
    body: SnapshotDownloadRequest,
    use_case: FromDishka[DownloadSnapshotUseCase],
) -> SnapshotDownloadResponse:
    snapshot = await use_case.execute(profile_id=DeviceId(value=body.device_id).profile_id)
    return SnapshotDownloadResponse.from_domain(snapshot=snapshot)
