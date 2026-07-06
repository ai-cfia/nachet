import { useEffect } from "react";
import { useSpeciesStore } from "@stores/useSpeciesStore";
import { requestClassList } from "@common/api";
import { useNachetAuth } from "@auth";

export const useSpeciesData = (backendUrl: string) => {
  const {
    speciesData,
    isLoading,
    error,
    setSpeciesData,
    setLoading,
    setError,
  } = useSpeciesStore();
  const { isAuthenticated, isLoading: authLoading } = useNachetAuth();

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

      if (authLoading) {
        return; // Wait for interaction to complete
      }

      setLoading(true);
      setError(null);

      try {
        const response = await requestClassList({ backendUrl });
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
    authLoading,
    backendUrl,
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
