import { describe, it, expect, beforeEach, vi } from "vitest";
import type { RawImage } from "@huggingface/transformers";
import {
  AutoProcessor,
  AutoModelForObjectDetection,
} from "@huggingface/transformers";
import {
  patchProcessorSize,
  isDetectorReady,
  loadDetector,
  runDetector,
} from "../detector";
import { loadSam3, runSam3, unloadSam3 } from "../sam3";
import type { ModelConfig } from "../models";

// Mock the SAM 3 module — detector.ts delegates to it, we assert the calls.
vi.mock("../sam3", () => ({
  loadSam3: vi.fn(async () => {}),
  runSam3: vi.fn(async () => ({ boxes: [], scores: [], classes: [] })),
  unloadSam3: vi.fn(async () => {}),
}));

// Mock transformers.js so no real model is fetched/instantiated.
vi.mock("@huggingface/transformers", () => ({
  AutoProcessor: { from_pretrained: vi.fn() },
  AutoModelForObjectDetection: { from_pretrained: vi.fn() },
}));

// ---------------------------------------------------------------------------
// Fakes
// ---------------------------------------------------------------------------

// A callable processor with an image_processor sub-object, matching what
// AutoProcessor.from_pretrained returns.
const makeFakeProcessor = () =>
  Object.assign(async () => ({ pixel_values: { dims: [1, 3, 640, 640] } }), {
    image_processor: {
      size: { longest_edge: 640 },
      post_process_object_detection: () => [
        { boxes: [[0.1, 0.1, 0.5, 0.5]], classes: [0], scores: [0.9] },
      ],
    },
  });

// A callable detection model with a config.id2label map and an async dispose().
const makeFakeModel = () =>
  Object.assign(
    async () => ({ logits: { dims: [1, 1, 1], data: new Float32Array([2]) } }),
    { config: { id2label: { 0: "seed" } }, dispose: vi.fn(async () => {}) },
  );

const objConfig = {
  detectorKind: "object-detection",
  detectorModel: "cfia-ai-lab/rtdetr",
  detectorThreshold: 0.3,
} as unknown as ModelConfig;

const sam3Config = {
  detectorKind: "text-promptable-segmentation",
  detectorModel: "cfia-ai-lab/sam3",
  detectorThreshold: 0.5,
} as unknown as ModelConfig;

const fakeRawImage = { width: 1280, height: 640 } as unknown as RawImage;

const callbacks = () => ({
  transformersProgress: vi.fn(),
  sam3Progress: vi.fn(),
});

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(AutoProcessor.from_pretrained).mockResolvedValue(
    makeFakeProcessor(),
  );
  vi.mocked(AutoModelForObjectDetection.from_pretrained).mockResolvedValue(
    makeFakeModel(),
  );
  vi.mocked(loadSam3).mockResolvedValue(undefined);
  vi.mocked(unloadSam3).mockResolvedValue(undefined);
});

// ---------------------------------------------------------------------------
// patchProcessorSize
// ---------------------------------------------------------------------------

describe("patchProcessorSize", () => {
  it("converts {max_height, max_width} to {longest_edge} using the smaller side", () => {
    const proc = {
      image_processor: { size: { max_height: 800, max_width: 600 } },
    };
    patchProcessorSize(proc);
    expect(proc.image_processor.size).toEqual({ longest_edge: 600 });
  });

  it("works when size lives directly on the processor (no image_processor)", () => {
    const proc = { size: { max_height: 500, max_width: 900 } };
    patchProcessorSize(proc);
    expect(proc.size).toEqual({ longest_edge: 500 });
  });

  it("leaves an already-normalized size untouched", () => {
    const proc = { image_processor: { size: { longest_edge: 640 } } };
    patchProcessorSize(proc);
    expect(proc.image_processor.size).toEqual({ longest_edge: 640 });
  });

  it("is a no-op when there is no size", () => {
    const proc = { image_processor: {} };
    expect(() => patchProcessorSize(proc)).not.toThrow();
  });
});

// ---------------------------------------------------------------------------
// loadDetector
// ---------------------------------------------------------------------------

