import { useCallback, useLayoutEffect, type ReactNode } from "react";
import { type PublicClientApplication } from "@azure/msal-browser";
import { MsalProvider } from "@azure/msal-react";
import {
  NachetAuthContext,
  useNachetAuth,
  type NachetAuthTokenOptions,
} from "./NachetAuthContext";
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

  // API and log requests use the provider's default API scope.
  const getApiAccessToken = useCallback(
    (options?: NachetAuthTokenOptions) => getAccessToken(undefined, options),
    [getAccessToken],
  );

  useLayoutEffect(() => {
    // Install before child useEffect API calls run on mount.
    initializeApi(getApiAccessToken);
    errorLogger.setTokenProvider(getApiAccessToken);

    return () => {
      clearApiAuthentication();
      errorLogger.setTokenProvider(null);
    };
  }, [getApiAccessToken]);

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
