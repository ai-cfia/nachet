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
  NachetAuthTokenOptions,
} from "../NachetAuthContext";

interface MsalAuthProviderProps {
  apiScopeClaim: string;
  authContext: Context<NachetAuthContextValue | undefined>;
  children: ReactNode;
}

const mapAccount = (account: AccountInfo): NachetAuthAccount => {
  const idTokenClaims = account.idTokenClaims as
    | Record<string, unknown>
    | undefined;
  const oidClaim = idTokenClaims?.oid;
  const subClaim = idTokenClaims?.sub;
  const acctClaim = idTokenClaims?.acct;

  return {
    username: account.username,
    name: account.name,
    userId:
      typeof oidClaim === "string"
        ? oidClaim
        : typeof subClaim === "string"
          ? subClaim
          : account.localAccountId,
    // Default to guest unless Entra explicitly marks the account as a member.
    // Longer term, backend auth or configured claim mapping may own this.
    isGuest: acctClaim !== 0,
    idTokenClaims,
  };
};

export const MsalAuthProvider = ({
  apiScopeClaim,
  authContext,
  children,
}: MsalAuthProviderProps) => {
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
    async (
      scopes = defaultScopes,
      options?: NachetAuthTokenOptions,
    ): Promise<string> => {
      return acquireAccessToken(instance, scopes, options);
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
};
