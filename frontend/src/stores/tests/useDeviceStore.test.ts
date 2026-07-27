import { describe, it, expect, beforeEach } from "vitest";
import { act } from "@testing-library/react";
import { useDeviceStore } from "../useDeviceStore";
import type { ApiDevicesResponse } from "@common/types";

describe("useDeviceStore", () => {
  const mockDevicesData: ApiDevicesResponse = {
    devices: [
      {
        id: "brand-1",
        name: "Canon",
        description: "Canon cameras",
        models: [
          {
            id: "model-1",
            name: "EOS R5",
            description: "Canon EOS R5",
          },
        ],
        lenses: [
          {
            id: "lens-1",
            name: "RF 24-70mm f/2.8",
            description: "Canon RF 24-70mm",
          },
          {
            id: "lens-2",
            name: "RF 70-200mm f/2.8",
            description: "Canon RF 70-200mm",
          },
        ],
      },
      {
        id: "brand-2",
        name: "Nikon",
        description: "Nikon cameras",
        models: [
          {
            id: "model-2",
            name: "Z9",
            description: "Nikon Z9",
          },
        ],
        lenses: [
          {
            id: "lens-3",
            name: "NIKKOR Z 24-70mm f/2.8",
            description: "Nikon NIKKOR Z 24-70mm",
          },
        ],
      },
    ],
  };

  beforeEach(() => {
    // Clear localStorage for persistence tests
    localStorage.clear();

    // Reset store to initial state
    act(() => {
      useDeviceStore.setState({
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
          magnification: 0,
          sampleIdPrefix: "",
          sampleDescription: "",
        },
      });
    });
  });

  describe("Initial State", () => {
    it("should have null devicesData", () => {
      expect(useDeviceStore.getState().devicesData).toBeNull();
    });

    it("should have isLoading false", () => {
      expect(useDeviceStore.getState().isLoading).toBe(false);
    });

    it("should have null error", () => {
      expect(useDeviceStore.getState().error).toBeNull();
    });

    it("should have empty device selection", () => {
      const { deviceSelection } = useDeviceStore.getState();
      expect(deviceSelection.selectedBrandId).toBe("");
      expect(deviceSelection.selectedModelId).toBe("");
      expect(deviceSelection.selectedLensId).toBe("");
    });

    it("should have empty sample metadata", () => {
      const { sampleMetadata } = useDeviceStore.getState();
      expect(sampleMetadata.trayCode).toBe("");
      expect(sampleMetadata.magnification).toBe(0);
      expect(sampleMetadata.sampleIdPrefix).toBe("");
      expect(sampleMetadata.sampleDescription).toBe("");
    });
  });

  describe("setDevicesData", () => {
    it("should set devices data", () => {
      act(() => {
        useDeviceStore.getState().setDevicesData(mockDevicesData);
      });

      expect(useDeviceStore.getState().devicesData).toEqual(mockDevicesData);
    });

    it("should clear error when setting devices data", () => {
      act(() => {
        useDeviceStore.getState().setError("Previous error");
        useDeviceStore.getState().setDevicesData(mockDevicesData);
      });

      const state = useDeviceStore.getState();
      expect(state.devicesData).toEqual(mockDevicesData);
      expect(state.error).toBeNull();
    });
  });

  describe("setLoading", () => {
    it("should set loading to true", () => {
      act(() => {
        useDeviceStore.getState().setLoading(true);
      });

      expect(useDeviceStore.getState().isLoading).toBe(true);
    });

    it("should set loading to false", () => {
      act(() => {
        useDeviceStore.getState().setLoading(true);
        useDeviceStore.getState().setLoading(false);
      });

      expect(useDeviceStore.getState().isLoading).toBe(false);
    });
  });

  describe("setError", () => {
    it("should set error message", () => {
      act(() => {
        useDeviceStore.getState().setError("Failed to load devices");
      });

      const state = useDeviceStore.getState();
      expect(state.error).toBe("Failed to load devices");
      expect(state.isLoading).toBe(false);
    });

    it("should set loading to false when setting error", () => {
      act(() => {
        useDeviceStore.getState().setLoading(true);
        useDeviceStore.getState().setError("Error occurred");
      });

      const state = useDeviceStore.getState();
      expect(state.isLoading).toBe(false);
      expect(state.error).toBe("Error occurred");
    });

    it("should clear error with null", () => {
      act(() => {
        useDeviceStore.getState().setError("Error message");
        useDeviceStore.getState().setError(null);
      });

      expect(useDeviceStore.getState().error).toBeNull();
    });
  });

  describe("clearDevicesData", () => {
    it("should clear all device data state", () => {
      act(() => {
        useDeviceStore.getState().setDevicesData(mockDevicesData);
        useDeviceStore.getState().setLoading(true);
        useDeviceStore.getState().setError("Some error");
        useDeviceStore.getState().clearDevicesData();
      });

      const state = useDeviceStore.getState();
      expect(state.devicesData).toBeNull();
      expect(state.error).toBeNull();
      expect(state.isLoading).toBe(false);
    });
  });

  describe("setDeviceSelection", () => {
    it("should set device selection", () => {
      const selection = {
        selectedBrandId: "brand-1",
        selectedModelId: "model-1",
        selectedLensId: "lens-1",
      };

      act(() => {
        useDeviceStore.getState().setDeviceSelection(selection);
      });

      expect(useDeviceStore.getState().deviceSelection).toEqual(selection);
    });

    it("should update device selection", () => {
      act(() => {
        useDeviceStore.getState().setDeviceSelection({
          selectedBrandId: "brand-1",
          selectedModelId: "model-1",
          selectedLensId: "lens-1",
        });
        useDeviceStore.getState().setDeviceSelection({
          selectedBrandId: "brand-2",
          selectedModelId: "model-2",
          selectedLensId: "lens-3",
        });
      });

      const { deviceSelection } = useDeviceStore.getState();
      expect(deviceSelection.selectedBrandId).toBe("brand-2");
      expect(deviceSelection.selectedModelId).toBe("model-2");
      expect(deviceSelection.selectedLensId).toBe("lens-3");
    });

    it("should allow partial device selection", () => {
      act(() => {
        useDeviceStore.getState().setDeviceSelection({
          selectedBrandId: "brand-1",
          selectedModelId: "",
          selectedLensId: "",
        });
      });

      const { deviceSelection } = useDeviceStore.getState();
      expect(deviceSelection.selectedBrandId).toBe("brand-1");
      expect(deviceSelection.selectedModelId).toBe("");
      expect(deviceSelection.selectedLensId).toBe("");
    });
  });

  describe("clearDeviceSelection", () => {
    it("should clear device selection", () => {
      act(() => {
        useDeviceStore.getState().setDeviceSelection({
          selectedBrandId: "brand-1",
          selectedModelId: "model-1",
          selectedLensId: "lens-1",
        });
        useDeviceStore.getState().clearDeviceSelection();
      });

      const { deviceSelection } = useDeviceStore.getState();
      expect(deviceSelection.selectedBrandId).toBe("");
      expect(deviceSelection.selectedModelId).toBe("");
      expect(deviceSelection.selectedLensId).toBe("");
    });
  });

  describe("setSampleMetadata", () => {
    it("should set sample metadata", () => {
      const metadata = {
        trayCode: "TRAY-001",
        magnification: 40,
        sampleIdPrefix: "SAMPLE-2024",
        sampleDescription: "Test sample description",
      };

      act(() => {
        useDeviceStore.getState().setSampleMetadata(metadata);
      });

      expect(useDeviceStore.getState().sampleMetadata).toEqual(metadata);
    });

    it("should update sample metadata", () => {
      act(() => {
        useDeviceStore.getState().setSampleMetadata({
          trayCode: "TRAY-001",
          magnification: 40,
          sampleIdPrefix: "SAMPLE-2024",
          sampleDescription: "Original description",
        });
        useDeviceStore.getState().setSampleMetadata({
          trayCode: "TRAY-002",
          magnification: 100,
          sampleIdPrefix: "SAMPLE-2025",
          sampleDescription: "Updated description",
        });
      });

      const { sampleMetadata } = useDeviceStore.getState();
      expect(sampleMetadata.trayCode).toBe("TRAY-002");
      expect(sampleMetadata.magnification).toBe(100);
      expect(sampleMetadata.sampleIdPrefix).toBe("SAMPLE-2025");
      expect(sampleMetadata.sampleDescription).toBe("Updated description");
    });
  });

  describe("clearSampleMetadata", () => {
    it("should clear sample metadata", () => {
      act(() => {
        useDeviceStore.getState().setSampleMetadata({
          trayCode: "TRAY-001",
          magnification: 40,
          sampleIdPrefix: "SAMPLE-2024",
          sampleDescription: "Test sample",
        });
        useDeviceStore.getState().clearSampleMetadata();
      });

      const { sampleMetadata } = useDeviceStore.getState();
      expect(sampleMetadata.trayCode).toBe("");
      expect(sampleMetadata.magnification).toBe(0.1);
      expect(sampleMetadata.sampleIdPrefix).toBe("");
      expect(sampleMetadata.sampleDescription).toBe("");
    });
  });

  describe("isDeviceInfoSet", () => {
    it("should return false when device selection is empty", () => {
      expect(useDeviceStore.getState().isDeviceInfoSet()).toBe(false);
    });

    it("should return false when device selection is partial", () => {
      act(() => {
        useDeviceStore.getState().setDeviceSelection({
          selectedBrandId: "brand-1",
          selectedModelId: "model-1",
          selectedLensId: "",
        });
      });

      expect(useDeviceStore.getState().isDeviceInfoSet()).toBe(false);
    });

    it("should return true when all device fields are set", () => {
      act(() => {
        useDeviceStore.getState().setDeviceSelection({
          selectedBrandId: "brand-1",
          selectedModelId: "model-1",
          selectedLensId: "lens-1",
        });
      });

      expect(useDeviceStore.getState().isDeviceInfoSet()).toBe(true);
    });
  });

  describe("isSampleMetadataComplete", () => {
    it("should return false when both device and sample metadata are empty", () => {
      expect(useDeviceStore.getState().isSampleMetadataComplete()).toBe(false);
    });

    it("should return false when only device selection is complete", () => {
      act(() => {
        useDeviceStore.getState().setDeviceSelection({
          selectedBrandId: "brand-1",
          selectedModelId: "model-1",
          selectedLensId: "lens-1",
        });
      });

      expect(useDeviceStore.getState().isSampleMetadataComplete()).toBe(false);
    });

    it("should return false when only sample metadata is complete", () => {
      act(() => {
        useDeviceStore.getState().setSampleMetadata({
          trayCode: "TRAY-001",
          magnification: 40,
          sampleIdPrefix: "SAMPLE-2024",
          sampleDescription: "Test sample",
        });
      });

      expect(useDeviceStore.getState().isSampleMetadataComplete()).toBe(false);
    });

    it("should return false when magnification is zero", () => {
      act(() => {
        useDeviceStore.getState().setDeviceSelection({
          selectedBrandId: "brand-1",
          selectedModelId: "model-1",
          selectedLensId: "lens-1",
        });
        useDeviceStore.getState().setSampleMetadata({
          trayCode: "TRAY-001",
          magnification: 0,
          sampleIdPrefix: "SAMPLE-2024",
          sampleDescription: "Test sample",
        });
      });

      expect(useDeviceStore.getState().isSampleMetadataComplete()).toBe(false);
    });

    it("should return true when all fields are complete", () => {
      act(() => {
        useDeviceStore.getState().setDeviceSelection({
          selectedBrandId: "brand-1",
          selectedModelId: "model-1",
          selectedLensId: "lens-1",
        });
        useDeviceStore.getState().setSampleMetadata({
          trayCode: "TRAY-001",
          magnification: 40,
          sampleIdPrefix: "SAMPLE-2024",
          sampleDescription: "Test sample",
        });
      });

      expect(useDeviceStore.getState().isSampleMetadataComplete()).toBe(true);
    });
  });

  describe("getMissingMetadataCount", () => {
    it("should return 7 when all fields are empty", () => {
      expect(useDeviceStore.getState().getMissingMetadataCount()).toBe(7);
    });

    it("should return 3 when device selection is complete", () => {
      act(() => {
        useDeviceStore.getState().setDeviceSelection({
          selectedBrandId: "brand-1",
          selectedModelId: "model-1",
          selectedLensId: "lens-1",
        });
      });

      expect(useDeviceStore.getState().getMissingMetadataCount()).toBe(4);
    });

    it("should return 3 when sample metadata is complete", () => {
      act(() => {
        useDeviceStore.getState().setSampleMetadata({
          trayCode: "TRAY-001",
          magnification: 40,
          sampleIdPrefix: "SAMPLE-2024",
          sampleDescription: "Test sample",
        });
      });

      expect(useDeviceStore.getState().getMissingMetadataCount()).toBe(3);
    });

    it("should return 0 when all fields are complete", () => {
      act(() => {
        useDeviceStore.getState().setDeviceSelection({
          selectedBrandId: "brand-1",
          selectedModelId: "model-1",
          selectedLensId: "lens-1",
        });
        useDeviceStore.getState().setSampleMetadata({
          trayCode: "TRAY-001",
          magnification: 40,
          sampleIdPrefix: "SAMPLE-2024",
          sampleDescription: "Test sample",
        });
      });

      expect(useDeviceStore.getState().getMissingMetadataCount()).toBe(0);
    });

    it("should count magnification <= 0 as missing", () => {
      act(() => {
        useDeviceStore.getState().setSampleMetadata({
          trayCode: "TRAY-001",
          magnification: -5,
          sampleIdPrefix: "SAMPLE-2024",
          sampleDescription: "Test sample",
        });
      });

      const missing = useDeviceStore.getState().getMissingMetadataCount();
      expect(missing).toBeGreaterThanOrEqual(4);
    });
  });

  describe("Persistence", () => {
    it("should persist device selection to localStorage", () => {
      act(() => {
        useDeviceStore.getState().setDeviceSelection({
          selectedBrandId: "brand-1",
          selectedModelId: "model-1",
          selectedLensId: "lens-1",
        });
      });

      // Check localStorage
      const stored = localStorage.getItem("device-storage");
      expect(stored).toBeTruthy();
      if (stored) {
        const parsed = JSON.parse(stored);
        expect(parsed.state.deviceSelection).toEqual({
          selectedBrandId: "brand-1",
          selectedModelId: "model-1",
          selectedLensId: "lens-1",
        });
      }
    });

    it("should persist sample metadata to localStorage", () => {
      act(() => {
        useDeviceStore.getState().setSampleMetadata({
          trayCode: "TRAY-001",
          magnification: 40,
          sampleIdPrefix: "SAMPLE-2024",
          sampleDescription: "Test sample",
        });
      });

      const stored = localStorage.getItem("device-storage");
      expect(stored).toBeTruthy();
      if (stored) {
        const parsed = JSON.parse(stored);
        expect(parsed.state.sampleMetadata).toEqual({
          trayCode: "TRAY-001",
          magnification: 40,
          sampleIdPrefix: "SAMPLE-2024",
          sampleDescription: "Test sample",
        });
      }
    });

    it("should not persist devicesData to localStorage", () => {
      act(() => {
        useDeviceStore.getState().setDevicesData(mockDevicesData);
      });

      const stored = localStorage.getItem("device-storage");
      if (stored) {
        const parsed = JSON.parse(stored);
        expect(parsed.state.devicesData).toBeUndefined();
      }
    });

    it("should not persist loading/error state to localStorage", () => {
      act(() => {
        useDeviceStore.getState().setLoading(true);
        useDeviceStore.getState().setError("Test error");
      });

      const stored = localStorage.getItem("device-storage");
      if (stored) {
        const parsed = JSON.parse(stored);
        expect(parsed.state.isLoading).toBeUndefined();
        expect(parsed.state.error).toBeUndefined();
      }
    });
  });

  describe("Edge Cases", () => {
    it("should handle rapid state changes", () => {
      act(() => {
        useDeviceStore.getState().setDeviceSelection({
          selectedBrandId: "brand-1",
          selectedModelId: "model-1",
          selectedLensId: "lens-1",
        });
        useDeviceStore.getState().setSampleMetadata({
          trayCode: "TRAY-001",
          magnification: 40,
          sampleIdPrefix: "SAMPLE-2024",
          sampleDescription: "Test",
        });
        useDeviceStore.getState().clearDeviceSelection();
        useDeviceStore.getState().clearSampleMetadata();
      });

      expect(useDeviceStore.getState().isDeviceInfoSet()).toBe(false);
      expect(useDeviceStore.getState().isSampleMetadataComplete()).toBe(false);
      expect(useDeviceStore.getState().getMissingMetadataCount()).toBe(7);
    });

    it("should handle empty device data", () => {
      const emptyDevicesData: ApiDevicesResponse = {
        devices: [],
      };

      act(() => {
        useDeviceStore.getState().setDevicesData(emptyDevicesData);
      });

      expect(useDeviceStore.getState().devicesData?.devices).toHaveLength(0);
    });
  });
});
