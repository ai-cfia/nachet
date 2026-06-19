/*
 * Borrowed and adapted from react-oidc-context:
 * https://github.com/authts/react-oidc-context/blob/80e60ae0b538afdb6e0be7016ec3430104b1bf42/src/AuthContext.ts
 * https://github.com/authts/react-oidc-context/blob/80e60ae0b538afdb6e0be7016ec3430104b1bf42/src/AuthState.ts
 *
 * Original project is MIT licensed. See LICENSE in this directory.
 */
import { createContext } from "react";
import type {
  SigninRedirectArgs,
  SigninSilentArgs,
  SignoutRedirectArgs,
  User,
  UserManagerEvents,
  UserManagerSettings,
} from "oidc-client-ts";

interface AuthState {
  isLoading: boolean;
  isAuthenticated: boolean;
  user: User | null;
  error: Error | null;
}

export interface AuthContextValue extends AuthState {
  settings: UserManagerSettings;
  events: UserManagerEvents;
  signinRedirect: (args?: SigninRedirectArgs) => Promise<void>;
  signinSilent: (args?: SigninSilentArgs) => Promise<User | null>;
  signoutRedirect: (args?: SignoutRedirectArgs) => Promise<void>;
  removeUser: () => Promise<void>;
  clearStaleState: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | undefined>(
  undefined,
);
