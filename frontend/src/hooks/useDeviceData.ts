import { useEffect } from "react";
import { useMsal, useIsAuthenticated } from "@azure/msal-react";
import { InteractionStatus } from "@azure/msal-browser";
import { useDeviceStore } from "@stores/useDeviceStore";
import { fetchDevices } from "@common/api";
import { acquireAccessToken } from "@common/auth";

export const useDeviceData = (backendUrl: string, apiScopeClaim: string) => {
  const {
    devicesData,
    isLoading,
    error,
    setDevicesData,
    setLoading,
    setError,
  } = useDeviceStore();
  const { instance, inProgress } = useMsal();
  const isAuthenticated = useIsAuthenticated();

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

      if (inProgress !== InteractionStatus.None) {
        return; // Wait for interaction to complete
      }

      setLoading(true);
      setError(null);

      try {
        const accessToken = await acquireAccessToken(instance, [apiScopeClaim]);
        const response = await fetchDevices({ backendUrl, accessToken });
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
    apiScopeClaim,
    backendUrl,
    instance,
    inProgress,
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
