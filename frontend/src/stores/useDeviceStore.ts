import { create } from "zustand";
import { ApiDevicesResponse } from "@common/types";

interface DeviceState {
  devicesData: ApiDevicesResponse | null;
  isLoading: boolean;
  error: string | null;
  setDevicesData: (data: ApiDevicesResponse) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearDevicesData: () => void;
}

export const useDeviceStore = create<DeviceState>((set) => ({
  devicesData: null,
  isLoading: false,
  error: null,
  setDevicesData: (data) => set({ devicesData: data, error: null }),
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error, isLoading: false }),
  clearDevicesData: () =>
    set({ devicesData: null, error: null, isLoading: false }),
}));
