import { useMsal } from "@azure/msal-react";
import { getAccessToken } from "@common/auth";

export function useAuth(apiScopeClaim: string) {
  const { instance: msalInstance } = useMsal();

  // Always fetch a fresh token right before API calls
  const fetchAccessToken = async (): Promise<string> => {
    const accessToken = await getAccessToken(msalInstance, {
      scopes: [apiScopeClaim],
    });
    return accessToken;
  };

  return {
    fetchAccessToken,
    msalInstance,
  };
}
