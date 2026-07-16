from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_PATH = REPOSITORY_ROOT / "docker-compose.yaml"
REALM_PATH = REPOSITORY_ROOT / "keycloak" / "nachet-realm.json"
BACKEND_DOCKERIGNORE_PATH = REPOSITORY_ROOT / "backend" / ".dockerignore"

LOCAL_ISSUER = "http://keycloak.localhost:8080/realms/nachet"
LOCAL_ADMIN_USER_ID = "8ea46a6b-7d37-4fbb-a66f-775112376e16"
LOCAL_FRONTEND_ORIGINS = {
    "http://localhost:5173",
    "http://localhost:12436",
}


def load_compose() -> dict:
    return yaml.safe_load(COMPOSE_PATH.read_text())


def load_realm() -> dict:
    return json.loads(REALM_PATH.read_text())


def get_client(realm: dict, client_id: str) -> dict:
    for client in realm["clients"]:
        if client["clientId"] == client_id:
            return client
    raise AssertionError(f"Realm does not define client {client_id}")


def get_client_scope(realm: dict, scope_name: str) -> dict:
    for scope in realm["clientScopes"]:
        if scope["name"] == scope_name:
            return scope
    raise AssertionError(f"Realm does not define client scope {scope_name}")


def get_protocol_mapper(client_scope: dict, mapper_type: str) -> dict:
    for mapper in client_scope["protocolMappers"]:
        if mapper["protocolMapper"] == mapper_type:
            return mapper
    raise AssertionError(f"Client scope does not define mapper {mapper_type}")


def test_compose_runs_a_pinned_local_keycloak_with_fixed_issuer() -> None:
    service = load_compose()["services"]["nachet-keycloak"]

    assert service["image"].startswith("quay.io/keycloak/keycloak:")
    assert not service["image"].endswith(":latest")
    assert service["command"] == ["start-dev", "--import-realm"]
    assert service["environment"]["KC_HOSTNAME"] == "http://keycloak.localhost:8080"
    assert "KC_HOSTNAME_BACKCHANNEL_DYNAMIC" not in service["environment"]
    assert set(service["ports"]) == {
        "127.0.0.1:8080:8080",
        "[::1]:8080:8080",
    }
    assert service["mem_limit"] == "1g"


def test_keycloak_network_is_shared_only_with_the_backend() -> None:
    services = load_compose()["services"]
    keycloak_network = "nachet-oidc-network"

    keycloak_network_config = services["nachet-keycloak"]["networks"]
    assert set(keycloak_network_config) == {keycloak_network}
    assert keycloak_network_config[keycloak_network]["aliases"] == [
        "keycloak.localhost"
    ]
    assert keycloak_network in services["nachet-backend"]["networks"]
    for service_name, service in services.items():
        if service_name not in {"nachet-keycloak", "nachet-backend"}:
            assert keycloak_network not in service.get("networks", [])


def test_compose_does_not_override_backend_oidc_configuration() -> None:
    backend_service = load_compose()["services"]["nachet-backend"]

    assert "environment" not in backend_service


def test_compose_backend_builds_from_an_existing_dockerfile() -> None:
    backend_build = load_compose()["services"]["nachet-backend"]["build"]
    dockerfile_path = (
        REPOSITORY_ROOT / backend_build["context"] / backend_build["dockerfile"]
    )

    assert dockerfile_path.is_file()


def test_backend_image_excludes_local_environment_and_virtualenv_files() -> None:
    ignored_paths = set(BACKEND_DOCKERIGNORE_PATH.read_text().splitlines())

    assert ".env*" in ignored_paths
    assert ".venv" in ignored_paths


def test_compose_imports_the_realm_read_only() -> None:
    service = load_compose()["services"]["nachet-keycloak"]

    assert (
        "./keycloak/nachet-realm.json:/opt/keycloak/data/import/nachet-realm.json:ro"
        in service["volumes"]
    )


