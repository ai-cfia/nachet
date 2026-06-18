import { createContext, useContext } from "react";
import type { NachetAuthContextValue } from "./types";

export const NachetAuthContext = createContext<
  NachetAuthContextValue | undefined
>(undefined);

export function useNachetAuth(): NachetAuthContextValue {
  const context = useContext(NachetAuthContext);
  if (!context) {
    throw new Error("useNachetAuth must be used within NachetAuthProvider");
  }
  return context;
}
