import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { TrayCode } from "@common/types";

export interface MetadataDefaults {
  namePrefix: string;
  deviceBrandId: string;
  deviceModelId: string;
  deviceLensId: string;
  trayCode: TrayCode | "";
  description: string;
}

interface MetadataDefaultsState {
  defaults: MetadataDefaults;
  setDefaults: (defaults: MetadataDefaults) => void;
  clearDefaults: () => void;
}

const initialDefaults: MetadataDefaults = {
  namePrefix: "image",
  deviceBrandId: "",
  deviceModelId: "",
  deviceLensId: "",
  trayCode: "",
  description: "",
};

export const useMetadataDefaultsStore = create<MetadataDefaultsState>()(
  persist(
    (set) => ({
      defaults: { ...initialDefaults },
      setDefaults: (defaults: MetadataDefaults) => set({ defaults }),
      clearDefaults: () => set({ defaults: { ...initialDefaults } }),
    }),
    { name: "metadata-defaults-storage" },
  ),
);
