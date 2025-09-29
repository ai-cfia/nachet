import { useMsal } from "@azure/msal-react";
import { useCallback } from "react";
import { getAccessToken } from "@common/auth";

export function useAuth(apiScopeClaim: string) {
  const { instance: msalInstance } = useMsal();

  // Always fetch a fresh token right before API calls
  const fetchAccessToken = useCallback(async (): Promise<string> => {
    const accessToken = await getAccessToken(msalInstance, {
      scopes: [apiScopeClaim],
    });
    return accessToken;
  }, [msalInstance, apiScopeClaim]);

  return {
    fetchAccessToken,
    msalInstance,
  };
}
