/**
 * Model Store (Zustand)
 *
 * Global state management for ML model selection and metadata.
 * Manages available models, selected model, and loading state.
 */

import { create } from "zustand";
import { ModelMetadata } from "@common/types";

interface ModelState {
  selectedModel: string;
  metadata: ModelMetadata[];
  isLoading: boolean;

  setSelectedModel: (model: string) => void;
  setMetadata: (metadata: ModelMetadata[]) => void;
  setLoading: (loading: boolean) => void;
}

export const useModelStore = create<ModelState>((set) => ({
  selectedModel: "Swin transformer",
  metadata: [],
  isLoading: false,

  setSelectedModel: (model) => set({ selectedModel: model }),
  setMetadata: (metadata) => set({ metadata }),
  setLoading: (loading) => set({ isLoading: loading }),
}));
