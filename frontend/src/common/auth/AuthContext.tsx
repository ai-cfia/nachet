import React, { createContext, useEffect, useState } from "react";
import { useMsal, useIsAuthenticated } from "@azure/msal-react";
import { AccountInfo } from "@azure/msal-browser";
import { AuthContextType } from "./useAuth";

// eslint-disable-next-line react-refresh/only-export-components
export const AuthContext = createContext<AuthContextType | undefined>(
  undefined,
);

interface AuthProviderProps {
  children: React.ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const { instance, accounts } = useMsal();
  const isAuthenticated = useIsAuthenticated();
  const [user, setUser] = useState<AccountInfo | null>(null);

  useEffect(() => {
    if (isAuthenticated && accounts.length > 0) {
      setUser(accounts[0]);
    } else {
      setUser(null);
    }
  }, [isAuthenticated, accounts]);

  const login = async (): Promise<void> => {
    try {
      await instance.loginPopup({
        scopes: ["openid", "profile", "email"],
      });
    } catch (error) {
      console.error("Login failed:", error);
      throw error;
    }
  };

  const logout = async (): Promise<void> => {
    try {
      await instance.logoutPopup();
    } catch (error) {
      console.error("Logout failed:", error);
      throw error;
    }
  };

  const getAccessToken = async (): Promise<string | null> => {
    if (!isAuthenticated || accounts.length === 0) {
      return null;
    }

    try {
      const response = await instance.acquireTokenSilent({
        scopes: ["openid", "profile", "email"],
        account: accounts[0],
      });
      return response.accessToken;
    } catch (error) {
      console.error("Token acquisition failed:", error);
      // If silent acquisition fails, try interactive
      try {
        const response = await instance.acquireTokenPopup({
          scopes: ["openid", "profile", "email"],
          account: accounts[0],
        });
        return response.accessToken;
      } catch (interactiveError) {
        console.error(
          "Interactive token acquisition failed:",
          interactiveError,
        );
        return null;
      }
    }
  };

  const contextValue: AuthContextType = {
    isAuthenticated,
    user,
    login,
    logout,
    getAccessToken,
  };

  return (
    <AuthContext.Provider value={contextValue}>{children}</AuthContext.Provider>
  );
};
