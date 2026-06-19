import { useEffect, type ReactNode } from "react";
import { NachetAuthContext, useNachetAuth } from "./NachetAuthContext";
import { MsalAuthProvider } from "./msal/MsalAuthProvider";
import { OidcAuthProvider } from "./oidc/OidcAuthProvider";
import { initializeApi } from "../common/api";
import { errorLogger } from "../logging";

export interface NachetAuthProviderProps {
  apiScopeClaim: string;
  children: ReactNode;
}

function AuthApiBridge() {
  const { getAccessToken } = useNachetAuth();

  useEffect(() => {
    initializeApi(getAccessToken);
    errorLogger.setTokenProvider(async () => getAccessToken());
  }, [getAccessToken]);

  return null;
}

export function NachetAuthProvider({
  apiScopeClaim,
  children,
}: NachetAuthProviderProps) {
  const configuredProvider = (import.meta.env.VITE_AUTH_PROVIDER ?? "msal")
    .trim()
    .toLowerCase();
  const oidcApiScopeClaim =
    import.meta.env.VITE_OIDC_API_SCOPE_CLAIM?.trim() || apiScopeClaim;

  if (configuredProvider === "msal") {
    return (
      <MsalAuthProvider
        apiScopeClaim={apiScopeClaim}
        authContext={NachetAuthContext}
      >
        <AuthApiBridge />
        {children}
      </MsalAuthProvider>
    );
  }

  if (configuredProvider === "oidc") {
    return (
      <OidcAuthProvider
        apiScopeClaim={oidcApiScopeClaim}
        authContext={NachetAuthContext}
      >
        <AuthApiBridge />
        {children}
      </OidcAuthProvider>
    );
  }

  throw new Error(
    `Unsupported auth provider '${configuredProvider}'. Use 'msal' or 'oidc'.`,
  );
}
