/**
 * Unit tests for seed lookup utility
 */

import { describe, it, expect, beforeEach, vi } from "vitest";
import { getSeedIdByTaxonomy, seedExists, getAllSeeds } from "./seedLookup";
import { useSpeciesStore } from "@stores/useSpeciesStore";
import type { SpeciesData, ApiSpeciesData } from "../common/types";

// Mock the useSpeciesStore module
vi.mock("@stores/useSpeciesStore", () => ({
  useSpeciesStore: {
    getState: vi.fn(),
  },
}));

describe("seedLookup", () => {
  const mockSeeds: SpeciesData[] = [
    {
      seedId: "seed-1",
      family: "Poaceae",
      genus: "Triticum",
      species: "aestivum",
      nameCode: "WHEAT_001",
    },
    {
      seedId: "seed-2",
      family: "Fabaceae",
      genus: "Glycine",
      species: "max",
      nameCode: "SOYBEAN_001",
    },
    {
      seedId: "seed-3",
      family: "Poaceae",
      genus: "Zea",
      species: "mays",
      nameCode: "CORN_001",
    },
  ];

  const mockSpeciesData: ApiSpeciesData = {
    seeds: mockSeeds,
  };

  beforeEach(() => {
    // Reset mocks before each test
    vi.clearAllMocks();
  });

  describe("getSeedIdByTaxonomy", () => {
    it("should return seed_id for valid taxonomy", () => {
      vi.mocked(useSpeciesStore.getState).mockReturnValue({
        speciesData: mockSpeciesData,
        isLoading: false,
        error: null,
        setSpeciesData: vi.fn(),
        setLoading: vi.fn(),
        setError: vi.fn(),
        clearSpeciesData: vi.fn(),
      });

      const result = getSeedIdByTaxonomy({
        family: "Poaceae",
        genus: "Triticum",
        species: "aestivum",
        nameCode: "WHEAT_001",
      });

      expect(result).toBe("seed-1");
    });

    it("should return correct seed_id for different taxonomy", () => {
      vi.mocked(useSpeciesStore.getState).mockReturnValue({
        speciesData: mockSpeciesData,
        isLoading: false,
        error: null,
        setSpeciesData: vi.fn(),
        setLoading: vi.fn(),
        setError: vi.fn(),
        clearSpeciesData: vi.fn(),
      });

      const result = getSeedIdByTaxonomy({
        family: "Fabaceae",
        genus: "Glycine",
        species: "max",
        nameCode: "SOYBEAN_001",
      });

      expect(result).toBe("seed-2");
    });

    it("should throw error if seed data not loaded", () => {
      vi.mocked(useSpeciesStore.getState).mockReturnValue({
        speciesData: null,
        isLoading: false,
        error: null,
        setSpeciesData: vi.fn(),
        setLoading: vi.fn(),
        setError: vi.fn(),
        clearSpeciesData: vi.fn(),
      });

      expect(() =>
        getSeedIdByTaxonomy({
          family: "Poaceae",
          genus: "Triticum",
          species: "aestivum",
          nameCode: "WHEAT_001",
        }),
      ).toThrow("Seed data not loaded");
    });

    it("should throw error if seeds array is missing", () => {
      vi.mocked(useSpeciesStore.getState).mockReturnValue({
        speciesData: {} as ApiSpeciesData,
        isLoading: false,
        error: null,
        setSpeciesData: vi.fn(),
        setLoading: vi.fn(),
        setError: vi.fn(),
        clearSpeciesData: vi.fn(),
      });

      expect(() =>
        getSeedIdByTaxonomy({
          family: "Poaceae",
          genus: "Triticum",
          species: "aestivum",
          nameCode: "WHEAT_001",
        }),
      ).toThrow("Seed data not loaded");
    });

    it("should throw error if seed not found", () => {
      vi.mocked(useSpeciesStore.getState).mockReturnValue({
        speciesData: mockSpeciesData,
        isLoading: false,
        error: null,
        setSpeciesData: vi.fn(),
        setLoading: vi.fn(),
        setError: vi.fn(),
        clearSpeciesData: vi.fn(),
      });

      expect(() =>
        getSeedIdByTaxonomy({
          family: "NonExistent",
          genus: "NonExistent",
          species: "nonexistent",
          nameCode: "NONE_001",
        }),
      ).toThrow(
        "Seed not found: NonExistent NonExistent nonexistent (NONE_001)",
      );
    });

    it("should match exact taxonomy (case-sensitive)", () => {
      vi.mocked(useSpeciesStore.getState).mockReturnValue({
        speciesData: mockSpeciesData,
        isLoading: false,
        error: null,
        setSpeciesData: vi.fn(),
        setLoading: vi.fn(),
        setError: vi.fn(),
        clearSpeciesData: vi.fn(),
      });

      // Wrong case should not match
      expect(() =>
        getSeedIdByTaxonomy({
          family: "poaceae", // lowercase
          genus: "Triticum",
          species: "aestivum",
          nameCode: "WHEAT_001",
        }),
      ).toThrow("Seed not found");
    });
  });

  describe("seedExists", () => {
    it("should return true if seed exists", () => {
      vi.mocked(useSpeciesStore.getState).mockReturnValue({
        speciesData: mockSpeciesData,
        isLoading: false,
        error: null,
        setSpeciesData: vi.fn(),
        setLoading: vi.fn(),
        setError: vi.fn(),
        clearSpeciesData: vi.fn(),
      });

      const result = seedExists({
        family: "Poaceae",
        genus: "Triticum",
        species: "aestivum",
        nameCode: "WHEAT_001",
      });

      expect(result).toBe(true);
    });

    it("should return false if seed not found", () => {
      vi.mocked(useSpeciesStore.getState).mockReturnValue({
        speciesData: mockSpeciesData,
        isLoading: false,
        error: null,
        setSpeciesData: vi.fn(),
        setLoading: vi.fn(),
        setError: vi.fn(),
        clearSpeciesData: vi.fn(),
      });

      const result = seedExists({
        family: "NonExistent",
        genus: "NonExistent",
        species: "nonexistent",
        nameCode: "NONE_001",
      });

      expect(result).toBe(false);
    });

    it("should return false if seed data not loaded", () => {
      vi.mocked(useSpeciesStore.getState).mockReturnValue({
        speciesData: null,
        isLoading: false,
        error: null,
        setSpeciesData: vi.fn(),
        setLoading: vi.fn(),
        setError: vi.fn(),
        clearSpeciesData: vi.fn(),
      });

      const result = seedExists({
        family: "Poaceae",
        genus: "Triticum",
        species: "aestivum",
        nameCode: "WHEAT_001",
      });

      expect(result).toBe(false);
    });
  });

  describe("getAllSeeds", () => {
    it("should return all seeds if data loaded", () => {
      vi.mocked(useSpeciesStore.getState).mockReturnValue({
        speciesData: mockSpeciesData,
        isLoading: false,
        error: null,
        setSpeciesData: vi.fn(),
        setLoading: vi.fn(),
        setError: vi.fn(),
        clearSpeciesData: vi.fn(),
      });

      const result = getAllSeeds();

      expect(result).toEqual(mockSeeds);
      expect(result).toHaveLength(3);
    });

    it("should return empty array if seed data not loaded", () => {
      vi.mocked(useSpeciesStore.getState).mockReturnValue({
        speciesData: null,
        isLoading: false,
        error: null,
        setSpeciesData: vi.fn(),
        setLoading: vi.fn(),
        setError: vi.fn(),
        clearSpeciesData: vi.fn(),
      });

      const result = getAllSeeds();

      expect(result).toEqual([]);
    });

    it("should return empty array if seeds array missing", () => {
      vi.mocked(useSpeciesStore.getState).mockReturnValue({
        speciesData: {} as ApiSpeciesData,
        isLoading: false,
        error: null,
        setSpeciesData: vi.fn(),
        setLoading: vi.fn(),
        setError: vi.fn(),
        clearSpeciesData: vi.fn(),
      });

      const result = getAllSeeds();

      expect(result).toEqual([]);
    });
  });
});
