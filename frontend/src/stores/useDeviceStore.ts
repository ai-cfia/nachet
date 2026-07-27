import { create } from "zustand";
import { persist } from "zustand/middleware";
import { ApiDevicesResponse } from "@common/types";

interface DeviceSelection {
  selectedBrandId: string;
  selectedModelId: string;
  selectedLensId: string;
}

interface SampleMetadata {
  trayCode: string;
  magnification: number;
  sampleIdPrefix: string;
  sampleDescription: string;
}

interface DeviceState {
  devicesData: ApiDevicesResponse | null;
  isLoading: boolean;
  error: string | null;
  deviceSelection: DeviceSelection;
  sampleMetadata: SampleMetadata;
  setDevicesData: (data: ApiDevicesResponse) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearDevicesData: () => void;
  setDeviceSelection: (selection: DeviceSelection) => void;
  clearDeviceSelection: () => void;
  setSampleMetadata: (metadata: SampleMetadata) => void;
  clearSampleMetadata: () => void;
  isDeviceInfoSet: () => boolean;
  isSampleMetadataComplete: () => boolean;
  getMissingMetadataCount: () => number;
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
      sampleMetadata: {
        trayCode: "",
        magnification: 0.1,
        sampleIdPrefix: "",
        sampleDescription: "",
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
      setSampleMetadata: (metadata) => set({ sampleMetadata: metadata }),
      clearSampleMetadata: () =>
        set({
          sampleMetadata: {
            trayCode: "",
            magnification: 0.1,
            sampleIdPrefix: "",
            sampleDescription: "",
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
      isSampleMetadataComplete: () => {
        const state = get();
        const { deviceSelection, sampleMetadata } = state;
        return (
          deviceSelection.selectedBrandId !== "" &&
          deviceSelection.selectedModelId !== "" &&
          deviceSelection.selectedLensId !== "" &&
          sampleMetadata.trayCode !== "" &&
          sampleMetadata.magnification > 0 &&
          sampleMetadata.sampleIdPrefix !== "" &&
          sampleMetadata.sampleDescription !== ""
        );
      },
      getMissingMetadataCount: () => {
        const state = get();
        const { deviceSelection, sampleMetadata } = state;
        let missing = 0;
        if (!deviceSelection.selectedBrandId) missing++;
        if (!deviceSelection.selectedModelId) missing++;
        if (!deviceSelection.selectedLensId) missing++;
        if (!sampleMetadata.trayCode) missing++;
        if (sampleMetadata.magnification <= 0) missing++;
        if (!sampleMetadata.sampleIdPrefix) missing++;
        if (!sampleMetadata.sampleDescription) missing++;
        return missing;
      },
    }),
    {
      name: "device-storage",
      partialize: (state) => ({
        deviceSelection: state.deviceSelection,
        sampleMetadata: state.sampleMetadata,
      }),
      version: 1, // Increment version to trigger migration
      migrate: (persistedState: any, version: number) => {
        console.log("DEBUG: Migrating device store from version", version);

        // Migrate from version 0 (no version) to version 1
        if (version === 0 || !version) {
          // Check if old sampleId exists and migrate to sampleIdPrefix
          if (persistedState?.sampleMetadata?.sampleId !== undefined) {
            console.log(
              "DEBUG: Migrating sampleId to sampleIdPrefix:",
              persistedState.sampleMetadata.sampleId,
            );
            persistedState.sampleMetadata.sampleIdPrefix =
              persistedState.sampleMetadata.sampleId;
            delete persistedState.sampleMetadata.sampleId;
          }
        }

        return persistedState;
      },
    },
  ),
);
