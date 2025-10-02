import { create } from "zustand";
import { ApiSpeciesData } from "@common/types";

interface SpeciesState {
  speciesData: ApiSpeciesData | null;
  isLoading: boolean;
  error: string | null;
  setSpeciesData: (data: ApiSpeciesData) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearSpeciesData: () => void;
}

export const useSpeciesStore = create<SpeciesState>((set) => ({
  speciesData: null,
  isLoading: false,
  error: null,
  setSpeciesData: (data) => set({ speciesData: data, error: null }),
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error, isLoading: false }),
  clearSpeciesData: () =>
    set({ speciesData: null, error: null, isLoading: false }),
}));
