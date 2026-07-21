/*
 * Borrowed and adapted from these react-oidc-context files:
 * https://github.com/authts/react-oidc-context/blob/80e60ae0b538afdb6e0be7016ec3430104b1bf42/src/AuthProvider.tsx
 * https://github.com/authts/react-oidc-context/blob/80e60ae0b538afdb6e0be7016ec3430104b1bf42/src/AuthState.ts
 * https://github.com/authts/react-oidc-context/blob/80e60ae0b538afdb6e0be7016ec3430104b1bf42/src/utils.ts
 *
 * Original project is MIT licensed. See LICENSE in this directory.
 */
import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
  UserManager,
  type SigninRedirectArgs,
  type SigninSilentArgs,
  type SignoutRedirectArgs,
  type User,
  type UserManagerSettings,
} from "oidc-client-ts";
import { AuthContext } from "./AuthContext";

interface AuthState {
  isLoading: boolean;
  isAuthenticated: boolean;
  user: User | null;
  error: Error | null;
}

const initialAuthState: AuthState = {
  isLoading: true,
  isAuthenticated: false,
  user: null,
  error: null,
};

interface AuthProviderProps extends UserManagerSettings {
  children: ReactNode;
  skipSigninCallback?: boolean;
  onSigninCallback?: (user: User | null) => Promise<void> | void;
}

const hasAuthParams = (location = window.location): boolean => {
  const searchParams = new URLSearchParams(location.search);
  const hashParams = new URLSearchParams(location.hash.replace(/^#/, ""));

  return (
    ((searchParams.has("code") || searchParams.has("error")) &&
      searchParams.has("state")) ||
    ((hashParams.has("code") || hashParams.has("error")) &&
      hashParams.has("state"))
  );
};

const toError = (error: unknown): Error => {
  if (error instanceof Error) {
    return error;
  }

  return new Error(typeof error === "string" ? error : JSON.stringify(error));
};

export const AuthProvider = ({
  children,
  skipSigninCallback = false,
  onSigninCallback,
  ...settings
}: AuthProviderProps) => {
  const [userManager] = useState(() => new UserManager(settings));
  const [state, setState] = useState<AuthState>(initialAuthState);
  const didInitialize = useRef(false);

  useEffect(() => {
    // React StrictMode replays effects in development. An authorization code
    // can only be exchanged once, so initialization must run once per mount.
    if (didInitialize.current) {
      return;
    }
    didInitialize.current = true;

    const initialise = async (): Promise<void> => {
      try {
        let user: User | null | undefined;

        if (hasAuthParams() && !skipSigninCallback) {
          user = await userManager.signinCallback();
          await onSigninCallback?.(user ?? null);
        } else {
          user = await userManager.getUser();
        }

        const authenticatedUser = user ?? null;

        setState({
          isLoading: false,
          isAuthenticated: Boolean(
            authenticatedUser && !authenticatedUser.expired,
          ),
          user: authenticatedUser,
          error: null,
        });
      } catch (error) {
        setState({
          isLoading: false,
          isAuthenticated: false,
          user: null,
          error: toError(error),
        });
      }
    };

    void initialise();
  }, [onSigninCallback, skipSigninCallback, userManager]);

  useEffect(() => {
    const removeUserLoaded = userManager.events.addUserLoaded((user) => {
      setState({
        isLoading: false,
        isAuthenticated: !user.expired,
        user,
        error: null,
      });
    });
    const removeUserUnloaded = userManager.events.addUserUnloaded(() => {
      setState({
        isLoading: false,
        isAuthenticated: false,
        user: null,
        error: null,
      });
    });
    const removeUserSignedOut = userManager.events.addUserSignedOut(() => {
      setState({
        isLoading: false,
        isAuthenticated: false,
        user: null,
        error: null,
      });
    });
    const removeSilentRenewError = userManager.events.addSilentRenewError(
      (error) => {
        setState((currentState) => ({
          ...currentState,
          error,
        }));
      },
    );

    return () => {
      removeUserLoaded();
      removeUserUnloaded();
      removeUserSignedOut();
      removeSilentRenewError();
    };
  }, [userManager]);

  const value = useMemo(
    () => ({
      ...state,
      settings: userManager.settings,
      events: userManager.events,
      signinRedirect: (args?: SigninRedirectArgs) =>
        userManager.signinRedirect(args),
      signinSilent: (args?: SigninSilentArgs) => userManager.signinSilent(args),
      signoutRedirect: (args?: SignoutRedirectArgs) =>
        userManager.signoutRedirect(args),
      removeUser: () => userManager.removeUser(),
      clearStaleState: () => userManager.clearStaleState(),
    }),
    [state, userManager],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
