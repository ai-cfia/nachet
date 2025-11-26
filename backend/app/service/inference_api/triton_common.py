import requests


def check_server_health(url: str = "http://localhost:28300") -> bool:
    """Check if Triton server is ready."""
    from app.service.logs import LogService

    logger = LogService.get_logger()

    health_url = f"{url}/v2/health/ready"
    try:
        response = requests.get(health_url, timeout=5)
        if response.status_code == 200:
            logger.info(f"✓ Server is ready at {url}")
            return True
        else:
            logger.warning(f"✗ Server not ready (status: {response.status_code})")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"✗ Cannot connect to server: {e}")
        return False
