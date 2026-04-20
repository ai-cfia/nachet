import { describe, it, expect, beforeEach } from "vitest";
import { useMetadataDefaultsStore } from "../useMetadataDefaultsStore";
import type { MetadataDefaults } from "../useMetadataDefaultsStore";

const initialDefaults: MetadataDefaults = {
  namePrefix: "image",
  deviceBrandId: "",
  deviceModelId: "",
  deviceLensId: "",
  trayCode: "",
  description: "",
};

describe("useMetadataDefaultsStore", () => {
  beforeEach(() => {
    useMetadataDefaultsStore.setState({ defaults: { ...initialDefaults } });
  });

  it("has correct initial defaults", () => {
    expect(useMetadataDefaultsStore.getState().defaults).toEqual(initialDefaults);
  });

  describe("setDefaults", () => {
    it("updates defaults with new values", () => {
      const newDefaults: MetadataDefaults = {
        namePrefix: "seed",
        deviceBrandId: "brand-1",
        deviceModelId: "model-x",
        deviceLensId: "lens-wide",
        trayCode: "A",
        description: "test session",
      };
      useMetadataDefaultsStore.getState().setDefaults(newDefaults);
      expect(useMetadataDefaultsStore.getState().defaults).toEqual(newDefaults);
    });

    it("replaces the previous defaults entirely", () => {
      useMetadataDefaultsStore.getState().setDefaults({ ...initialDefaults, namePrefix: "first" });
      useMetadataDefaultsStore.getState().setDefaults({ ...initialDefaults, namePrefix: "second", deviceBrandId: "brand-x" });
      const { defaults } = useMetadataDefaultsStore.getState();
      expect(defaults.namePrefix).toBe("second");
      expect(defaults.deviceBrandId).toBe("brand-x");
    });

    it("accepts all valid tray codes", () => {
      for (const code of ["A", "B", "C", "D", "E", "None", ""] as const) {
        useMetadataDefaultsStore.getState().setDefaults({ ...initialDefaults, trayCode: code });
        expect(useMetadataDefaultsStore.getState().defaults.trayCode).toBe(code);
      }
    });
  });

  describe("clearDefaults", () => {
    it("resets defaults to initial values after modification", () => {
      useMetadataDefaultsStore.getState().setDefaults({
        namePrefix: "custom",
        deviceBrandId: "brand-1",
        deviceModelId: "model-1",
        deviceLensId: "lens-1",
        trayCode: "B",
        description: "some desc",
      });
      useMetadataDefaultsStore.getState().clearDefaults();
      expect(useMetadataDefaultsStore.getState().defaults).toEqual(initialDefaults);
    });

    it("is idempotent when already at initial state", () => {
      useMetadataDefaultsStore.getState().clearDefaults();
      expect(useMetadataDefaultsStore.getState().defaults).toEqual(initialDefaults);
    });
  });
});
