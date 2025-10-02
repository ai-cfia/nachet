import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App.tsx";
import "./index.css";
import { Configuration, PublicClientApplication } from "@azure/msal-browser";
// import { MsalProvider } from "@azure/msal-react";
// import { msalConfig } from "./common/auth/authConfig";
// import { AuthProvider } from "./common/auth/AuthContext";

const msalConfig: Configuration = {
  auth: {
    clientId: import.meta.env.VITE_AZURE_CLIENT_ID || "your-client-id", // Client ID from Azure App Registration
    authority:
      import.meta.env.VITE_AZURE_AUTHORITY ||
      "https://login.microsoftonline.com/common", // Tenant/Authority URL
    redirectUri:
      import.meta.env.VITE_AZURE_REDIRECT_URI || window.location.origin, // Redirect URI
    // mainWindowRedirectUri: window.location.origin,
    postLogoutRedirectUri:
      import.meta.env.VITE_AZURE_POST_LOGOUT_REDIRECT_URI ||
      window.location.origin, // Post logout redirect URI
  },
  cache: {
    cacheLocation: "memoryStorage", // Store tokens in memoryStorage for security and persistence during session
    storeAuthStateInCookie: true, // Store auth state in cookies for improved SSO experience
  },
};

const msalInstance = new PublicClientApplication(msalConfig);
const basename = process.env.REACT_APP_BASENAME ?? "/";
const apiScopeClaim =
  (import.meta.env.VITE_AZURE_APP_ID_URI ?? "") +
  (import.meta.env.VITE_AZURE_API_SCOPE_CLAIM ?? "");

console.log("Azure API Scope Claim: ", apiScopeClaim);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App
      msalInstance={msalInstance}
      basename={basename}
      apiScopeClaim={apiScopeClaim}
    />
  </React.StrictMode>,
);
