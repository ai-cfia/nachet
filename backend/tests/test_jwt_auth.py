from uuid import uuid4

import pytest
from fastapi import HTTPException
from fastapi.security import SecurityScopes
from starlette.requests import HTTPConnection

from app.api import config as config_module
from app.service.auth.jwt_auth import JWTAuthenticator


def reset_settings_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config_module, "_settings", None)


def make_http_connection() -> HTTPConnection:
    return HTTPConnection({"type": "http", "headers": []})


@pytest.mark.asyncio
async def test_auth_disabled_returns_local_dev_user(
    monkeypatch: pytest.MonkeyPatch,
):
    dev_user_id = str(uuid4())
    monkeypatch.setenv("AZURE_AUTH_ENABLED", "false")
    monkeypatch.setenv("NACHET_ENV", "development")
    monkeypatch.setenv("DEV_USER_ID", dev_user_id)
    monkeypatch.setenv("DEV_USER_EMAIL", "local.dev@example.test")
    monkeypatch.setenv("DEV_USER_NAME", "Local Dev")
    reset_settings_cache(monkeypatch)

    request = make_http_connection()
    user = await JWTAuthenticator()(request, SecurityScopes())

    assert user.oid == dev_user_id
    assert user.email == "local.dev@example.test"
    assert user.preferred_username == "local.dev@example.test"
    assert user.name == "Local Dev"
    assert user.access_token == "local-dev-auth-disabled"
    assert request.state.user.oid == dev_user_id


@pytest.mark.asyncio
async def test_auth_disabled_requires_valid_dev_user_id(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("AZURE_AUTH_ENABLED", "false")
    monkeypatch.setenv("NACHET_ENV", "development")
    monkeypatch.setenv("DEV_USER_ID", "not-a-uuid")
    reset_settings_cache(monkeypatch)

    with pytest.raises(HTTPException) as exc_info:
        await JWTAuthenticator()(make_http_connection(), SecurityScopes())

    assert exc_info.value.status_code == 500
    assert "Invalid DEV_USER_ID format" in exc_info.value.detail


@pytest.mark.asyncio
async def test_auth_disabled_is_rejected_outside_development_or_test(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("AZURE_AUTH_ENABLED", "false")
    monkeypatch.setenv("NACHET_ENV", "production")
    monkeypatch.setenv("IS_TEST_ENVIRONMENT", "false")
    reset_settings_cache(monkeypatch)

    with pytest.raises(HTTPException) as exc_info:
        await JWTAuthenticator()(make_http_connection(), SecurityScopes())

    assert exc_info.value.status_code == 500
    assert "AZURE_AUTH_ENABLED=false is only allowed" in exc_info.value.detail


@pytest.mark.asyncio
async def test_auth_disabled_is_allowed_in_test_environment(
    monkeypatch: pytest.MonkeyPatch,
):
    dev_user_id = str(uuid4())
    monkeypatch.setenv("AZURE_AUTH_ENABLED", "false")
    monkeypatch.setenv("NACHET_ENV", "production")
    monkeypatch.setenv("IS_TEST_ENVIRONMENT", "true")
    monkeypatch.setenv("DEV_USER_ID", dev_user_id)
    reset_settings_cache(monkeypatch)

    user = await JWTAuthenticator()(make_http_connection(), SecurityScopes())

    assert user.oid == dev_user_id


@pytest.mark.asyncio
async def test_auth_disabled_is_allowed_in_local_environment(
    monkeypatch: pytest.MonkeyPatch,
):
    dev_user_id = str(uuid4())
    monkeypatch.setenv("AZURE_AUTH_ENABLED", "false")
    monkeypatch.setenv("NACHET_ENV", "local")
    monkeypatch.setenv("IS_TEST_ENVIRONMENT", "false")
    monkeypatch.setenv("DEV_USER_ID", dev_user_id)
    reset_settings_cache(monkeypatch)

    user = await JWTAuthenticator()(make_http_connection(), SecurityScopes())

    assert user.oid == dev_user_id


@pytest.mark.asyncio
async def test_auth_enabled_still_requires_azure_configuration(
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("AZURE_AUTH_ENABLED", "true")
    monkeypatch.delenv("AZURE_CLIENT_ID", raising=False)
    monkeypatch.delenv("AZURE_TENANT_ID", raising=False)
    reset_settings_cache(monkeypatch)

    with pytest.raises(HTTPException) as exc_info:
        await JWTAuthenticator()(make_http_connection(), SecurityScopes())

    assert exc_info.value.status_code == 500
    assert "Azure AD configuration missing" in exc_info.value.detail
