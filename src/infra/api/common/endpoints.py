from fastapi import APIRouter, Response, status

router = APIRouter(prefix="", tags=["default"])


@router.get(path="/health")
async def health() -> Response:
    return Response(status_code=status.HTTP_200_OK)
