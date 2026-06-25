import { createContext, useContext } from "react";

export type AuthProviderKind = "msal" | "oidc";

export interface NachetAuthAccount {
  username: string;
  name?: string;
  userId: string;
  isGuest: boolean;
  idTokenClaims?: Record<string, unknown>;
}

export interface NachetAuthTokenOptions {
  forceRefresh?: boolean;
}

export interface NachetAuthContextValue {
  provider: AuthProviderKind;
  isAuthenticated: boolean;
  isLoading: boolean;
  accounts: NachetAuthAccount[];
  activeAccount: NachetAuthAccount | null;
  login: (scopes?: string[]) => Promise<void>;
  logout: () => Promise<void>;
  getAccessToken: (
    scopes?: string[],
    options?: NachetAuthTokenOptions,
  ) => Promise<string>;
}

export const NachetAuthContext = createContext<
  NachetAuthContextValue | undefined
>(undefined);

export const useNachetAuth = (): NachetAuthContextValue => {
  const context = useContext(NachetAuthContext);
  if (!context) {
    throw new Error("useNachetAuth must be used within NachetAuthProvider");
  }
  return context;
};
