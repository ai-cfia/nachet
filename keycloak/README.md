# Local Keycloak configuration

Nachet imports `nachet-realm.json` when the local Keycloak container starts.
The realm contains a public browser client, a bearer-only API client, an API
audience mapper, and two local users.

The main configuration choices are:

- Keycloak serves HTTPS directly with the certificate created by
  `setup_local_tls.sh`.
- `KC_HOSTNAME` fixes the public issuer at
  `https://keycloak.localhost:8443`.
- The frontend client uses the authorization code flow with PKCE S256. It has
  no client secret and cannot use the direct password grant.
- The API client is bearer-only. The audience mapper adds `nachet-api` to
  access tokens requested by the frontend.
- `sslRequired` is set to `all` because the local provider does not allow an
  HTTP authentication path.
- Compose overrides the container user with the developer's UID and keeps group
  `0`, which is the group used by the official Keycloak image. The UID lets
  Keycloak read the bind-mounted private key without changing its `0600` mode;
  group `0` keeps Keycloak's own group-writable directories usable.

See the official Keycloak documentation for the underlying settings:

- [Configuring TLS](https://www.keycloak.org/server/enabletls)
- [Configuring the hostname](https://www.keycloak.org/server/hostname)
- [Importing a realm during startup](https://www.keycloak.org/server/importExport#importing-a-realm-during-startup)
- [Securing applications with OpenID Connect](https://www.keycloak.org/securing-apps/oidc-layers)
- [Official Keycloak container image](https://github.com/keycloak/keycloak/blob/26.7.0/quarkus/container/Dockerfile)
- [Docker bind mounts](https://docs.docker.com/engine/storage/bind-mounts/)
- [Docker Compose `user` setting](https://docs.docker.com/reference/compose-file/services/#user)
- [Docker Compose environment precedence](https://docs.docker.com/compose/how-tos/environment-variables/envvars-precedence/)

Compose's `environment` section takes precedence over `env_file`. For that
reason, `OIDC_CA_BUNDLE` stays in the backend environment file instead of being
set by `docker-compose.yaml`. Each provider can use its own CA bundle, or omit
the setting to use the normal public trust store.

`verify_local_setup.sh` checks Keycloak's certificate, discovery document,
redirect URIs, and browser origins. It does not sign in to Nachet. Complete the
browser checks in the developer guide to verify the full application flow.

The full setup and sign-in steps are in the
[developer guide](../DEVELOPER.md#local-keycloak).
