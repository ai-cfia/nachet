from __future__ import annotations

import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path


KEYCLOAK_HOST = "keycloak.localhost"
KEYCLOAK_DIRECTORY = Path(__file__).resolve().parent
LOCAL_CERT_DIRECTORY = KEYCLOAK_DIRECTORY / "local-certs"
SERVER_CERT_DIRECTORY = LOCAL_CERT_DIRECTORY / "server"
CA_CERT_DIRECTORY = LOCAL_CERT_DIRECTORY / "ca"


def copy_public_ca(ca_root: Path, destination: Path) -> None:
    public_ca = ca_root / "rootCA.pem"
    if not public_ca.is_file():
        raise RuntimeError(f"mkcert did not create {public_ca}")

    destination.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(public_ca, destination / "rootCA.pem")


def _run(command: list[str], *, capture_output: bool = False) -> str:
    result = subprocess.run(
        command,
        check=True,
        text=True,
        capture_output=capture_output,
    )
    return result.stdout.strip() if capture_output else ""


def _hostname_resolves() -> bool:
    try:
        socket.getaddrinfo(KEYCLOAK_HOST, 8443)
    except socket.gaierror:
        return False
    return True


def _print_hosts_file_help() -> None:
    if os.name == "nt":
        hosts_file = r"C:\Windows\System32\drivers\etc\hosts"
    else:
        hosts_file = "/etc/hosts"

    print()
    print(f"{KEYCLOAK_HOST} does not resolve on this machine.")
    print(f"Add this line to {hosts_file}:")
    print(f"127.0.0.1 {KEYCLOAK_HOST}")


def _create_local_certificates(
    mkcert: str,
    server_certificate: Path,
    server_private_key: Path,
) -> None:
    _run([mkcert, "-install"])
    _run(
        [
            mkcert,
            "-cert-file",
            str(server_certificate),
            "-key-file",
            str(server_private_key),
            KEYCLOAK_HOST,
        ]
    )

    ca_root = Path(_run([mkcert, "-CAROOT"], capture_output=True))
    copy_public_ca(ca_root, CA_CERT_DIRECTORY)


def main() -> int:
    mkcert = shutil.which("mkcert")
    if mkcert is None:
        print("mkcert is required. Install it, then run this command again.")
        return 1

    SERVER_CERT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    CA_CERT_DIRECTORY.mkdir(parents=True, exist_ok=True)

    server_certificate = SERVER_CERT_DIRECTORY / "keycloak.pem"
    server_private_key = SERVER_CERT_DIRECTORY / "keycloak-key.pem"

    try:
        _create_local_certificates(
            mkcert,
            server_certificate,
            server_private_key,
        )
    except (OSError, subprocess.CalledProcessError, RuntimeError) as error:
        print(f"Unable to create local Keycloak certificates: {error}")
        return 1

    if os.name != "nt":
        server_private_key.chmod(0o600)

    print(f"Created a trusted certificate for https://{KEYCLOAK_HOST}:8443")
    if not _hostname_resolves():
        _print_hosts_file_help()

    return 0


if __name__ == "__main__":
    sys.exit(main())