describe("loadDetector", () => {
  it("delegates to loadSam3 for a text-promptable detector", async () => {
    const cb = callbacks();
    await loadDetector(sam3Config, cb);
    expect(loadSam3).toHaveBeenCalledWith(sam3Config, cb.sam3Progress);
    expect(AutoModelForObjectDetection.from_pretrained).not.toHaveBeenCalled();
  });

  it("loads a closed-vocabulary detector and reports it ready", async () => {
    await loadDetector(objConfig, callbacks());
    expect(AutoProcessor.from_pretrained).toHaveBeenCalledWith(
      "cfia-ai-lab/rtdetr",
    );
    expect(AutoModelForObjectDetection.from_pretrained).toHaveBeenCalled();
    expect(isDetectorReady(objConfig)).toBe(true);
  });

  it("unloads SAM 3 BEFORE allocating the closed-vocab detector (OOM guard)", async () => {
    await loadDetector(objConfig, callbacks());
    const unloadOrder = vi.mocked(unloadSam3).mock.invocationCallOrder[0];
    const modelOrder = vi.mocked(AutoModelForObjectDetection.from_pretrained)
      .mock.invocationCallOrder[0];
    expect(unloadOrder).toBeLessThan(modelOrder);
  });

  it("disposes the previous closed-vocab detector's session before switching", async () => {
    const dispose = vi.fn(async () => {});
    const model = Object.assign(
      async () => ({
        logits: { dims: [1, 1, 1], data: new Float32Array([2]) },
      }),
      { config: { id2label: {} }, dispose },
    );
    vi.mocked(
      AutoModelForObjectDetection.from_pretrained,
    ).mockResolvedValueOnce(model);
    await loadDetector(objConfig, callbacks()); // loads `model`
    await loadDetector(sam3Config, callbacks()); // switches away -> disposes it
    expect(dispose).toHaveBeenCalledTimes(1);
  });
});

// ---------------------------------------------------------------------------
// isDetectorReady
// ---------------------------------------------------------------------------

describe("isDetectorReady", () => {
  it("is always true for a text-promptable detector (managed by sam3)", () => {
    expect(isDetectorReady(sam3Config)).toBe(true);
  });

  it("is false for a closed-vocab detector before it is loaded", async () => {
    // Loading a SAM 3 detector clears any closed-vocab model state.
    await loadDetector(sam3Config, callbacks());
    expect(isDetectorReady(objConfig)).toBe(false);
  });
});

// ---------------------------------------------------------------------------
// runDetector
// ---------------------------------------------------------------------------

describe("runDetector", () => {
  it("runs SAM 3 and labels every detection with the prompt", async () => {
    vi.mocked(runSam3).mockResolvedValue({
      boxes: [[1, 2, 3, 4]],
      scores: [0.8],
      classes: [0],
    });
    const { detections, labelForClass } = await runDetector(
      sam3Config,
      "data:image/png;base64,AAAA",
      fakeRawImage,
      "ragweed",
    );
    expect(runSam3).toHaveBeenCalledWith(
      "data:image/png;base64,AAAA",
      "ragweed",
      0.5,
      1280,
      640,
    );
    expect(detections.boxes).toEqual([[1, 2, 3, 4]]);
    expect(labelForClass(0)).toBe("ragweed");
  });

  it("defaults the SAM 3 prompt to 'seed' when none is given", async () => {
    await runDetector(
      sam3Config,
      "data:image/png;base64,AAAA",
      fakeRawImage,
      null,
    );
    expect(runSam3).toHaveBeenCalledWith(
      "data:image/png;base64,AAAA",
      "seed",
      0.5,
      1280,
      640,
    );
  });

  it("scales closed-vocab boxes to original pixel space and maps labels", async () => {
    await loadDetector(objConfig, callbacks());
    const { detections, labelForClass } = await runDetector(
      objConfig,
      "data:image/png;base64,AAAA",
      fakeRawImage,
      undefined,
    );
    // model 640x640, image 1280x640 -> scaleX=2, scaleY=2 (through resized dims).
    // box [0.1,0.1,0.5,0.5] -> [128,128,640,640].
    [128, 128, 640, 640].forEach((v, i) =>
      expect(detections.boxes[0][i]).toBeCloseTo(v, 3),
    );
    expect(labelForClass(0)).toBe("seed");
    expect(labelForClass(99)).toBe("class_99");
  });
});
