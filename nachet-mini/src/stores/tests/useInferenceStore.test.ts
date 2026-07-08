import { describe, it, expect, beforeEach } from "vitest";
import { useInferenceStore, resultKey, boxKey } from "../useInferenceStore";
import type { CamBoxResult } from "../useInferenceStore";
import type { InferenceResult } from "@common/types";

const makeCam = (classCount = 3, grid = 2): CamBoxResult => ({
  grid,
  classes: Array.from({ length: classCount }, (_, i) => ({
    classIndex: i,
    label: `species-${i}`,
    score: 1 - i * 0.1,
    heatmap: Array.from({ length: grid * grid }, () => 0),
  })),
});

const makeResult = (
  overrides: Partial<InferenceResult> = {},
): InferenceResult => ({
  scores: [0.9],
  classifications: ["wheat"],
  boxes: [],
  topN: [],
  overlapping: [],
  overlappingIndices: [],
  labelOccurrence: { wheat: 1 },
  totalBoxes: 1,
  models: [{ name: "model-1", version: "1.0" }],
  completedAt: "2024-01-01T00:00:00Z",
  isActive: true,
  minBoxSize: 10,
  ...overrides,
});

const getInitialState = () => ({
  results: new Map<string, InferenceResult>(),
  camResults: new Map<string, CamBoxResult>(),
  camRank: new Map<string, number>(),
  activeResultKey: null as string | null,
  status: "idle" as const,
  modelLoaded: false,
  modelLoadProgress: null as null,
  error: null as string | null,
});

describe("resultKey", () => {
  it("formats key as imageIndex:modelConfigId", () => {
    expect(resultKey(0, "swin-v2")).toBe("0:swin-v2");
    expect(resultKey(3, "ensemble")).toBe("3:ensemble");
  });

  it("handles index 0 without ambiguity", () => {
    expect(resultKey(0, "model")).toBe("0:model");
    expect(resultKey(10, "model")).toBe("10:model");
  });
});

describe("boxKey", () => {
  it("formats key as imageIndex:modelConfigId:boxId", () => {
    expect(boxKey(0, "swin-v2", "box-1")).toBe("0:swin-v2:box-1");
    expect(boxKey(3, "ensemble", "abc")).toBe("3:ensemble:abc");
  });

  it("shares the result-key prefix so per-box entries sort under their run", () => {
    expect(boxKey(2, "m", "b").startsWith(`${resultKey(2, "m")}:`)).toBe(true);
  });
});

