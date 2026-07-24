from fastapi import APIRouter
from httpx import ASGITransport, AsyncClient
import pytest

from app.api.config import Settings, create_app


# Use Nachet's middleware stack so the test checks the CSP served with the frontend.
def create_frontend_app(settings: Settings):
    router = APIRouter()

    @router.get("/")
    async def frontend_root() -> dict[str, str]:
        return {"status": "ok"}

    return create_app(settings, router)


@pytest.mark.asyncio
async def test_oidc_frontend_csp_allows_the_configured_issuer_origin() -> None:
    app = create_frontend_app(
        Settings(
            auth_provider="oidc",
            oidc_issuer="https://keycloak.localhost:8443/realms/nachet",
            oidc_audience="nachet-api",
        )
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
    ) as client:
        response = await client.get("/")

    csp = response.headers["content-security-policy"]
    directives: dict[str, set[str]] = {}
    for directive in csp.split(";"):
        parts = directive.split()
        if parts:
            directives[parts[0]] = set(parts[1:])

    provider_origin = "https://keycloak.localhost:8443"
    provider_issuer = f"{provider_origin}/realms/nachet"
    connect_sources = directives["connect-src"]
    frame_sources = directives["frame-src"]

    assert "'self'" in connect_sources
    assert "'self'" in frame_sources
    assert provider_origin in connect_sources
    assert provider_origin in frame_sources
    assert provider_issuer not in connect_sources
    assert provider_issuer not in frame_sources


@pytest.mark.asyncio
async def test_azure_frontend_csp_does_not_add_an_oidc_issuer() -> None:
    app = create_frontend_app(
        Settings(
            auth_provider="azure",
            oidc_issuer="https://untrusted.example/realms/nachet",
        )
    )

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://localhost",
    ) as client:
        response = await client.get("/")

    assert "https://untrusted.example" not in response.headers[
        "content-security-policy"
    ]
