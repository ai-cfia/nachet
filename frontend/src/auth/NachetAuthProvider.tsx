import { type ReactNode } from "react";
import { NachetAuthContext } from "./NachetAuthContext";
import { MsalAuthProvider } from "./msal/MsalAuthProvider";
import { OidcAuthProvider } from "./oidc/OidcAuthProvider";

export interface NachetAuthProviderProps {
  apiScopeClaim: string;
  children: ReactNode;
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
        {children}
      </OidcAuthProvider>
    );
  }

  throw new Error(
    `Unsupported auth provider '${configuredProvider}'. Use 'msal' or 'oidc'.`,
  );
}
