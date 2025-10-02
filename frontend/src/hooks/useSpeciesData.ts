import { useEffect } from "react";
import { useMsal } from "@azure/msal-react";
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
  const { instance } = useMsal();

  useEffect(() => {
    const fetchSpeciesData = async () => {
      if (!backendUrl || backendUrl === "") {
        return;
      }

      if (speciesData) {
        return; // Already have data, don't fetch again
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
