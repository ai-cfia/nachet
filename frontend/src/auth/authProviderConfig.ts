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
