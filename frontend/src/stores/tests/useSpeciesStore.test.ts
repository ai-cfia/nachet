import { describe, it, expect, beforeEach } from "vitest";
import { act } from "@testing-library/react";
import { useSpeciesStore } from "../useSpeciesStore";
import type { ApiSpeciesData } from "@common/types";

describe("useSpeciesStore", () => {
  const mockSpeciesData: ApiSpeciesData = {
    seeds: [
      {
        seedId: "1",
        nameCode: "AVEFC",
        family: "Poaceae",
        genus: "Avena",
        species: "fatua",
      },
      {
        seedId: "2",
        nameCode: "BROSE",
        family: "Poaceae",
        genus: "Bromus",
        species: "secalinus",
      },
      {
        seedId: "3",
        nameCode: "TRIGA",
        family: "Poaceae",
        genus: "Triticum",
        species: "aestivum",
      },
    ],
  };

  beforeEach(() => {
    // Reset store to initial state
    act(() => {
      useSpeciesStore.setState({
        speciesData: null,
        isLoading: false,
        error: null,
      });
    });
  });

  describe("Initial State", () => {
    it("should have null speciesData", () => {
      expect(useSpeciesStore.getState().speciesData).toBeNull();
    });

    it("should have isLoading false", () => {
      expect(useSpeciesStore.getState().isLoading).toBe(false);
    });

    it("should have null error", () => {
      expect(useSpeciesStore.getState().error).toBeNull();
    });
  });

  describe("setSpeciesData", () => {
    it("should set species data", () => {
      act(() => {
        useSpeciesStore.getState().setSpeciesData(mockSpeciesData);
      });

      expect(useSpeciesStore.getState().speciesData).toEqual(mockSpeciesData);
    });

    it("should clear error when setting species data", () => {
      act(() => {
        useSpeciesStore.getState().setError("Previous error");
        useSpeciesStore.getState().setSpeciesData(mockSpeciesData);
      });

      const state = useSpeciesStore.getState();
      expect(state.speciesData).toEqual(mockSpeciesData);
      expect(state.error).toBeNull();
    });

    it("should update existing species data", () => {
      const updatedData: ApiSpeciesData = {
        seeds: [
          {
            seedId: "4",
            nameCode: "HORVU",
            family: "Poaceae",
            genus: "Hordeum",
            species: "vulgare",
          },
        ],
      };

      act(() => {
        useSpeciesStore.getState().setSpeciesData(mockSpeciesData);
        useSpeciesStore.getState().setSpeciesData(updatedData);
      });

      const state = useSpeciesStore.getState();
      expect(state.speciesData).toEqual(updatedData);
      expect(state.speciesData?.seeds).toHaveLength(1);
    });
  });

  describe("setLoading", () => {
    it("should set loading to true", () => {
      act(() => {
        useSpeciesStore.getState().setLoading(true);
      });

      expect(useSpeciesStore.getState().isLoading).toBe(true);
    });

    it("should set loading to false", () => {
      act(() => {
        useSpeciesStore.getState().setLoading(true);
        useSpeciesStore.getState().setLoading(false);
      });

      expect(useSpeciesStore.getState().isLoading).toBe(false);
    });
  });

  describe("setError", () => {
    it("should set error message", () => {
      act(() => {
        useSpeciesStore.getState().setError("Failed to load species");
      });

      const state = useSpeciesStore.getState();
      expect(state.error).toBe("Failed to load species");
      expect(state.isLoading).toBe(false);
    });

    it("should set loading to false when setting error", () => {
      act(() => {
        useSpeciesStore.getState().setLoading(true);
        useSpeciesStore.getState().setError("Error occurred");
      });

      const state = useSpeciesStore.getState();
      expect(state.isLoading).toBe(false);
      expect(state.error).toBe("Error occurred");
    });

    it("should clear error with null", () => {
      act(() => {
        useSpeciesStore.getState().setError("Error message");
        useSpeciesStore.getState().setError(null);
      });

      expect(useSpeciesStore.getState().error).toBeNull();
    });
  });

  describe("clearSpeciesData", () => {
    it("should clear all state", () => {
      act(() => {
        useSpeciesStore.getState().setSpeciesData(mockSpeciesData);
        useSpeciesStore.getState().setLoading(true);
        useSpeciesStore.getState().setError("Some error");
        useSpeciesStore.getState().clearSpeciesData();
      });

      const state = useSpeciesStore.getState();
      expect(state.speciesData).toBeNull();
      expect(state.error).toBeNull();
      expect(state.isLoading).toBe(false);
    });

    it("should handle clearing when already cleared", () => {
      act(() => {
        useSpeciesStore.getState().clearSpeciesData();
      });

      const state = useSpeciesStore.getState();
      expect(state.speciesData).toBeNull();
      expect(state.error).toBeNull();
      expect(state.isLoading).toBe(false);
    });
  });

  describe("Loading Workflow", () => {
    it("should follow typical loading workflow", () => {
      // Start loading
      act(() => {
        useSpeciesStore.getState().setLoading(true);
      });

      expect(useSpeciesStore.getState().isLoading).toBe(true);

      // Success case
      act(() => {
        useSpeciesStore.getState().setSpeciesData(mockSpeciesData);
        useSpeciesStore.getState().setLoading(false);
      });

      const state = useSpeciesStore.getState();
      expect(state.isLoading).toBe(false);
      expect(state.speciesData).toEqual(mockSpeciesData);
      expect(state.error).toBeNull();
    });

    it("should handle error workflow", () => {
      // Start loading
      act(() => {
        useSpeciesStore.getState().setLoading(true);
      });

      // Error occurs
      act(() => {
        useSpeciesStore.getState().setError("Network error");
      });

      const state = useSpeciesStore.getState();
      expect(state.isLoading).toBe(false);
      expect(state.error).toBe("Network error");
      expect(state.speciesData).toBeNull();
    });
  });

  describe("Edge Cases", () => {
    it("should handle empty seeds array", () => {
      const emptyData: ApiSpeciesData = {
        seeds: [],
      };

      act(() => {
        useSpeciesStore.getState().setSpeciesData(emptyData);
      });

      expect(useSpeciesStore.getState().speciesData?.seeds).toHaveLength(0);
    });

    it("should handle multiple error updates", () => {
      act(() => {
        useSpeciesStore.getState().setError("Error 1");
        useSpeciesStore.getState().setError("Error 2");
        useSpeciesStore.getState().setError("Error 3");
      });

      expect(useSpeciesStore.getState().error).toBe("Error 3");
    });

    it("should handle rapid state changes", () => {
      act(() => {
        useSpeciesStore.getState().setLoading(true);
        useSpeciesStore.getState().setSpeciesData(mockSpeciesData);
        useSpeciesStore.getState().setLoading(false);
        useSpeciesStore.getState().clearSpeciesData();
      });

      const state = useSpeciesStore.getState();
      expect(state.isLoading).toBe(false);
      expect(state.speciesData).toBeNull();
    });
  });
});
