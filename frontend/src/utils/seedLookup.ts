/**
 * Seed Lookup Utility
 *
 * This module provides utilities to map taxonomic fields to seed_id.
 * It uses cached seed data from useSpeciesStore (already populated by useSpeciesData hook).
 */

import { useSpeciesStore } from "@stores/useSpeciesStore";
import { SpeciesData } from "../common/types";

export interface SeedTaxonomy {
  family: string;
  genus: string;
  species: string;
  nameCode: string;
}

/**
 * Get seed_id by taxonomic fields.
 * Uses cached data from useSpeciesStore (already populated by useSpeciesData hook).
 *
 * @param taxonomy - Taxonomic fields to match
 * @returns seed_id string
 * @throws Error if seed not found or data not loaded
 *
 * @example
 * const seedId = getSeedIdByTaxonomy({
 *   family: "Poaceae",
 *   genus: "Triticum",
 *   species: "aestivum",
 *   nameCode: "WHEAT_001"
 * });
 */
export const getSeedIdByTaxonomy = (taxonomy: SeedTaxonomy): string => {
  const { speciesData } = useSpeciesStore.getState(); // Access Zustand store directly

  if (!speciesData || !speciesData.seeds) {
    throw new Error(
      "Seed data not loaded. useSpeciesData hook should populate this automatically.",
    );
  }

  const matchingSeed = speciesData.seeds.find(
    (seed: SpeciesData) =>
      seed.family === taxonomy.family &&
      seed.genus === taxonomy.genus &&
      seed.species === taxonomy.species &&
      seed.name_code === taxonomy.nameCode,
  );

  if (!matchingSeed) {
    throw new Error(
      `Seed not found: ${taxonomy.family} ${taxonomy.genus} ${taxonomy.species} (${taxonomy.nameCode})`,
    );
  }

  return matchingSeed.seed_id;
};

/**
 * Check if seed exists (non-throwing version).
 *
 * @param taxonomy - Taxonomic fields to check
 * @returns true if seed exists, false otherwise
 */
export const seedExists = (taxonomy: SeedTaxonomy): boolean => {
  try {
    getSeedIdByTaxonomy(taxonomy);
    return true;
  } catch {
    return false;
  }
};

/**
 * Get all available seeds from cache.
 *
 * @returns Array of SpeciesData or empty array if not loaded
 */
export const getAllSeeds = (): SpeciesData[] => {
  const { speciesData } = useSpeciesStore.getState();
  return speciesData?.seeds || [];
};
