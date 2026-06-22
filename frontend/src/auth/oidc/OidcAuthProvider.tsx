import { useCallback, useMemo, type Context, type ReactNode } from "react";
import {
  WebStorageStateStore,
  type User,
  type UserManagerSettings,
} from "oidc-client-ts";
import type { NachetAuthContextValue } from "../NachetAuthContext";
import { AuthProvider } from "./react-oidc-context/AuthProvider";
import { useAuth as useOidcAuth } from "./react-oidc-context/useAuth";

interface OidcAuthProviderProps {
  apiScopeClaim: string;
  authContext: Context<NachetAuthContextValue | undefined>;
  children: ReactNode;
}

interface OidcEnv {
  authority: string;
  clientId: string;
  scope: string;
  redirectUri: string;
  postLogoutRedirectUri: string;
}

interface OidcAuthBridgeProps extends OidcAuthProviderProps {
  defaultScope: string;
}

const getOidcEnv = (): OidcEnv => {
  const oidcEnv = {
    authority: import.meta.env.VITE_OIDC_AUTHORITY?.trim() ?? "",
    clientId: import.meta.env.VITE_OIDC_CLIENT_ID?.trim() ?? "",
    scope: import.meta.env.VITE_OIDC_SCOPE?.trim() ?? "",
    redirectUri: import.meta.env.VITE_OIDC_REDIRECT_URI?.trim() ?? "",
    postLogoutRedirectUri:
      import.meta.env.VITE_OIDC_POST_LOGOUT_REDIRECT_URI?.trim() ?? "",
  };

  const missingEnv = [
    ["VITE_OIDC_AUTHORITY", oidcEnv.authority],
    ["VITE_OIDC_CLIENT_ID", oidcEnv.clientId],
    ["VITE_OIDC_SCOPE", oidcEnv.scope],
    ["VITE_OIDC_REDIRECT_URI", oidcEnv.redirectUri],
    ["VITE_OIDC_POST_LOGOUT_REDIRECT_URI", oidcEnv.postLogoutRedirectUri],
  ]
    .filter(([, value]) => !value)
    .map(([name]) => name);

  if (missingEnv.length > 0) {
    throw new Error(
      `Missing required OIDC auth configuration: ${missingEnv.join(", ")}`,
    );
  }

  return oidcEnv;
};

interface OidcConfig {
  defaultScope: string;
  settings: UserManagerSettings;
}

const buildScope = (baseScope: string, requestedScopes?: string[]): string => {
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
};

const getStringClaim = (
  profile: Record<string, unknown>,
  claimNames: string[],
): string | undefined => {
  return claimNames
    .map((claimName) => profile[claimName])
    .find((claimValue): claimValue is string => typeof claimValue === "string");
};

const mapUser = (user: User | null) => {
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
};

const OidcAuthBridge = ({
  authContext,
  children,
  defaultScope,
}: OidcAuthBridgeProps) => {
  const oidc = useOidcAuth();
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

      await login(scopes);
      throw new Error("Redirecting to sign in for a fresh OIDC access token.");
    },
    [login, oidc],
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
};

const getOidcConfig = (apiScopeClaim: string): OidcConfig => {
  const oidcEnv = getOidcEnv();
  const defaultScope = buildScope(
    oidcEnv.scope,
    apiScopeClaim ? [apiScopeClaim] : [],
  );

  return {
    defaultScope,
    settings: {
      authority: oidcEnv.authority,
      client_id: oidcEnv.clientId,
      redirect_uri: oidcEnv.redirectUri,
      post_logout_redirect_uri: oidcEnv.postLogoutRedirectUri,
      response_type: "code",
      scope: defaultScope,
      userStore: new WebStorageStateStore({ store: window.sessionStorage }),
      automaticSilentRenew: false,
    },
  };
};

export const OidcAuthProvider = (props: OidcAuthProviderProps) => {
  const oidcConfig = useMemo(
    () => getOidcConfig(props.apiScopeClaim),
    [props.apiScopeClaim],
  );

  const onSigninCallback = useCallback(() => {
    const cleanUrl = `${window.location.pathname}${window.location.hash || ""}`;
    window.history.replaceState({}, document.title, cleanUrl);
  }, []);

  return (
    <AuthProvider {...oidcConfig.settings} onSigninCallback={onSigninCallback}>
      <OidcAuthBridge {...props} defaultScope={oidcConfig.defaultScope} />
    </AuthProvider>
  );
};
