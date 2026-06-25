import { useEffect, type ReactNode } from "react";
import { type PublicClientApplication } from "@azure/msal-browser";
import { MsalProvider } from "@azure/msal-react";
import { NachetAuthContext, useNachetAuth } from "./NachetAuthContext";
import { MsalAuthProvider } from "./msal/MsalAuthProvider";
import { OidcAuthProvider } from "./oidc/OidcAuthProvider";
import { getConfiguredAuthProvider } from "./authProviderConfig";
import { clearApiAuthentication, initializeApi } from "../common/api";
import { errorLogger } from "../logging";

export interface NachetAuthProviderProps {
  apiScopeClaim: string;
  children: ReactNode;
  msalInstance?: PublicClientApplication;
}

const AuthApiBridge = () => {
  const { getAccessToken } = useNachetAuth();

  useEffect(() => {
    initializeApi((options) => getAccessToken(undefined, options));
    errorLogger.setTokenProvider(async () => getAccessToken());

    return () => {
      clearApiAuthentication();
      errorLogger.setTokenProvider(async () => null);
    };
  }, [getAccessToken]);

  return null;
};

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
            <AuthApiBridge />
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
          <AuthApiBridge />
          {children}
        </OidcAuthProvider>
      );
  }
};
