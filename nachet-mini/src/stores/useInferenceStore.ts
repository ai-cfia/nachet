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
export const resultKey = (imageIndex: number, modelConfigId: string): string =>
  `${imageIndex}:${modelConfigId}`;

/** Per-box key: "imageIndex:modelConfigId:boxId" */
export const boxKey = (
  imageIndex: number,
  modelConfigId: string,
  boxId: string,
): string => `${resultKey(imageIndex, modelConfigId)}:${boxId}`;

/** One top-K class's CAM for a box. */
export interface CamClass {
  classIndex: number;
  label: string;
  score: number;
  /** grid*grid floats in [0, 1] (row-major). */
  heatmap: number[];
}

/** Class Activation Maps for one classified box. */
export interface CamBoxResult {
  /** spatial grid side (e.g. 12 → 12×12). */
  grid: number;
  /** one entry per top-K class. */
  classes: CamClass[];
}

interface InferenceState {
  /** Results keyed by "imageIndex:modelConfigId" */
  results: Map<string, InferenceResult>;
  /** CAM maps keyed by "imageIndex:modelConfigId:boxId" */
  camResults: Map<string, CamBoxResult>;
  /**
   * Which prediction rank's CAM is overlaid, per run. Keyed by the result key
   * "imageIndex:modelConfigId" → rank index (0 = top-1, 1 = top-2, …). One rank
   * at a time (single-select); when set, every seed of that run shows its own
   * rank-N species map. Absent = no overlay.
   */
  camRank: Map<string, number>;
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
  setCamResult: (
    imageIndex: number,
    modelConfigId: string,
    boxId: string,
    cam: CamBoxResult,
  ) => void;
  /** Toggle a prediction rank's CAM overlay for a run (clears it if on). */
  toggleCamRank: (resultKey: string, rank: number) => void;
  setActiveResultKey: (key: string | null) => void;
  removeResultsForImage: (imageIndex: number) => void;
  removeResult: (key: string) => void;
  setStatus: (status: InferenceStatus) => void;
  setModelLoaded: (value: boolean) => void;
  setModelLoadProgress: (progress: ModelLoadProgress | null) => void;
  setError: (error: string | null) => void;
  clearResults: () => void;
}

export const useInferenceStore = create<InferenceState>()((set, get) => ({
  results: new Map(),
  camResults: new Map(),
  camRank: new Map(),
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

  setCamResult: (
    imageIndex: number,
    modelConfigId: string,
    boxId: string,
    cam: CamBoxResult,
  ) => {
    const key = boxKey(imageIndex, modelConfigId, boxId);
    set((state) => {
      const newMap = new Map(state.camResults);
      newMap.set(key, cam);
      return { camResults: newMap };
    });
  },

  toggleCamRank: (key: string, rank: number) => {
    set((state) => {
      const next = new Map(state.camRank);
      if (next.get(key) === rank) next.delete(key);
      else next.set(key, rank);
      return { camRank: next };
    });
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
      const newCam = new Map(state.camResults);
      for (const key of newCam.keys()) {
        if (key.startsWith(prefix)) {
          newCam.delete(key);
        }
      }
      const newRank = new Map(state.camRank);
      for (const key of newRank.keys()) {
        if (key.startsWith(prefix)) {
          newRank.delete(key);
        }
      }
      const activeKey =
        state.activeResultKey?.startsWith(prefix) === true
          ? null
          : state.activeResultKey;
      return {
        results: newMap,
        camResults: newCam,
        camRank: newRank,
        activeResultKey: activeKey,
      };
    });
  },

  removeResult: (key: string) => {
    set((state) => {
      const newMap = new Map(state.results);
      newMap.delete(key);
      // Also drop this run's CAM state, keyed by the "<resultKey>:<boxId>"
      // prefix (maps) and the resultKey itself (overlaid rank). Box ids are
      // reused across runs, so leaving these behind could resurface a stale
      // heatmap or overlay. Mirrors removeResultsForImage.
      const prefix = `${key}:`;
      const newCam = new Map(state.camResults);
      for (const camKey of newCam.keys()) {
        if (camKey.startsWith(prefix)) newCam.delete(camKey);
      }
      const newRank = new Map(state.camRank);
      newRank.delete(key);
      const activeKey =
        state.activeResultKey === key ? null : state.activeResultKey;
      return {
        results: newMap,
        camResults: newCam,
        camRank: newRank,
        activeResultKey: activeKey,
      };
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
      camResults: new Map(),
      camRank: new Map(),
      activeResultKey: null,
      status: "idle",
      modelLoadProgress: null,
      error: null,
    });
  },
}));
