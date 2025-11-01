import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.tsx";
import "./index.css";
import {
  Configuration,
  PublicClientApplication,
  LogLevel,
} from "@azure/msal-browser";
import { CacheProvider } from "@emotion/react";
import { createEmotionCache } from "./common/emotionCache";
import { ErrorBoundary } from "@components/body/index.ts";
import { errorLogger } from "./logging";
import {
  acquireAccessToken,
  shouldTriggerRedirect,
  resetAuthRedirectFlag,
} from "./common/auth";
import { initializeApi, resetRedirectFlag } from "./common/api";

const msalConfig: Configuration = {
  auth: {
    clientId: import.meta.env.VITE_AZURE_CLIENT_ID || "your-client-id", // Client ID from Azure App Registration
    authority:
      import.meta.env.VITE_AZURE_AUTHORITY ||
      "https://login.microsoftonline.com/common", // Tenant/Authority URL
    redirectUri: window.location.origin + window.location.pathname, // Include pathname for HashRouter compatibility
    postLogoutRedirectUri:
      import.meta.env.VITE_AZURE_POST_LOGOUT_REDIRECT_URI ||
      window.location.origin, // Post logout redirect URI
    navigateToLoginRequestUrl: true, // Navigate back to the page that initiated login
  },
  cache: {
    cacheLocation: "sessionStorage",
  },
  system: {
    loggerOptions: {
      logLevel: LogLevel.Error,
      loggerCallback: (
        level: LogLevel,
        message: string,
        containsPii: boolean,
      ): void => {
        if (containsPii) {
          return;
        }
        switch (level) {
          case LogLevel.Error:
            console.error(message);
            return;
          case LogLevel.Info:
            console.info(message);
            return;
          case LogLevel.Verbose:
            console.debug(message);
            return;
          case LogLevel.Warning:
            console.warn(message);
            return;
        }
      },
      piiLoggingEnabled: false,
    },
    // windowHashTimeout: 60000,
    // iframeHashTimeout: 6000,
    // loadFrameTimeout: 0,
    // asyncPopups: false,
  },
};

const msalInstance = new PublicClientApplication(msalConfig);
const basename = process.env.REACT_APP_BASENAME ?? "/";
const apiScopeClaim =
  (import.meta.env.VITE_AZURE_APP_ID_URI ?? "") +
  (import.meta.env.VITE_AZURE_API_SCOPE_CLAIM ?? "");

console.log("Azure API Scope Claim: ", apiScopeClaim);

// Initialize MSAL and handle redirect promise before rendering app
// This is critical for processing OAuth callbacks from Azure AD
msalInstance
  .initialize()
  .then(() => {
    return msalInstance.handleRedirectPromise();
  })
  .then((response) => {
    if (response) {
      // Set the active account after successful redirect
      msalInstance.setActiveAccount(response.account);
      // Reset redirect flags to allow future redirects if needed
      resetRedirectFlag(); // For axios interceptor
      resetAuthRedirectFlag(); // For auth.ts
    } else {
      // Check if we have any cached accounts
      const accounts = msalInstance.getAllAccounts();
      if (accounts.length > 0) {
        msalInstance.setActiveAccount(accounts[0]);
      }
    }

    // Initialize axios interceptor for authentication
    const scopes = apiScopeClaim ? [apiScopeClaim] : [];
    initializeApi(msalInstance, scopes);

    // Set up token provider for error logger
    errorLogger.setTokenProvider(async () => {
      try {
        const token = await acquireAccessToken(msalInstance, scopes);
        return token;
      } catch (error) {
        // Check if error requires redirect
        if (shouldTriggerRedirect(error)) {
          console.error(
            "Error logger: Token acquisition failed. Redirecting to login...",
          );
          // Trigger redirect authentication
          const activeAccount = msalInstance.getActiveAccount();
          const accounts = msalInstance.getAllAccounts();
          if (activeAccount || accounts.length > 0) {
            await msalInstance.acquireTokenRedirect({
              scopes,
              account: activeAccount || accounts[0],
            });
          }
        }
        // If token acquisition fails, return null (logs will be sent without auth)
        console.warn("Failed to acquire token for error logger:", error);
        return null;
      }
    });

    // Create Emotion cache with CSP nonce support
    const emotionCache = createEmotionCache();

    // Render app after MSAL is initialized
    ReactDOM.createRoot(document.getElementById("root")!).render(
      <React.StrictMode>
        <CacheProvider value={emotionCache}>
          <ErrorBoundary>
            <App
              msalInstance={msalInstance}
              basename={basename}
              apiScopeClaim={apiScopeClaim}
            />
          </ErrorBoundary>
        </CacheProvider>
      </React.StrictMode>,
    );
  })
  .catch((error) => {
    console.error("Error initializing MSAL:", error);

    // Still render the app even if there's an error, so user can see auth popup
    const emotionCache = createEmotionCache();
    ReactDOM.createRoot(document.getElementById("root")!).render(
      <React.StrictMode>
        <CacheProvider value={emotionCache}>
          <ErrorBoundary>
            <App
              msalInstance={msalInstance}
              basename={basename}
              apiScopeClaim={apiScopeClaim}
            />
          </ErrorBoundary>
        </CacheProvider>
      </React.StrictMode>,
    );
  });
