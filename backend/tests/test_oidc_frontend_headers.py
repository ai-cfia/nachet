from fastapi import APIRouter
from httpx import ASGITransport, AsyncClient
import pytest

from app.api.config import Settings, create_app
from app.service.auth.config import BackendAuthConfig


# Use Nachet's middleware stack so the test checks the CSP served with the frontend.
def create_frontend_app(settings: Settings):
    router = APIRouter()
    auth_config = BackendAuthConfig.from_settings(settings)

    @router.get("/")
    async def frontend_root() -> dict[str, str]:
        return {"status": "ok"}

    return create_app(
        settings,
        router,
        auth_provider_origin=auth_config.browser_provider_origin,
    )


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
    assert "connect-src 'self'" in csp
    assert "frame-src 'self'" in csp
    assert "https://keycloak.localhost:8443" in csp
    assert "https://keycloak.localhost:8443/realms/nachet" not in csp

    directives = {
        directive.partition(" ")[0]: directive
        for directive in csp.split("; ")
        if directive
    }
    assert "https://keycloak.localhost:8443" in directives["connect-src"]
    assert "https://keycloak.localhost:8443" in directives["frame-src"]


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
