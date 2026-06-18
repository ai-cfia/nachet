/*
 * Borrowed and adapted from react-oidc-context AuthContext.ts:
 * https://github.com/authts/react-oidc-context/blob/main/src/AuthContext.ts
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
import type { AuthState } from "./AuthState";

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
