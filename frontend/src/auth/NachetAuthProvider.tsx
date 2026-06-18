import React from "react";
import { NachetAuthContext } from "./NachetAuthContext";
import { MsalAuthProvider } from "./msal/MsalAuthProvider";

export interface NachetAuthProviderProps {
  apiScopeClaim: string;
  children: React.ReactNode;
}

export function NachetAuthProvider({
  apiScopeClaim,
  children,
}: NachetAuthProviderProps) {
  const configuredProvider = (import.meta.env.VITE_AUTH_PROVIDER ?? "msal")
    .trim()
    .toLowerCase();

  if (configuredProvider !== "msal") {
    throw new Error(
      `Unsupported auth provider '${configuredProvider}'. Only 'msal' is wired in this slice.`,
    );
  }

  return (
    <MsalAuthProvider
      apiScopeClaim={apiScopeClaim}
      authContext={NachetAuthContext}
    >
      {children}
    </MsalAuthProvider>
  );
}
