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

See the official Keycloak documentation for the underlying settings:

- [Configuring TLS](https://www.keycloak.org/server/enabletls)
- [Configuring the hostname](https://www.keycloak.org/server/hostname)
- [Importing a realm during startup](https://www.keycloak.org/server/importExport#importing-a-realm-during-startup)
- [Securing applications with OpenID Connect](https://www.keycloak.org/securing-apps/oidc-layers)

The full setup and sign-in steps are in the
[developer guide](../DEVELOPER.md#local-keycloak).
