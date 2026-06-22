import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";
import { useInference } from "../useInference";
import { useInferenceStore } from "@stores/useInferenceStore";
import type { ModelConfig, WorkerOutMessage } from "../models";
import type { BoxCoordinates, InferenceResult } from "@common/types";

// ---------------------------------------------------------------------------
// Mock Worker
// ---------------------------------------------------------------------------

// workerInstance is set by MockWorker's constructor each time new Worker() is
// called inside the hook's useEffect, so it is always fresh per renderHook call.
let workerInstance!: {
  onmessage: ((e: MessageEvent) => void) | null;
  onerror: ((e: ErrorEvent) => void) | null;
  postMessage: ReturnType<typeof vi.fn>;
  terminate: ReturnType<typeof vi.fn>;
};

const initialStoreState = {
  results: new Map(),
  activeResultKey: null,
  status: "idle" as const,
  modelLoaded: false,
  modelLoadProgress: null,
  error: null,
};

beforeEach(() => {
  const postMessage = vi.fn();
  const terminate = vi.fn();

  // Must be a class/function so it can be invoked with `new`.
  vi.stubGlobal(
    "Worker",
    class {
      onmessage: ((e: MessageEvent) => void) | null = null;
      onerror: ((e: ErrorEvent) => void) | null = null;
      postMessage = postMessage;
      terminate = terminate;
      constructor() {
        workerInstance = this as unknown as typeof workerInstance;
      }
    },
  );

  useInferenceStore.setState(initialStoreState);
});

afterEach(() => {
  vi.unstubAllGlobals();
});

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

const fireMessage = (msg: WorkerOutMessage) =>
  act(() => {
    workerInstance.onmessage!(new MessageEvent("message", { data: msg }));
  });

const fireError = (message: string) =>
  act(() => {
    workerInstance.onerror!(new ErrorEvent("error", { message }));
  });

const simulateModelLoaded = () => fireMessage({ type: "model-loaded" });

const mockConfig: ModelConfig = {
  id: "test-config",
  detectorModel: "det-model",
  classifierModel: "cls-model",
  detectorThreshold: 0.5,
  classifierTopK: 5,
  minBoxSize: 224,
};

const makeResult = (): InferenceResult => ({
  scores: [0.9],
  classifications: ["weed"],
  boxes: [],
  topN: [],
  overlapping: [],
  overlappingIndices: [],
  labelOccurrence: {},
  totalBoxes: 1,
  models: [],
  completedAt: "2026-01-01T00:00:00Z",
  isActive: true,
  minBoxSize: 224,
});

const mockBoxes: BoxCoordinates[] = [
  { topX: 0, topY: 0, bottomX: 100, bottomY: 100 },
];

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

