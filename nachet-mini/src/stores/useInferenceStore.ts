import { create } from "zustand";
import { InferenceResult } from "@common/types";

export type InferenceStatus =
  | "idle"
  | "loading-model"
  | "detecting"
  | "classifying"
  | "complete"
  | "error";

export interface ModelLoadProgress {
  name: string;
  progress: number;
}

interface InferenceState {
  results: Map<number, InferenceResult>;
  status: InferenceStatus;
  modelLoadProgress: ModelLoadProgress | null;
  error: string | null;

  setResult: (imageIndex: number, result: InferenceResult) => void;
  getResult: (imageIndex: number) => InferenceResult | undefined;
  setStatus: (status: InferenceStatus) => void;
  setModelLoadProgress: (progress: ModelLoadProgress | null) => void;
  setError: (error: string | null) => void;
  clearResults: () => void;
}

export const useInferenceStore = create<InferenceState>()((set, get) => ({
  results: new Map(),
  status: "idle",
  modelLoadProgress: null,
  error: null,

  setResult: (imageIndex: number, result: InferenceResult) => {
    set((state) => {
      const newMap = new Map(state.results);
      newMap.set(imageIndex, result);
      return { results: newMap };
    });
  },

  getResult: (imageIndex: number) => {
    return get().results.get(imageIndex);
  },

  setStatus: (status: InferenceStatus) => {
    set({ status });
  },

  setModelLoadProgress: (progress: ModelLoadProgress | null) => {
    set({ modelLoadProgress: progress });
  },

  setError: (error: string | null) => {
    set({ error });
  },

  clearResults: () => {
    set({
      results: new Map(),
      status: "idle",
      modelLoadProgress: null,
      error: null,
    });
  },
}));
