import { useEffect } from "react";
import { useMsal, useIsAuthenticated } from "@azure/msal-react";
import { InteractionStatus } from "@azure/msal-browser";
import { useSpeciesStore } from "@stores/useSpeciesStore";
import { requestClassList } from "@common/api";
import { acquireAccessToken } from "@common/auth";

export const useSpeciesData = (backendUrl: string, apiScopeClaim: string) => {
  const {
    speciesData,
    isLoading,
    error,
    setSpeciesData,
    setLoading,
    setError,
  } = useSpeciesStore();
  const { instance, inProgress } = useMsal();
  const isAuthenticated = useIsAuthenticated();

  useEffect(() => {
    const fetchSpeciesData = async () => {
      if (!backendUrl || backendUrl === "") {
        return;
      }

      if (!isAuthenticated) {
        return; // Must be authenticated first
      }

      if (speciesData) {
        return; // Already have data, don't fetch again
      }

      if (inProgress !== InteractionStatus.None) {
        return; // Wait for interaction to complete
      }

      setLoading(true);
      setError(null);

      try {
        const accessToken = await acquireAccessToken(instance, [apiScopeClaim]);
        const response = await requestClassList({ backendUrl, accessToken });
        setSpeciesData(response);
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Unknown error occurred";
        setError(errorMessage);
        console.error("Error fetching species data:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchSpeciesData();
  }, [
    apiScopeClaim,
    backendUrl,
    instance,
    inProgress,
    isAuthenticated,
    setError,
    setLoading,
    setSpeciesData,
    speciesData,
  ]);

  return {
    speciesData,
    isLoading,
    error,
  };
};
