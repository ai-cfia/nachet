export type AuthProviderKind = "msal" | "oidc";

export interface NachetAuthAccount {
  username: string;
  name?: string;
  idTokenClaims?: Record<string, unknown>;
}

export interface NachetAuthContextValue {
  provider: AuthProviderKind;
  isAuthenticated: boolean;
  isLoading: boolean;
  accounts: NachetAuthAccount[];
  activeAccount: NachetAuthAccount | null;
  login: (scopes?: string[]) => Promise<void>;
  logout: () => Promise<void>;
  getAccessToken: (scopes?: string[]) => Promise<string>;
}
