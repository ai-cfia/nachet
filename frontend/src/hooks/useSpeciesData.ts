import { useEffect } from "react";
import { useSpeciesStore } from "../stores/useSpeciesStore";
import { requestClassList } from "@common/api";

export const useSpeciesData = (backendUrl: string) => {
  const {
    speciesData,
    isLoading,
    error,
    setSpeciesData,
    setLoading,
    setError,
  } = useSpeciesStore();

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
        const response = await requestClassList(backendUrl);
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
  }, [backendUrl, speciesData, setSpeciesData, setLoading, setError]);

  return {
    speciesData,
    isLoading,
    error,
  };
};
