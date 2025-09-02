from fastapi import APIRouter, status

router = APIRouter()

# no authentication needed
@router.get('/health', status_code=status.HTTP_200_OK, name="Get Health Status [NO AUTH REQUIRED]")
async def get_health_status():
    return 'OK'

@router.get('/version', status_code=status.HTTP_200_OK, name="Get API Version [NO AUTH REQUIRED]")
async def get_version():
    return '0.0.0'

@router.get('/ready', status_code=status.HTTP_200_OK, name="Get Readiness Status [NO AUTH REQUIRED]")
async def get_readiness_status():
    return 'OK'


