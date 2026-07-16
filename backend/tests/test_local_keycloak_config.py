from __future__ import annotations

import importlib.util
import json
from pathlib import Path
from types import ModuleType
from uuid import UUID

import pytest
import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
COMPOSE_PATH = REPOSITORY_ROOT / "docker-compose.yaml"
REALM_PATH = REPOSITORY_ROOT / "keycloak" / "nachet-realm.json"
BACKEND_DOCKERIGNORE_PATH = REPOSITORY_ROOT / "backend" / ".dockerignore"
TLS_SETUP_PATH = REPOSITORY_ROOT / "keycloak" / "setup_local_tls.py"
LOCAL_CA_DIRECTORY = REPOSITORY_ROOT / "keycloak" / "local-certs" / "ca"
LOCAL_SERVER_CERT_DIRECTORY = (
    REPOSITORY_ROOT / "keycloak" / "local-certs" / "server"
)

LOCAL_ISSUER = "https://keycloak.localhost:8443/realms/nachet"
LOCAL_ADMIN_USER_ID = "8ea46a6b-7d37-4fbb-a66f-775112376e16"
LOCAL_FRONTEND_ORIGINS = {
    "http://localhost:5173",
    "http://localhost:12436",
}


def load_compose() -> dict:
    return yaml.safe_load(COMPOSE_PATH.read_text())


def load_realm() -> dict:
    return json.loads(REALM_PATH.read_text())


def load_tls_setup_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("setup_local_tls", TLS_SETUP_PATH)
    if spec is None or spec.loader is None:
        raise AssertionError("Unable to load local TLS setup script")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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
    assert service["command"] == ["start", "--import-realm"]
    assert service["environment"]["KC_DB"] == "dev-file"
    assert service["environment"]["KC_CACHE"] == "local"
    assert service["environment"]["KC_HOSTNAME"] == "https://keycloak.localhost:8443"
    assert service["environment"]["KC_HTTP_ENABLED"] == "false"
    assert service["environment"]["KC_HTTP_MANAGEMENT_SCHEME"] == "http"
    assert (
        service["environment"]["KC_HTTPS_CERTIFICATE_FILE"]
        == "/opt/keycloak/conf/tls/keycloak.pem"
    )
    assert (
        service["environment"]["KC_HTTPS_CERTIFICATE_KEY_FILE"]
        == "/opt/keycloak/conf/tls/keycloak-key.pem"
    )
    assert "KC_HOSTNAME_BACKCHANNEL_DYNAMIC" not in service["environment"]
    assert set(service["ports"]) == {
        "127.0.0.1:8443:8443",
        "[::1]:8443:8443",
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


def test_backend_container_receives_only_the_public_local_ca() -> None:
    backend_service = load_compose()["services"]["nachet-backend"]

    assert backend_service["environment"] == {
        "OIDC_CA_BUNDLE": "/opt/nachet/local-ca/rootCA.pem"
    }
    assert (
        "./keycloak/local-certs/ca:/opt/nachet/local-ca:ro"
        in backend_service["volumes"]
    )
    assert all("local-certs/server" not in volume for volume in backend_service["volumes"])


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
    assert (
        "./keycloak/local-certs/server:/opt/keycloak/conf/tls:ro"
        in service["volumes"]
    )


def test_realm_requires_https_for_all_requests() -> None:
    assert load_realm()["sslRequired"] == "all"


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
    assert "OIDC_REQUIRE_HTTPS_METADATA" not in backend_template
    assert (
        'OIDC_CA_BUNDLE="../keycloak/local-certs/ca/rootCA.pem"'
        in backend_template
    )


def test_local_keycloak_documentation_uses_one_frontend_origin() -> None:
    developer_guide = (REPOSITORY_ROOT / "DEVELOPER.md").read_text()

    assert "npm run dev -- --port 5173" in developer_guide
    assert "npm run dev -- --port 12438" not in developer_guide
    assert LOCAL_ISSUER in developer_guide
    assert "OIDC_DISCOVERY_URL" not in developer_guide
    assert "OIDC_REQUIRE_HTTPS_METADATA" not in developer_guide
    assert "python keycloak/setup_local_tls.py" in developer_guide


def test_generated_local_certificates_are_ignored() -> None:
    for directory in (LOCAL_CA_DIRECTORY, LOCAL_SERVER_CERT_DIRECTORY):
        ignore_file = directory / ".gitignore"
        assert ignore_file.is_file()
        assert ignore_file.read_text().splitlines() == ["*", "!.gitignore"]


def test_tls_setup_copies_only_the_public_ca(tmp_path: Path) -> None:
    module = load_tls_setup_module()
    ca_root = tmp_path / "mkcert-ca"
    destination = tmp_path / "repository-ca"
    ca_root.mkdir()
    (ca_root / "rootCA.pem").write_text("public CA")
    (ca_root / "rootCA-key.pem").write_text("private CA key")

    module.copy_public_ca(ca_root, destination)

    assert (destination / "rootCA.pem").read_text() == "public CA"
    assert not (destination / "rootCA-key.pem").exists()


def test_tls_setup_generates_server_certificate_and_copies_public_ca(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    module = load_tls_setup_module()
    server_directory = tmp_path / "server"
    ca_directory = tmp_path / "ca"
    mkcert_ca_root = tmp_path / "mkcert-ca"
    mkcert_ca_root.mkdir()
    (mkcert_ca_root / "rootCA.pem").write_text("public CA")
    commands: list[list[str]] = []

    def fake_run(command: list[str], *, capture_output: bool = False) -> str:
        commands.append(command)
        if "-cert-file" in command:
            certificate_path = Path(command[command.index("-cert-file") + 1])
            private_key_path = Path(command[command.index("-key-file") + 1])
            certificate_path.write_text("certificate")
            private_key_path.write_text("private key")
        if "-CAROOT" in command:
            return str(mkcert_ca_root)
        return ""

    monkeypatch.setattr(module.shutil, "which", lambda command: "/usr/bin/mkcert")
    monkeypatch.setattr(module, "_run", fake_run)
    monkeypatch.setattr(module, "_hostname_resolves", lambda: True)
    monkeypatch.setattr(module, "SERVER_CERT_DIRECTORY", server_directory)
    monkeypatch.setattr(module, "CA_CERT_DIRECTORY", ca_directory)

    assert module.main() == 0
    assert commands == [
        ["/usr/bin/mkcert", "-install"],
        [
            "/usr/bin/mkcert",
            "-cert-file",
            str(server_directory / "keycloak.pem"),
            "-key-file",
            str(server_directory / "keycloak-key.pem"),
            "keycloak.localhost",
        ],
        ["/usr/bin/mkcert", "-CAROOT"],
    ]
    assert (ca_directory / "rootCA.pem").read_text() == "public CA"
