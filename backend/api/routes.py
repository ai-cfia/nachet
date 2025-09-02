from fastapi import APIRouter, status

router = APIRouter()

# no authentication needed
@router.get('/health', status_code=status.HTTP_200_OK, name="Get Health Status [NO AUTH REQUIRED]")
async def get_health_status():
    return 'OK'