def test_realm_configures_a_public_pkce_frontend_client() -> None:
    frontend_client = get_client(load_realm(), "nachet-frontend")

    assert frontend_client["publicClient"] is True
    assert frontend_client["standardFlowEnabled"] is True
    assert frontend_client["directAccessGrantsEnabled"] is False
    assert frontend_client["serviceAccountsEnabled"] is False
    assert "secret" not in frontend_client
    assert frontend_client["attributes"]["pkce.code.challenge.method"] == "S256"
    assert set(frontend_client["redirectUris"]) == LOCAL_FRONTEND_ORIGINS
    assert set(frontend_client["webOrigins"]) == LOCAL_FRONTEND_ORIGINS


def test_realm_adds_the_api_audience_to_access_tokens() -> None:
    realm = load_realm()
    frontend_client = get_client(realm, "nachet-frontend")
    api_client = get_client(realm, "nachet-api")
    api_scope = get_client_scope(realm, "nachet-api")
    audience_mapper = get_protocol_mapper(api_scope, "oidc-audience-mapper")

    assert api_client["bearerOnly"] is True
    assert "nachet-api" in frontend_client["optionalClientScopes"]
    assert audience_mapper["config"]["included.client.audience"] == "nachet-api"
    assert audience_mapper["config"]["access.token.claim"] == "true"
    assert audience_mapper["config"]["id.token.claim"] == "false"


def test_frontend_references_only_client_scopes_defined_by_the_realm() -> None:
    realm = load_realm()
    frontend_client = get_client(realm, "nachet-frontend")
    defined_scope_names = {scope["name"] for scope in realm["clientScopes"]}
    referenced_scope_names = set(frontend_client["defaultClientScopes"])
    referenced_scope_names.update(frontend_client["optionalClientScopes"])

    assert referenced_scope_names == {"basic", "profile", "email", "nachet-api"}
    assert referenced_scope_names <= defined_scope_names


def test_realm_adds_the_user_subject_to_access_tokens() -> None:
    realm = load_realm()
    basic_scope = get_client_scope(realm, "basic")
    subject_mapper = get_protocol_mapper(basic_scope, "oidc-sub-mapper")

    assert subject_mapper["config"]["access.token.claim"] == "true"


def test_realm_users_have_uuid_subjects_and_non_temporary_local_passwords() -> None:
    users = load_realm()["users"]

    assert len(users) == 2
    assert any(user["id"] == LOCAL_ADMIN_USER_ID for user in users)
    for user in users:
        UUID(user["id"])
        assert user["enabled"] is True
        assert user["credentials"] == [
            {
                "type": "password",
                "value": "nachet-local",
                "temporary": False,
            }
        ]


def test_environment_templates_use_the_same_local_keycloak_contract() -> None:
    frontend_template = (REPOSITORY_ROOT / "frontend" / ".env.template").read_text()
    backend_template = (REPOSITORY_ROOT / "backend" / ".env.template").read_text()

    assert f'VITE_OIDC_AUTHORITY="{LOCAL_ISSUER}"' in frontend_template
    assert 'VITE_OIDC_API_SCOPE_CLAIM="nachet-api"' in frontend_template
    assert 'VITE_OIDC_REDIRECT_URI="http://localhost:5173"' in frontend_template
    assert (
        'VITE_OIDC_POST_LOGOUT_REDIRECT_URI="http://localhost:5173"'
        in frontend_template
    )
    assert f'OIDC_ISSUER="{LOCAL_ISSUER}"' in backend_template
    assert 'OIDC_AUDIENCE="nachet-api"' in backend_template
    assert 'NACHET_ENV="local"' in backend_template
    assert (
        'CORS_ALLOW_ORIGINS="http://localhost:5173,http://localhost:12436"'
        in backend_template
    )
    assert "OIDC_DISCOVERY_URL" not in backend_template
    assert 'OIDC_REQUIRE_HTTPS_METADATA="false"' in backend_template


def test_local_keycloak_documentation_uses_one_frontend_origin() -> None:
    developer_guide = (REPOSITORY_ROOT / "DEVELOPER.md").read_text()

    assert "npm run dev -- --port 5173" in developer_guide
    assert "npm run dev -- --port 12438" not in developer_guide
    assert LOCAL_ISSUER in developer_guide
    assert "OIDC_DISCOVERY_URL" not in developer_guide
