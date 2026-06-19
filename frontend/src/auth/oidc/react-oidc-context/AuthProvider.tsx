/*
 * Borrowed and adapted from react-oidc-context AuthProvider.tsx:
 * https://github.com/authts/react-oidc-context/blob/main/src/AuthProvider.tsx
 *
 * Original project is MIT licensed. See LICENSE in this directory.
 */
import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  UserManager,
  type SigninRedirectArgs,
  type SigninSilentArgs,
  type SignoutRedirectArgs,
  type User,
  type UserManagerSettings,
} from "oidc-client-ts";
import { AuthContext } from "./AuthContext";
import { initialAuthState, type AuthState } from "./AuthState";
import { hasAuthParams, toError } from "./utils";

interface AuthProviderProps extends UserManagerSettings {
  children: ReactNode;
  skipSigninCallback?: boolean;
  onSigninCallback?: (user: User | null) => Promise<void> | void;
}

export function AuthProvider({
  children,
  skipSigninCallback = false,
  onSigninCallback,
  ...settings
}: AuthProviderProps) {
  const managerSettings = useMemo<UserManagerSettings>(
    () => ({
      authority: settings.authority,
      client_id: settings.client_id,
      redirect_uri: settings.redirect_uri,
      post_logout_redirect_uri: settings.post_logout_redirect_uri,
      response_type: settings.response_type,
      scope: settings.scope,
      silent_redirect_uri: settings.silent_redirect_uri,
      automaticSilentRenew: settings.automaticSilentRenew,
      userStore: settings.userStore,
    }),
    [
      settings.authority,
      settings.client_id,
      settings.redirect_uri,
      settings.post_logout_redirect_uri,
      settings.response_type,
      settings.scope,
      settings.silent_redirect_uri,
      settings.automaticSilentRenew,
      settings.userStore,
    ],
  );
  const userManager = useMemo(
    () => new UserManager(managerSettings),
    [managerSettings],
  );
  const [state, setState] = useState<AuthState>(initialAuthState);

  useEffect(() => {
    let isMounted = true;

    const initialise = async (): Promise<void> => {
      try {
        let user: User | null | undefined;

        if (hasAuthParams() && !skipSigninCallback) {
          user = await userManager.signinCallback();
          await onSigninCallback?.(user ?? null);
        } else {
          user = await userManager.getUser();
        }

        if (!isMounted) {
          return;
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
        if (!isMounted) {
          return;
        }

        setState({
          isLoading: false,
          isAuthenticated: false,
          user: null,
          error: toError(error),
        });
      }
    };

    void initialise();

    return () => {
      isMounted = false;
    };
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
      settings: managerSettings,
      events: userManager.events,
      signinRedirect: (args?: SigninRedirectArgs) =>
        userManager.signinRedirect(args),
      signinSilent: (args?: SigninSilentArgs) => userManager.signinSilent(args),
      signoutRedirect: (args?: SignoutRedirectArgs) =>
        userManager.signoutRedirect(args),
      removeUser: () => userManager.removeUser(),
      clearStaleState: () => userManager.clearStaleState(),
    }),
    [managerSettings, state, userManager],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
