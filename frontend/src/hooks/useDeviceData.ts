import { useEffect } from "react";
import { useDeviceStore } from "@stores/useDeviceStore";
import { fetchDevices } from "@common/api";
import { useNachetAuth } from "@auth";

export const useDeviceData = (backendUrl: string) => {
  const {
    devicesData,
    isLoading,
    error,
    setDevicesData,
    setLoading,
    setError,
  } = useDeviceStore();
  const { isAuthenticated, isLoading: authLoading } = useNachetAuth();

  useEffect(() => {
    const fetchDeviceData = async () => {
      if (!backendUrl || backendUrl === "") {
        return;
      }

      if (!isAuthenticated) {
        return; // Must be authenticated first
      }

      if (devicesData) {
        return; // Already have data, don't fetch again
      }

      if (authLoading) {
        return; // Wait for interaction to complete
      }

      setLoading(true);
      setError(null);

      try {
        const response = await fetchDevices({ backendUrl });
        setDevicesData(response);
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Unknown error occurred";
        setError(errorMessage);
        console.error("Error fetching device data:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchDeviceData();
  }, [
    authLoading,
    backendUrl,
    isAuthenticated,
    setError,
    setLoading,
    setDevicesData,
    devicesData,
  ]);

  return {
    devicesData,
    isLoading,
    error,
  };
};
