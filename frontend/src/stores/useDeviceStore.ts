import { create } from "zustand";
import { persist } from "zustand/middleware";
import { ApiDevicesResponse } from "@common/types";

interface DeviceSelection {
  selectedBrandId: string;
  selectedModelId: string;
  selectedLensId: string;
}

interface DeviceState {
  devicesData: ApiDevicesResponse | null;
  isLoading: boolean;
  error: string | null;
  deviceSelection: DeviceSelection;
  setDevicesData: (data: ApiDevicesResponse) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearDevicesData: () => void;
  setDeviceSelection: (selection: DeviceSelection) => void;
  clearDeviceSelection: () => void;
  isDeviceInfoSet: () => boolean;
}

export const useDeviceStore = create<DeviceState>()(
  persist(
    (set, get) => ({
      devicesData: null,
      isLoading: false,
      error: null,
      deviceSelection: {
        selectedBrandId: "",
        selectedModelId: "",
        selectedLensId: "",
      },
      setDevicesData: (data) => set({ devicesData: data, error: null }),
      setLoading: (loading) => set({ isLoading: loading }),
      setError: (error) => set({ error, isLoading: false }),
      clearDevicesData: () =>
        set({ devicesData: null, error: null, isLoading: false }),
      setDeviceSelection: (selection) => set({ deviceSelection: selection }),
      clearDeviceSelection: () =>
        set({
          deviceSelection: {
            selectedBrandId: "",
            selectedModelId: "",
            selectedLensId: "",
          },
        }),
      isDeviceInfoSet: () => {
        const state = get();
        return (
          state.deviceSelection.selectedBrandId !== "" &&
          state.deviceSelection.selectedModelId !== "" &&
          state.deviceSelection.selectedLensId !== ""
        );
      },
    }),
    {
      name: "device-storage",
      partialize: (state) => ({ deviceSelection: state.deviceSelection }),
    },
  ),
);
