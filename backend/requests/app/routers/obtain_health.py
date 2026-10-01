from fastapi import APIRouter, status
from ..models.health import Health

router = APIRouter()

#get de health para comprobar que anda vivo el fastapi
@router.get("/health", response_model=Health, status_code=status.HTTP_200_OK)
def health_check():
    return Health(status="ok")
