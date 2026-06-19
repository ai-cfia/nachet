/*
 * Borrowed and adapted from react-oidc-context useAuth.ts:
 * https://github.com/authts/react-oidc-context/blob/80e60ae0b538afdb6e0be7016ec3430104b1bf42/src/useAuth.ts
 *
 * Original project is MIT licensed. See LICENSE in this directory.
 */
import { useContext } from "react";
import { AuthContext } from "./AuthContext";

export function useAuth() {
  const context = useContext(AuthContext);

  if (context === undefined) {
    throw new Error("useAuth must be used within AuthProvider");
  }

  return context;
}
