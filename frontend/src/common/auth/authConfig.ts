import { Configuration, PopupRequest } from "@azure/msal-browser";

export const msalConfig: Configuration = {
  auth: {
    clientId: import.meta.env.VITE_AZURE_CLIENT_ID || "your-client-id", // Client ID from Azure App Registration
    authority:
      import.meta.env.VITE_AZURE_AUTHORITY ||
      "https://login.microsoftonline.com/common", // Tenant/Authority URL
    redirectUri:
      import.meta.env.VITE_AZURE_REDIRECT_URI || window.location.origin, // Redirect URI
    postLogoutRedirectUri:
      import.meta.env.VITE_AZURE_POST_LOGOUT_REDIRECT_URI ||
      window.location.origin, // Post logout redirect URI
  },
  cache: {
    cacheLocation: "sessionStorage", // This configures where your cache will be stored
    storeAuthStateInCookie: false, // Set this to "true" if you are having issues on IE11 or Edge
  },
};

// Add scopes here for ID token to be used at UserInfo endpoint
export const loginRequest: PopupRequest = {
  scopes: ["openid", "profile", "email"],
};

// Graph API scopes - adjust based on your needs
export const graphConfig = {
  graphMeEndpoint: "https://graph.microsoft.com/v1.0/me",
};
