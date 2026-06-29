import { type ReactNode } from "react";
import { type PublicClientApplication } from "@azure/msal-browser";
import { MsalProvider } from "@azure/msal-react";
import { NachetAuthContext } from "./NachetAuthContext";
import { MsalAuthProvider } from "./msal/MsalAuthProvider";
import { OidcAuthProvider } from "./oidc/OidcAuthProvider";
import { getConfiguredAuthProvider } from "./authProviderConfig";

export interface NachetAuthProviderProps {
  apiScopeClaim: string;
  children: ReactNode;
  msalInstance?: PublicClientApplication;
}

export const NachetAuthProvider = ({
  apiScopeClaim,
  children,
  msalInstance,
}: NachetAuthProviderProps) => {
  const configuredProvider = getConfiguredAuthProvider();

  switch (configuredProvider) {
    case "msal":
      if (!msalInstance) {
        throw new Error("MSAL auth provider requires an MSAL instance.");
      }

      return (
        <MsalProvider instance={msalInstance}>
          <MsalAuthProvider
            apiScopeClaim={apiScopeClaim}
            authContext={NachetAuthContext}
          >
            {children}
          </MsalAuthProvider>
        </MsalProvider>
      );
    case "oidc":
      return (
        <OidcAuthProvider
          apiScopeClaim={apiScopeClaim}
          authContext={NachetAuthContext}
        >
          {children}
        </OidcAuthProvider>
      );
  }
};
