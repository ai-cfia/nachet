import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import type { ModelConfig } from "../models";

// Shared handle to the ORT sessions the mock creates, in creation order
// (vision, text, decoder) — lets us assert the vision cache behavior.
const hoisted = vi.hoisted(() => ({
  sessions: [] as Array<{
    run: ReturnType<typeof vi.fn>;
    release: ReturnType<typeof vi.fn>;
  }>,
}));

// Mock onnxruntime-web: no real graph, sessions return shape-correct outputs.
vi.mock("onnxruntime-web", () => {
  class Tensor {
    type: string;
    data: unknown;
    dims: number[];
    constructor(type: string, data: unknown, dims: number[]) {
      this.type = type;
      this.data = data;
      this.dims = dims;
    }
  }
  return {
    Tensor,
    env: { logLevel: "warning" },
    InferenceSession: {
      create: vi.fn(async () => {
        const session = {
          release: vi.fn(async () => {}),
          run: vi.fn(async (feed: Record<string, unknown>) => {
            if ("pixel_values" in feed) {
              return {
                fpn_hidden_state_0: {},
                fpn_hidden_state_1: {},
                fpn_hidden_state_2: {},
                fpn_position_encoding_2: {},
              };
            }
            if ("input_ids" in feed) return { text_features: {} };
            // decoder: query 0 has a strong logit + a box, rest are zeros.
            const logits = new Float32Array(200);
            logits[0] = 10;
            const boxes = new Float32Array(800);
            boxes.set([0.1, 0.1, 0.5, 0.5], 0);
            return {
              pred_boxes: { data: boxes },
              pred_logits: { data: logits },
            };
          }),
        };
        hoisted.sessions.push(session);
        return session;
      }),
    },
  };
});

// Mock the tokenizer so no network/model is needed.
vi.mock("@huggingface/transformers", () => ({
  AutoTokenizer: {
    from_pretrained: vi.fn(async () => () => ({
      input_ids: { data: new BigInt64Array(32) },
      attention_mask: { data: new BigInt64Array(32) },
    })),
  },
}));

import { loadSam3, runSam3, unloadSam3 } from "../sam3";

const config = {
  detectorKind: "text-promptable-segmentation",
  detectorModel: "cfia-ai-lab/sam3",
  detectorComponentFiles: {
    vision: "vision_encoder",
    text: "text_encoder",
    decoder: "decoder",
  },
} as unknown as ModelConfig;

const IMG = "blob:test-image";

/** Build a small, genuinely decodable PNG blob for the vision path. */
const makeImageBlob = async (): Promise<Blob> => {
  const canvas = new OffscreenCanvas(4, 4);
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("no 2d context in test");
  ctx.fillStyle = "rgb(120, 40, 200)";
  ctx.fillRect(0, 0, 4, 4);
  return canvas.convertToBlob({ type: "image/png" });
};

beforeEach(async () => {
  hoisted.sessions.length = 0;
  const imageBlob = await makeImageBlob();
  // Return 404 for the HF external-data HEAD probe (weights are "inline"),
  // and serve the decodable image blob for the image fetch.
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: unknown) => {
      if (typeof url === "string" && url.includes("huggingface.co")) {
        return {
          ok: false,
          status: 404,
          headers: { get: () => null },
        } as unknown as Response;
      }
      return { ok: true, blob: async () => imageBlob } as unknown as Response;
    }),
  );
});

afterEach(async () => {
  await unloadSam3();
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});

describe("SAM 3 pipeline (mocked ORT)", () => {
  it("loads all three ONNX components and reports progress", async () => {
    const progress = vi.fn();
    await loadSam3(config, progress);
    expect(hoisted.sessions).toHaveLength(3);
    expect(progress).toHaveBeenCalledWith({
      name: "sam3 vision encoder",
      progress: 100,
    });
    expect(progress).toHaveBeenCalledWith({
      name: "sam3 decoder",
      progress: 100,
    });
  });

  it("runs the full pipeline and returns denormalized detections", async () => {
    await loadSam3(config);
    const res = await runSam3(IMG, "seed", 0.6, 100, 200);
    expect(res.boxes).toHaveLength(1);
    expect(res.boxes[0][0]).toBeCloseTo(10, 3); // 0.1 * width(100)
    expect(res.boxes[0][1]).toBeCloseTo(20, 3); // 0.1 * height(200)
    expect(res.scores[0]).toBeCloseTo(1 / (1 + Math.exp(-10)), 5);
  });

  it("reuses cached vision features for a repeated image", async () => {
    await loadSam3(config);
    const visionSession = hoisted.sessions[0];
    await runSam3(IMG, "seed", 0.6, 100, 200);
    await runSam3(IMG, "different prompt", 0.6, 100, 200);
    // Vision encoder runs once; the second call hits the cache.
    expect(visionSession.run).toHaveBeenCalledTimes(1);
  });

  it("releases sessions on unload", async () => {
    await loadSam3(config);
    const sessions = [...hoisted.sessions];
    await unloadSam3();
    for (const s of sessions) expect(s.release).toHaveBeenCalled();
  });
});
