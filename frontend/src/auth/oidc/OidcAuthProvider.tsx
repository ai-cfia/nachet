import { useCallback, useMemo } from "react";
import {
  WebStorageStateStore,
  type User,
  type UserManagerSettings,
} from "oidc-client-ts";
import type { NachetAuthContextValue } from "../types";
import { AuthProvider } from "./react-oidc-context/AuthProvider";
import { useAuth as useOidcAuth } from "./react-oidc-context/useAuth";

interface OidcAuthProviderProps {
  apiScopeClaim: string;
  authContext: React.Context<NachetAuthContextValue | undefined>;
  children: React.ReactNode;
}

function requiredEnv(name: string): string {
  const value = (import.meta.env as Record<string, string | undefined>)[
    name
  ]?.trim();

  if (!value) {
    throw new Error(`${name} is required by the OIDC auth adapter.`);
  }

  return value;
}

function optionalEnv(name: string): string | undefined {
  const value = (import.meta.env as Record<string, string | undefined>)[
    name
  ]?.trim();
  return value || undefined;
}

function buildScope(baseScope: string, requestedScopes?: string[]): string {
  const scopes = new Set(
    baseScope
      .split(/\s+/)
      .map((scope) => scope.trim())
      .filter(Boolean),
  );

  requestedScopes?.forEach((scope) => {
    if (scope.trim()) {
      scopes.add(scope.trim());
    }
  });

  return Array.from(scopes).join(" ");
}

function getStringClaim(
  profile: Record<string, unknown>,
  claimNames: string[],
): string | undefined {
  return claimNames
    .map((claimName) => profile[claimName])
    .find((claimValue): claimValue is string => typeof claimValue === "string");
}

function mapUser(user: User | null) {
  if (user === null) {
    return null;
  }

  const profile = user.profile as Record<string, unknown>;
  const username =
    getStringClaim(profile, ["preferred_username", "email", "sub"]) ??
    "unknown";
  const name = getStringClaim(profile, ["name"]) ?? username;

  return {
    username,
    name,
    idTokenClaims: profile,
  };
}

function OidcAuthBridge({
  apiScopeClaim,
  authContext,
  children,
}: OidcAuthProviderProps) {
  const oidc = useOidcAuth();
  const defaultScope = useMemo(() => {
    return (
      optionalEnv("VITE_OIDC_SCOPE") ??
      buildScope("openid profile email", apiScopeClaim ? [apiScopeClaim] : [])
    );
  }, [apiScopeClaim]);

  const activeAccount = useMemo(() => mapUser(oidc.user), [oidc.user]);

  const login = useCallback(
    async (scopes?: string[]) => {
      await oidc.signinRedirect({ scope: buildScope(defaultScope, scopes) });
    },
    [defaultScope, oidc],
  );

  const logout = useCallback(async () => {
    await oidc.signoutRedirect();
  }, [oidc]);

  const getAccessToken = useCallback(
    async (scopes?: string[]) => {
      if (oidc.user?.access_token && !oidc.user.expired) {
        return oidc.user.access_token;
      }

      const renewedUser = await oidc.signinSilent({
        scope: buildScope(defaultScope, scopes),
      });

      if (renewedUser?.access_token && !renewedUser.expired) {
        return renewedUser.access_token;
      }

      await login(scopes);
      throw new Error("Redirecting to sign in for a fresh OIDC access token.");
    },
    [defaultScope, login, oidc],
  );

  const authValue = useMemo<NachetAuthContextValue>(
    () => ({
      provider: "oidc",
      isAuthenticated: oidc.isAuthenticated,
      isLoading: oidc.isLoading,
      accounts: activeAccount ? [activeAccount] : [],
      activeAccount,
      login,
      logout,
      getAccessToken,
    }),
    [
      activeAccount,
      getAccessToken,
      login,
      logout,
      oidc.isAuthenticated,
      oidc.isLoading,
    ],
  );

  const Provider = authContext.Provider;
  return <Provider value={authValue}>{children}</Provider>;
}

function getOidcSettings(apiScopeClaim: string): UserManagerSettings {
  const baseScope =
    optionalEnv("VITE_OIDC_SCOPE") ??
    buildScope("openid profile email", apiScopeClaim ? [apiScopeClaim] : []);

  return {
    authority: requiredEnv("VITE_OIDC_AUTHORITY"),
    client_id: requiredEnv("VITE_OIDC_CLIENT_ID"),
    redirect_uri:
      optionalEnv("VITE_OIDC_REDIRECT_URI") ??
      window.location.origin + window.location.pathname,
    post_logout_redirect_uri:
      optionalEnv("VITE_OIDC_POST_LOGOUT_REDIRECT_URI") ??
      window.location.origin + window.location.pathname,
    response_type: "code",
    scope: baseScope,
    userStore: new WebStorageStateStore({ store: window.sessionStorage }),
    automaticSilentRenew: Boolean(optionalEnv("VITE_OIDC_SILENT_REDIRECT_URI")),
    silent_redirect_uri: optionalEnv("VITE_OIDC_SILENT_REDIRECT_URI"),
  };
}

export function OidcAuthProvider(props: OidcAuthProviderProps) {
  const settings = useMemo(
    () => getOidcSettings(props.apiScopeClaim),
    [props.apiScopeClaim],
  );

  const onSigninCallback = useCallback(() => {
    const cleanUrl = `${window.location.pathname}${window.location.hash || ""}`;
    window.history.replaceState({}, document.title, cleanUrl);
  }, []);

  return (
    <AuthProvider {...settings} onSigninCallback={onSigninCallback}>
      <OidcAuthBridge {...props} />
    </AuthProvider>
  );
}
