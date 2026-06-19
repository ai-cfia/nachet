import {
  useCallback,
  useEffect,
  useMemo,
  type Context,
  type ReactNode,
} from "react";
import { InteractionStatus, type AccountInfo } from "@azure/msal-browser";
import { useIsAuthenticated, useMsal } from "@azure/msal-react";
import { acquireAccessToken } from "../../common/auth";
import type {
  NachetAuthAccount,
  NachetAuthContextValue,
} from "../NachetAuthContext";

interface MsalAuthProviderProps {
  apiScopeClaim: string;
  authContext: Context<NachetAuthContextValue | undefined>;
  children: ReactNode;
}

function mapAccount(account: AccountInfo): NachetAuthAccount {
  return {
    username: account.username,
    name: account.name,
    idTokenClaims: account.idTokenClaims as Record<string, unknown> | undefined,
  };
}

export function MsalAuthProvider({
  apiScopeClaim,
  authContext,
  children,
}: MsalAuthProviderProps) {
  const { instance, inProgress, accounts } = useMsal();
  const isAuthenticated = useIsAuthenticated();
  const defaultScopes = useMemo(
    () => (apiScopeClaim ? [apiScopeClaim] : []),
    [apiScopeClaim],
  );

  useEffect(() => {
    if (accounts.length > 0 && !instance.getActiveAccount()) {
      instance.setActiveAccount(accounts[0]);
    }
  }, [accounts, instance]);

  const login = useCallback(
    async (scopes = defaultScopes): Promise<void> => {
      if (inProgress !== InteractionStatus.None) {
        console.warn("Interaction already in progress, please wait");
        return;
      }

      await instance.loginRedirect({ scopes });
    },
    [defaultScopes, inProgress, instance],
  );

  const logout = useCallback(async (): Promise<void> => {
    await instance.logoutRedirect();
  }, [instance]);

  const getAccessToken = useCallback(
    async (scopes = defaultScopes): Promise<string> => {
      return acquireAccessToken(instance, scopes);
    },
    [defaultScopes, instance],
  );

  const activeMsalAccount = instance.getActiveAccount() ?? accounts[0] ?? null;
  const value = useMemo<NachetAuthContextValue>(
    () => ({
      provider: "msal",
      isAuthenticated,
      isLoading: inProgress !== InteractionStatus.None,
      accounts: accounts.map(mapAccount),
      activeAccount: activeMsalAccount ? mapAccount(activeMsalAccount) : null,
      login,
      logout,
      getAccessToken,
    }),
    [
      accounts,
      activeMsalAccount,
      getAccessToken,
      inProgress,
      isAuthenticated,
      login,
      logout,
    ],
  );

  const Provider = authContext.Provider;

  return <Provider value={value}>{children}</Provider>;
}
