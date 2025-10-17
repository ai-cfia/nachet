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
import { acquireAccessToken } from "./common/auth";

const msalConfig: Configuration = {
  auth: {
    clientId: import.meta.env.VITE_AZURE_CLIENT_ID || "your-client-id", // Client ID from Azure App Registration
    authority:
      import.meta.env.VITE_AZURE_AUTHORITY ||
      "https://login.microsoftonline.com/common", // Tenant/Authority URL
    redirectUri: window.location.origin, // Always use current origin for redirect
    // mainWindowRedirectUri: window.location.origin,
    postLogoutRedirectUri:
      import.meta.env.VITE_AZURE_POST_LOGOUT_REDIRECT_URI ||
      window.location.origin, // Post logout redirect URI
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

// Set up token provider for error logger
errorLogger.setTokenProvider(async () => {
  try {
    const scopes = apiScopeClaim ? [apiScopeClaim] : [];
    const token = await acquireAccessToken(msalInstance, scopes);
    return token;
  } catch (error) {
    // If token acquisition fails, return null (logs will be sent without auth)
    console.warn("Failed to acquire token for error logger:", error);
    return null;
  }
});

// Create Emotion cache with CSP nonce support
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
