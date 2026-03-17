import { useEffect } from "react";
import { useWebcamStore } from "@stores/useWebcamStore";

export const useWebcamDevices = () => {
  const { devices, activeDeviceId, setDevices, setActiveDeviceId } =
    useWebcamStore();

  useEffect(() => {
    if (
      !navigator ||
      !navigator.mediaDevices ||
      typeof navigator.mediaDevices.enumerateDevices !== "function"
    ) {
      return;
    }

    const updateDevices = async (): Promise<void> => {
      try {
        const availableDevices =
          await navigator.mediaDevices.enumerateDevices();
        const videoDevices = availableDevices.filter(
          (i) => i.kind === "videoinput",
        );
        setDevices(videoDevices);

        if (activeDeviceId === "" || activeDeviceId === undefined) {
          setActiveDeviceId(videoDevices[0]?.deviceId);
        }
      } catch (error) {
        console.error("Failed to enumerate devices:", error);
      }
    };

    void updateDevices();

    navigator.mediaDevices.addEventListener("devicechange", updateDevices);

    return () => {
      navigator.mediaDevices.removeEventListener("devicechange", updateDevices);
    };
  }, [activeDeviceId, setDevices, setActiveDeviceId]);

  return { devices, activeDeviceId };
};
