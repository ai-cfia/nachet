import { useWebcamStore } from "@stores/useWebcamStore";
import { useCallback, useEffect, useState } from "react";

export const useWebcamDevices = () => {
  const { devices, activeDeviceId, setDevices, setActiveDeviceId } =
    useWebcamStore();

  const [listenerReady, setListenerReady] = useState(false);

  const updateDevices = useCallback(async () => {
    if (!navigator?.mediaDevices?.enumerateDevices) return;

    try {
      const availableDevices = await navigator.mediaDevices.enumerateDevices();
      const videoDevices = availableDevices.filter(
        (i) => i.kind === "videoinput",
      );
      setDevices(videoDevices);

      const { activeDeviceId: currentId } = useWebcamStore.getState();
      if (!currentId) {
        const defaultDevice = videoDevices[1] ?? videoDevices[0];
        setActiveDeviceId(defaultDevice?.deviceId);
      }
    } catch (error) {
      console.error("Failed to enumerate devices:", error);
    }
  }, [setDevices, setActiveDeviceId]);

  useEffect(() => {
    if (!listenerReady) return;
    navigator.mediaDevices.addEventListener("devicechange", updateDevices);
    return () => {
      navigator.mediaDevices.removeEventListener("devicechange", updateDevices);
    };
  }, [listenerReady, updateDevices]);

  const requestDevices = useCallback(async () => {
    if (!navigator?.mediaDevices?.enumerateDevices) return;

    try {
      const tempStream = await navigator.mediaDevices.getUserMedia({
        video: true,
      });
      tempStream.getTracks().forEach((track) => track.stop());
    } catch (error) {
      console.error("Camera permission denied or unavailable:", error);
      return;
    }

    setListenerReady(true);
    await updateDevices();
  }, [updateDevices]);

  return { devices, activeDeviceId, requestDevices };
};