describe("useInferenceStore", () => {
  beforeEach(() => {
    useInferenceStore.setState(getInitialState());
  });

  it("has correct initial state", () => {
    const state = useInferenceStore.getState();
    expect(state.results.size).toBe(0);
    expect(state.camResults.size).toBe(0);
    expect(state.camRank.size).toBe(0);
    expect(state.activeResultKey).toBeNull();
    expect(state.status).toBe("idle");
    expect(state.modelLoaded).toBe(false);
    expect(state.modelLoadProgress).toBeNull();
    expect(state.error).toBeNull();
  });

  describe("setResult / getResult", () => {
    it("stores and retrieves a result", () => {
      const result = makeResult();
      useInferenceStore.getState().setResult(0, "model-a", result);
      expect(useInferenceStore.getState().getResult(0, "model-a")).toEqual(
        result,
      );
    });

    it("overwrites existing result for the same key", () => {
      useInferenceStore
        .getState()
        .setResult(1, "model-a", makeResult({ totalBoxes: 1 }));
      useInferenceStore
        .getState()
        .setResult(1, "model-a", makeResult({ totalBoxes: 5 }));
      expect(
        useInferenceStore.getState().getResult(1, "model-a")?.totalBoxes,
      ).toBe(5);
    });

    it("returns undefined for a missing key", () => {
      expect(
        useInferenceStore.getState().getResult(99, "none"),
      ).toBeUndefined();
    });

    it("stores results for multiple image/model combinations independently", () => {
      useInferenceStore
        .getState()
        .setResult(0, "model-a", makeResult({ totalBoxes: 1 }));
      useInferenceStore
        .getState()
        .setResult(0, "model-b", makeResult({ totalBoxes: 2 }));
      useInferenceStore
        .getState()
        .setResult(1, "model-a", makeResult({ totalBoxes: 3 }));
      expect(useInferenceStore.getState().results.size).toBe(3);
    });
  });

  describe("getResultsForImage", () => {
    it("returns all results for a given image index", () => {
      useInferenceStore
        .getState()
        .setResult(2, "model-a", makeResult({ totalBoxes: 1 }));
      useInferenceStore
        .getState()
        .setResult(2, "model-b", makeResult({ totalBoxes: 2 }));
      useInferenceStore
        .getState()
        .setResult(3, "model-a", makeResult({ totalBoxes: 9 }));
      const results = useInferenceStore.getState().getResultsForImage(2);
      expect(results).toHaveLength(2);
      expect(results.map((r) => r.modelConfigId).sort()).toEqual([
        "model-a",
        "model-b",
      ]);
    });

    it("returns empty array when no results exist for the image", () => {
      useInferenceStore.getState().setResult(0, "model-a", makeResult());
      expect(useInferenceStore.getState().getResultsForImage(5)).toEqual([]);
    });

    it("does not include results from other images", () => {
      useInferenceStore.getState().setResult(10, "model-a", makeResult());
      useInferenceStore.getState().setResult(1, "model-a", makeResult());
      // "10:model-a" must not appear under image index 1
      const results = useInferenceStore.getState().getResultsForImage(1);
      expect(results).toHaveLength(1);
    });
  });

  describe("setActiveResultKey", () => {
    it("sets activeResultKey to a string", () => {
      useInferenceStore.getState().setActiveResultKey("1:model-a");
      expect(useInferenceStore.getState().activeResultKey).toBe("1:model-a");
    });

    it("accepts null to clear selection", () => {
      useInferenceStore.setState({ activeResultKey: "1:model-a" });
      useInferenceStore.getState().setActiveResultKey(null);
      expect(useInferenceStore.getState().activeResultKey).toBeNull();
    });
  });

  describe("removeResultsForImage", () => {
    it("removes all results for the specified image index", () => {
      useInferenceStore.getState().setResult(1, "model-a", makeResult());
      useInferenceStore.getState().setResult(1, "model-b", makeResult());
      useInferenceStore.getState().setResult(2, "model-a", makeResult());
      useInferenceStore.getState().removeResultsForImage(1);
      expect(useInferenceStore.getState().results.size).toBe(1);
      expect(
        useInferenceStore.getState().getResult(2, "model-a"),
      ).toBeDefined();
    });

    it("clears activeResultKey when it belongs to the removed image", () => {
      useInferenceStore.getState().setResult(1, "model-a", makeResult());
      useInferenceStore.setState({ activeResultKey: "1:model-a" });
      useInferenceStore.getState().removeResultsForImage(1);
      expect(useInferenceStore.getState().activeResultKey).toBeNull();
    });

    it("preserves activeResultKey when it belongs to a different image", () => {
      useInferenceStore.getState().setResult(1, "model-a", makeResult());
      useInferenceStore.getState().setResult(2, "model-a", makeResult());
      useInferenceStore.setState({ activeResultKey: "2:model-a" });
      useInferenceStore.getState().removeResultsForImage(1);
      expect(useInferenceStore.getState().activeResultKey).toBe("2:model-a");
    });

    it("is a no-op when no results exist for the image", () => {
      useInferenceStore.getState().setResult(0, "model-a", makeResult());
      useInferenceStore.getState().removeResultsForImage(99);
      expect(useInferenceStore.getState().results.size).toBe(1);
    });

    it("removes CAM results and ranks for the image but keeps others", () => {
      useInferenceStore
        .getState()
        .setCamResult(1, "model-a", "box-1", makeCam());
      useInferenceStore
        .getState()
        .setCamResult(2, "model-a", "box-1", makeCam());
      useInferenceStore.getState().toggleCamRank("1:model-a", 0);
      useInferenceStore.getState().toggleCamRank("2:model-a", 1);
      useInferenceStore.getState().removeResultsForImage(1);
      const state = useInferenceStore.getState();
      expect(state.camResults.has("1:model-a:box-1")).toBe(false);
      expect(state.camResults.has("2:model-a:box-1")).toBe(true);
      expect(state.camRank.has("1:model-a")).toBe(false);
      expect(state.camRank.get("2:model-a")).toBe(1);
    });
  });

  describe("removeResult", () => {
    it("removes the specific result by key", () => {
      useInferenceStore.getState().setResult(0, "model-a", makeResult());
      useInferenceStore.getState().setResult(0, "model-b", makeResult());
      useInferenceStore.getState().removeResult("0:model-a");
      expect(
        useInferenceStore.getState().getResult(0, "model-a"),
      ).toBeUndefined();
      expect(
        useInferenceStore.getState().getResult(0, "model-b"),
      ).toBeDefined();
    });

    it("clears activeResultKey when it matches the removed key", () => {
      useInferenceStore.getState().setResult(0, "model-a", makeResult());
      useInferenceStore.setState({ activeResultKey: "0:model-a" });
      useInferenceStore.getState().removeResult("0:model-a");
      expect(useInferenceStore.getState().activeResultKey).toBeNull();
    });

    it("preserves activeResultKey when it does not match", () => {
      useInferenceStore.getState().setResult(0, "model-a", makeResult());
      useInferenceStore.getState().setResult(0, "model-b", makeResult());
      useInferenceStore.setState({ activeResultKey: "0:model-b" });
      useInferenceStore.getState().removeResult("0:model-a");
      expect(useInferenceStore.getState().activeResultKey).toBe("0:model-b");
    });
  });

  describe("setCamResult", () => {
    it("stores a CAM result under the per-box key", () => {
      const cam = makeCam();
      useInferenceStore.getState().setCamResult(0, "model-a", "box-1", cam);
      expect(
        useInferenceStore.getState().camResults.get("0:model-a:box-1"),
      ).toEqual(cam);
    });

    it("keeps CAM results for different boxes independent", () => {
      useInferenceStore
        .getState()
        .setCamResult(0, "model-a", "box-1", makeCam(2));
      useInferenceStore
        .getState()
        .setCamResult(0, "model-a", "box-2", makeCam(3));
      const cams = useInferenceStore.getState().camResults;
      expect(cams.size).toBe(2);
      expect(cams.get("0:model-a:box-1")?.classes).toHaveLength(2);
      expect(cams.get("0:model-a:box-2")?.classes).toHaveLength(3);
    });

    it("overwrites an existing CAM result for the same box", () => {
      useInferenceStore
        .getState()
        .setCamResult(0, "model-a", "box-1", makeCam(2));
      useInferenceStore
        .getState()
        .setCamResult(0, "model-a", "box-1", makeCam(4));
      expect(
        useInferenceStore.getState().camResults.get("0:model-a:box-1")?.classes,
      ).toHaveLength(4);
    });
  });

  describe("toggleCamRank", () => {
    it("sets the active rank for a run when none is set", () => {
      useInferenceStore.getState().toggleCamRank("0:model-a", 1);
      expect(useInferenceStore.getState().camRank.get("0:model-a")).toBe(1);
    });

    it("clears the rank when the same rank is toggled again", () => {
      useInferenceStore.getState().toggleCamRank("0:model-a", 1);
      useInferenceStore.getState().toggleCamRank("0:model-a", 1);
      expect(useInferenceStore.getState().camRank.has("0:model-a")).toBe(false);
    });

    it("switches to a different rank (single-select) without stacking", () => {
      useInferenceStore.getState().toggleCamRank("0:model-a", 1);
      useInferenceStore.getState().toggleCamRank("0:model-a", 2);
      expect(useInferenceStore.getState().camRank.get("0:model-a")).toBe(2);
      expect(useInferenceStore.getState().camRank.size).toBe(1);
    });

    it("tracks the active rank per run independently", () => {
      useInferenceStore.getState().toggleCamRank("0:model-a", 0);
      useInferenceStore.getState().toggleCamRank("1:model-a", 2);
      expect(useInferenceStore.getState().camRank.get("0:model-a")).toBe(0);
      expect(useInferenceStore.getState().camRank.get("1:model-a")).toBe(2);
    });
  });

  describe("setStatus", () => {
    it.each([
      "idle",
      "loading-model",
      "detecting",
      "classifying",
      "complete",
      "error",
    ] as const)("sets status to '%s'", (status) => {
      useInferenceStore.getState().setStatus(status);
      expect(useInferenceStore.getState().status).toBe(status);
    });
  });

  describe("setModelLoaded", () => {
    it("sets modelLoaded to true", () => {
      useInferenceStore.getState().setModelLoaded(true);
      expect(useInferenceStore.getState().modelLoaded).toBe(true);
    });

    it("sets modelLoaded back to false", () => {
      useInferenceStore.setState({ modelLoaded: true });
      useInferenceStore.getState().setModelLoaded(false);
      expect(useInferenceStore.getState().modelLoaded).toBe(false);
    });
  });

  describe("setModelLoadProgress", () => {
    it("sets progress object", () => {
      const progress = { name: "swin", progress: 0.75 };
      useInferenceStore.getState().setModelLoadProgress(progress);
      expect(useInferenceStore.getState().modelLoadProgress).toEqual(progress);
    });

    it("accepts null to clear progress", () => {
      useInferenceStore.setState({
        modelLoadProgress: { name: "m", progress: 1 },
      });
      useInferenceStore.getState().setModelLoadProgress(null);
      expect(useInferenceStore.getState().modelLoadProgress).toBeNull();
    });
  });

  describe("setError", () => {
    it("sets error message", () => {
      useInferenceStore.getState().setError("inference failed");
      expect(useInferenceStore.getState().error).toBe("inference failed");
    });

    it("accepts null to clear error", () => {
      useInferenceStore.setState({ error: "old error" });
      useInferenceStore.getState().setError(null);
      expect(useInferenceStore.getState().error).toBeNull();
    });
  });

  describe("clearResults", () => {
    it("resets results map, activeResultKey, status, modelLoadProgress, and error", () => {
      useInferenceStore.getState().setResult(0, "model-a", makeResult());
      useInferenceStore.setState({
        activeResultKey: "0:model-a",
        status: "complete",
        modelLoadProgress: { name: "m", progress: 1 },
        error: "oops",
      });
      useInferenceStore
        .getState()
        .setCamResult(0, "model-a", "box-1", makeCam());
      useInferenceStore.getState().toggleCamRank("0:model-a", 0);
      useInferenceStore.getState().clearResults();
      const state = useInferenceStore.getState();
      expect(state.results.size).toBe(0);
      expect(state.camResults.size).toBe(0);
      expect(state.camRank.size).toBe(0);
      expect(state.activeResultKey).toBeNull();
      expect(state.status).toBe("idle");
      expect(state.modelLoadProgress).toBeNull();
      expect(state.error).toBeNull();
    });

    it("does not affect modelLoaded", () => {
      useInferenceStore.setState({ modelLoaded: true });
      useInferenceStore.getState().clearResults();
      expect(useInferenceStore.getState().modelLoaded).toBe(true);
    });
  });
});
