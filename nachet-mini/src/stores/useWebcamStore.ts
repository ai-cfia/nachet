import { create } from "zustand";

interface WebcamState {
  devices: MediaDeviceInfo[];
  activeDeviceId: string | undefined;

  setDevices: (devices: MediaDeviceInfo[]) => void;
  setActiveDeviceId: (deviceId: string | undefined) => void;
}

export const useWebcamStore = create<WebcamState>((set) => ({
  devices: [],
  activeDeviceId: undefined,

  setDevices: (devices) => set({ devices }),
  setActiveDeviceId: (deviceId) => set({ activeDeviceId: deviceId }),
}));
