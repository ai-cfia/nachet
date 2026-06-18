/*
 * Borrowed and adapted from react-oidc-context AuthState.ts:
 * https://github.com/authts/react-oidc-context/blob/main/src/AuthState.ts
 *
 * Original project is MIT licensed. See LICENSE in this directory.
 */
import type { User } from "oidc-client-ts";

export interface AuthState {
  isLoading: boolean;
  isAuthenticated: boolean;
  user: User | null;
  error: Error | null;
}

export const initialAuthState: AuthState = {
  isLoading: true,
  isAuthenticated: false,
  user: null,
  error: null,
};
