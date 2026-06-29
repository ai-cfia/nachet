import type { AuthProviderKind } from "./NachetAuthContext";

export const getConfiguredAuthProvider = (): AuthProviderKind => {
  const configuredProvider =
    import.meta.env.VITE_AUTH_PROVIDER?.trim().toLowerCase();

  switch (configuredProvider) {
    case "msal":
    case "oidc":
      return configuredProvider;
    default:
      throw new Error('VITE_AUTH_PROVIDER must be set to "msal" or "oidc".');
  }
};

export const getApiScopeClaim = (): string => {
  const configuredProvider = getConfiguredAuthProvider();
  const azureApiScopeClaim =
    (import.meta.env.VITE_AZURE_APP_ID_URI ?? "") +
    (import.meta.env.VITE_AZURE_API_SCOPE_CLAIM ?? "");
  const oidcApiScopeClaim = import.meta.env.VITE_OIDC_API_SCOPE_CLAIM?.trim();

  return configuredProvider === "oidc" && oidcApiScopeClaim
    ? oidcApiScopeClaim
    : azureApiScopeClaim;
};
