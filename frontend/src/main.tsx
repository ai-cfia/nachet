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
import { ThemeProvider } from "@mui/material/styles";
import { createEmotionCache } from "./common/emotionCache";
import { ErrorBoundary } from "@components/body/index.ts";
import { theme } from "./theme";
import { resetAuthRedirectFlag } from "./common/auth";
import "./i18n";
import "./locales/types"; // Import TypeScript type definitions for i18n

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

const basename = process.env.REACT_APP_BASENAME ?? "/";
const apiScopeClaim =
  (import.meta.env.VITE_AZURE_APP_ID_URI ?? "") +
  (import.meta.env.VITE_AZURE_API_SCOPE_CLAIM ?? "");
const configuredAuthProvider = (import.meta.env.VITE_AUTH_PROVIDER ?? "msal")
  .trim()
  .toLowerCase();

console.log("Azure API Scope Claim: ", apiScopeClaim);

const renderApp = (msalClient?: PublicClientApplication): void => {
  const emotionCache = createEmotionCache();

  ReactDOM.createRoot(document.getElementById("root")!).render(
    <React.StrictMode>
      <ThemeProvider theme={theme}>
        <CacheProvider value={emotionCache}>
          <ErrorBoundary>
            <App
              msalInstance={msalClient}
              basename={basename}
              apiScopeClaim={apiScopeClaim}
            />
          </ErrorBoundary>
        </CacheProvider>
      </ThemeProvider>
    </React.StrictMode>,
  );
};

const initializeMsalAndRender = async (): Promise<void> => {
  const msalInstance = new PublicClientApplication(msalConfig);

  try {
    await msalInstance.initialize();
    const response = await msalInstance.handleRedirectPromise();

    if (response) {
      // Set the active account after successful redirect
      msalInstance.setActiveAccount(response.account);
      // Reset redirect flags to allow future redirects if needed
      resetAuthRedirectFlag(); // For auth.ts
    } else {
      // Check if we have any cached accounts
      const accounts = msalInstance.getAllAccounts();
      if (accounts.length > 0) {
        msalInstance.setActiveAccount(accounts[0]);
      }
    }

    renderApp(msalInstance);
  } catch (error) {
    console.error("Error initializing MSAL:", error);

    // Still render the app even if there's an error, so user can see auth popup
    renderApp(msalInstance);
  }
};

if (configuredAuthProvider === "msal") {
  void initializeMsalAndRender();
} else {
  renderApp();
}