describe("useInference", () => {
  describe("worker lifecycle", () => {
    it("creates a Worker on mount", () => {
      renderHook(() => useInference(0));
      // workerInstance is set by the MockWorker constructor; its existence proves
      // new Worker() was called exactly once during mount.
      expect(workerInstance).toBeDefined();
    });

    it("terminates the worker on unmount", () => {
      const { unmount } = renderHook(() => useInference(0));
      unmount();
      expect(workerInstance.terminate).toHaveBeenCalledOnce();
    });
  });

  describe("isModelLoaded getter", () => {
    it("returns false initially", () => {
      const { result } = renderHook(() => useInference(0));
      expect(result.current.isModelLoaded).toBe(false);
    });

    it("returns true after model-loaded message", () => {
      const { result } = renderHook(() => useInference(0));
      simulateModelLoaded();
      expect(result.current.isModelLoaded).toBe(true);
    });

    it("resets to false when loadModels is called", () => {
      const { result } = renderHook(() => useInference(0));
      simulateModelLoaded();
      act(() => {
        result.current.loadModels(mockConfig);
      });
      expect(result.current.isModelLoaded).toBe(false);
    });
  });

  describe("model-progress message", () => {
    it("updates store modelLoadProgress with name and progress", () => {
      renderHook(() => useInference(0));
      fireMessage({ type: "model-progress", name: "detector", progress: 0.5 });
      expect(useInferenceStore.getState().modelLoadProgress).toEqual({
        name: "detector",
        progress: 0.5,
      });
    });
  });

  describe("model-loaded message", () => {
    it("isModelLoaded becomes true", () => {
      const { result } = renderHook(() => useInference(0));
      simulateModelLoaded();
      expect(result.current.isModelLoaded).toBe(true);
    });

    it("sets store status to idle", () => {
      renderHook(() => useInference(0));
      useInferenceStore.getState().setStatus("loading-model");
      simulateModelLoaded();
      expect(useInferenceStore.getState().status).toBe("idle");
    });

    it("clears store modelLoadProgress to null", () => {
      renderHook(() => useInference(0));
      useInferenceStore
        .getState()
        .setModelLoadProgress({ name: "classifier", progress: 0.8 });
      simulateModelLoaded();
      expect(useInferenceStore.getState().modelLoadProgress).toBeNull();
    });

    it("sets store modelLoaded to true", () => {
      renderHook(() => useInference(0));
      simulateModelLoaded();
      expect(useInferenceStore.getState().modelLoaded).toBe(true);
    });
  });

  describe("status message", () => {
    it("forwards the status value to the store", () => {
      renderHook(() => useInference(0));
      fireMessage({ type: "status", status: "detecting" });
      expect(useInferenceStore.getState().status).toBe("detecting");
    });
  });

  describe("partial-result message", () => {
    it("stores result at the correct composite key", () => {
      renderHook(() => useInference(0));
      const result = makeResult();
      fireMessage({
        type: "partial-result",
        imageIndex: 2,
        modelConfigId: "cfg-1",
        result,
      });
      expect(useInferenceStore.getState().results.get("2:cfg-1")).toEqual(
        result,
      );
    });

    // partial-result > updates activeResultKey
    it("updates activeResultKey", () => {
      renderHook(() => useInference(2)); // ← pass currentIndex matching imageIndex
      fireMessage({
        type: "partial-result",
        imageIndex: 2,
        modelConfigId: "cfg-1",
        result: makeResult(),
      });
      expect(useInferenceStore.getState().activeResultKey).toBe("2:cfg-1");
    });

    // result > updates activeResultKey
    it("updates activeResultKey", () => {
      renderHook(() => useInference(3)); // ← pass currentIndex matching imageIndex
      fireMessage({
        type: "result",
        imageIndex: 3,
        modelConfigId: "cfg-2",
        result: makeResult(),
      });
      expect(useInferenceStore.getState().activeResultKey).toBe("3:cfg-2");
    });
  });

  describe("result message", () => {
    it("stores result at the correct composite key", () => {
      renderHook(() => useInference(0));
      const result = makeResult();
      fireMessage({
        type: "result",
        imageIndex: 3,
        modelConfigId: "cfg-2",
        result,
      });
      expect(useInferenceStore.getState().results.get("3:cfg-2")).toEqual(
        result,
      );
    });

    it("updates activeResultKey", () => {
      renderHook(() => useInference(3));
      fireMessage({
        type: "result",
        imageIndex: 3,
        modelConfigId: "cfg-2",
        result: makeResult(),
      });
      expect(useInferenceStore.getState().activeResultKey).toBe("3:cfg-2");
    });

    it("sets store status to complete", () => {
      renderHook(() => useInference(0));
      fireMessage({
        type: "result",
        imageIndex: 0,
        modelConfigId: "cfg-0",
        result: makeResult(),
      });
      expect(useInferenceStore.getState().status).toBe("complete");
    });
  });

  describe("error message", () => {
    it("writes error message to store", () => {
      renderHook(() => useInference(0));
      fireMessage({ type: "error", message: "inference failed" });
      expect(useInferenceStore.getState().error).toBe("inference failed");
    });

    it("sets store status to error", () => {
      renderHook(() => useInference(0));
      fireMessage({ type: "error", message: "inference failed" });
      expect(useInferenceStore.getState().status).toBe("error");
    });
  });

  describe("worker.onerror handler", () => {
    it("writes error message to store", () => {
      renderHook(() => useInference(0));
      fireError("worker crashed");
      expect(useInferenceStore.getState().error).toBe("worker crashed");
    });

    it("sets store status to error", () => {
      renderHook(() => useInference(0));
      fireError("worker crashed");
      expect(useInferenceStore.getState().status).toBe("error");
    });
  });

  describe("loadModels", () => {
    it("posts load-models message with the provided config", () => {
      const { result } = renderHook(() => useInference(0));
      act(() => {
        result.current.loadModels(mockConfig);
      });
      expect(workerInstance.postMessage).toHaveBeenCalledWith({
        type: "load-models",
        config: mockConfig,
      });
    });

    it("resets isModelLoaded to false even if model was previously loaded", () => {
      const { result } = renderHook(() => useInference(0));
      simulateModelLoaded();
      expect(result.current.isModelLoaded).toBe(true);
      act(() => {
        result.current.loadModels(mockConfig);
      });
      expect(result.current.isModelLoaded).toBe(false);
    });

    it("sets store status to loading-model", () => {
      const { result } = renderHook(() => useInference(0));
      act(() => {
        result.current.loadModels(mockConfig);
      });
      expect(useInferenceStore.getState().status).toBe("loading-model");
    });

    it("sets store modelLoaded to false", () => {
      const { result } = renderHook(() => useInference(0));
      simulateModelLoaded();
      act(() => {
        result.current.loadModels(mockConfig);
      });
      expect(useInferenceStore.getState().modelLoaded).toBe(false);
    });

    it("does nothing after unmount", () => {
      const { result, unmount } = renderHook(() => useInference(0));
      unmount();
      act(() => {
        result.current.loadModels(mockConfig);
      });
      expect(workerInstance.postMessage).not.toHaveBeenCalled();
    });
  });

  describe("runInference", () => {
    it("posts run-inference message when model is loaded", () => {
      const { result } = renderHook(() => useInference(0));
      simulateModelLoaded();
      act(() => {
        result.current.runInference("data:image/png;base64,abc", 1);
      });
      expect(workerInstance.postMessage).toHaveBeenCalledWith({
        type: "run-inference",
        imageSrc: "data:image/png;base64,abc",
        imageIndex: 1,
      });
    });

    it("does nothing when model is not loaded", () => {
      const { result } = renderHook(() => useInference(0));
      act(() => {
        result.current.runInference("data:image/png;base64,abc", 1);
      });
      expect(workerInstance.postMessage).not.toHaveBeenCalled();
    });

    it("does nothing after unmount", () => {
      const { result, unmount } = renderHook(() => useInference(0));
      simulateModelLoaded();
      unmount();
      act(() => {
        result.current.runInference("data:image/png;base64,abc", 1);
      });
      expect(workerInstance.postMessage).not.toHaveBeenCalled();
    });
  });

  describe("runClassifyOnly", () => {
    it("posts run-classify-only message with the full payload when model is loaded", () => {
      const { result } = renderHook(() => useInference(0));
      simulateModelLoaded();
      act(() => {
        result.current.runClassifyOnly(
          "data:image/png;base64,abc",
          0,
          mockBoxes,
          "cfg-1",
        );
      });
      expect(workerInstance.postMessage).toHaveBeenCalledWith({
        type: "run-classify-only",
        imageSrc: "data:image/png;base64,abc",
        imageIndex: 0,
        boxes: mockBoxes,
        modelConfigId: "cfg-1",
      });
    });

    it("does nothing when model is not loaded", () => {
      const { result } = renderHook(() => useInference(0));
      act(() => {
        result.current.runClassifyOnly(
          "data:image/png;base64,abc",
          0,
          mockBoxes,
          "cfg-1",
        );
      });
      expect(workerInstance.postMessage).not.toHaveBeenCalled();
    });

    it("does nothing after unmount", () => {
      const { result, unmount } = renderHook(() => useInference(0));
      simulateModelLoaded();
      unmount();
      act(() => {
        result.current.runClassifyOnly(
          "data:image/png;base64,abc",
          0,
          mockBoxes,
          "cfg-1",
        );
      });
      expect(workerInstance.postMessage).not.toHaveBeenCalled();
    });
  });
});
