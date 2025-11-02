/**
 * useWebcamDevices Hook
 *
 * Custom hook to enumerate and manage webcam devices.
 * Automatically detects available video input devices and sets the active device.
 */

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

    // Retrieves the available devices and sets the active device to the first available device
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
        alert(error);
      }
    };

    void updateDevices();

    // Listen for device changes (e.g., camera connected/disconnected)
    navigator.mediaDevices.addEventListener("devicechange", updateDevices);

    return () => {
      navigator.mediaDevices.removeEventListener("devicechange", updateDevices);
    };
  }, [activeDeviceId, setDevices, setActiveDeviceId]);

  return { devices, activeDeviceId };
};
