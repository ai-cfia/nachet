import { create } from "zustand";
import type { InferenceResult } from "@common/types";

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

/** Build the composite key used to store results: "imageIndex:modelConfigId" */
export function resultKey(imageIndex: number, modelConfigId: string): string {
  return `${imageIndex}:${modelConfigId}`;
}

interface InferenceState {
  /** Results keyed by "imageIndex:modelConfigId" */
  results: Map<string, InferenceResult>;
  /** Which result the user is currently viewing */
  activeResultKey: string | null;
  status: InferenceStatus;
  modelLoaded: boolean;
  modelLoadProgress: ModelLoadProgress | null;
  error: string | null;

  setResult: (
    imageIndex: number,
    modelConfigId: string,
    result: InferenceResult,
  ) => void;
  getResult: (
    imageIndex: number,
    modelConfigId: string,
  ) => InferenceResult | undefined;
  getResultsForImage: (
    imageIndex: number,
  ) => Array<{ modelConfigId: string; result: InferenceResult }>;
  setActiveResultKey: (key: string | null) => void;
  removeResultsForImage: (imageIndex: number) => void;
  setStatus: (status: InferenceStatus) => void;
  setModelLoaded: (value: boolean) => void;
  setModelLoadProgress: (progress: ModelLoadProgress | null) => void;
  setError: (error: string | null) => void;
  clearResults: () => void;
}

export const useInferenceStore = create<InferenceState>()((set, get) => ({
  results: new Map(),
  activeResultKey: null,
  status: "idle",
  modelLoaded: false,
  modelLoadProgress: null,
  error: null,

  setResult: (
    imageIndex: number,
    modelConfigId: string,
    result: InferenceResult,
  ) => {
    const key = resultKey(imageIndex, modelConfigId);
    set((state) => {
      const newMap = new Map(state.results);
      newMap.set(key, result);
      return { results: newMap };
    });
  },

  getResult: (imageIndex: number, modelConfigId: string) => {
    return get().results.get(resultKey(imageIndex, modelConfigId));
  },

  getResultsForImage: (imageIndex: number) => {
    const prefix = `${imageIndex}:`;
    const entries: Array<{ modelConfigId: string; result: InferenceResult }> =
      [];
    for (const [key, result] of get().results) {
      if (key.startsWith(prefix)) {
        entries.push({ modelConfigId: key.slice(prefix.length), result });
      }
    }
    return entries;
  },

  setActiveResultKey: (key: string | null) => {
    set({ activeResultKey: key });
  },

  removeResultsForImage: (imageIndex: number) => {
    const prefix = `${imageIndex}:`;
    set((state) => {
      const newMap = new Map(state.results);
      for (const key of newMap.keys()) {
        if (key.startsWith(prefix)) {
          newMap.delete(key);
        }
      }
      const activeKey =
        state.activeResultKey?.startsWith(prefix) === true
          ? null
          : state.activeResultKey;
      return { results: newMap, activeResultKey: activeKey };
    });
  },

  setStatus: (status: InferenceStatus) => {
    set({ status });
  },

  setModelLoaded: (value: boolean) => {
    set({ modelLoaded: value });
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
      activeResultKey: null,
      status: "idle",
      modelLoadProgress: null,
      error: null,
    });
  },
}));
