import { describe, it, expect, vi } from "vitest";
import {
  buildHfUrl,
  onnxUrl,
  onnxDataUrl,
  sanitizeImageSrc,
  bigInt64FromTensor,
  postProcessSam3Detections,
  fetchWithProgress,
  loadSam3,
  unloadSam3,
  runSam3,
} from "../sam3";
import type { ModelConfig } from "../models";

// ---------------------------------------------------------------------------
// URL building (SSRF barrier)
// ---------------------------------------------------------------------------

describe("buildHfUrl", () => {
  it("builds a huggingface.co resolve URL from repo + file + suffix", () => {
    expect(
      buildHfUrl("cfia-ai-lab/sam3-text-onnx", "vision_encoder", ".onnx"),
    ).toBe(
      "https://huggingface.co/cfia-ai-lab/sam3-text-onnx/resolve/main/vision_encoder.onnx",
    );
  });

  it("onnxUrl / onnxDataUrl apply the .onnx and .onnx.data suffixes", () => {
    expect(onnxUrl("owner/repo", "decoder")).toBe(
      "https://huggingface.co/owner/repo/resolve/main/decoder.onnx",
    );
    expect(onnxDataUrl("owner/repo", "decoder")).toBe(
      "https://huggingface.co/owner/repo/resolve/main/decoder.onnx.data",
    );
  });

  it("rejects a repo id that is not owner/name", () => {
    expect(() => buildHfUrl("no-slash", "f", ".onnx")).toThrow();
    expect(() => buildHfUrl("too/many/slashes", "f", ".onnx")).toThrow();
  });

  it("rejects a filename with path traversal or illegal characters", () => {
    expect(() => buildHfUrl("owner/repo", "../secret", ".onnx")).toThrow();
    expect(() => buildHfUrl("owner/repo", "bad name", ".onnx")).toThrow();
  });
});

// ---------------------------------------------------------------------------
// Image source sanitization
// ---------------------------------------------------------------------------

describe("sanitizeImageSrc", () => {
  it.each([
    "blob:https://x/abc",
    "data:image/png;base64,AAAA",
    "/local/path.png",
  ])("accepts safe scheme %s", (src) => {
    expect(sanitizeImageSrc(src)).toBe(src);
  });

  it.each([
    "http://evil.example/x.png",
    "https://evil.example/x.png",
    "javascript:alert(1)",
    "ftp://host/x",
  ])("rejects unsafe scheme %s", (src) => {
    expect(() => sanitizeImageSrc(src)).toThrow();
  });
});

// ---------------------------------------------------------------------------
// BigInt64 coercion for ONNX int64 inputs
// ---------------------------------------------------------------------------

describe("bigInt64FromTensor", () => {
  it("passes a BigInt64Array through unchanged", () => {
    const src = new BigInt64Array([1n, 2n, 3n]);
    expect(bigInt64FromTensor({ data: src })).toBe(src);
  });

  it("converts a number[] to BigInt64Array", () => {
    expect(Array.from(bigInt64FromTensor({ data: [1, 2, 3] }))).toEqual([
      1n,
      2n,
      3n,
    ]);
  });

  it("converts an Int32Array to BigInt64Array", () => {
    const out = bigInt64FromTensor({ data: new Int32Array([4, 5]) });
    expect(out).toBeInstanceOf(BigInt64Array);
    expect(Array.from(out)).toEqual([4n, 5n]);
  });

  it("reads from ort_tensor.data when .data is absent", () => {
    const out = bigInt64FromTensor({
      ort_tensor: { data: new Int32Array([7]) },
    });
    expect(Array.from(out)).toEqual([7n]);
  });

  it("falls back to tolist()", () => {
    const out = bigInt64FromTensor({ tolist: () => [8, 9] });
    expect(Array.from(out)).toEqual([8n, 9n]);
  });

  it("throws on an unsupported data type", () => {
    expect(() => bigInt64FromTensor({ data: "nope" })).toThrow();
  });
});

// ---------------------------------------------------------------------------
// Detection post-processing (sigmoid + threshold + denormalize)
// ---------------------------------------------------------------------------

describe("postProcessSam3Detections", () => {
  it("keeps queries at/above threshold and denormalizes boxes to pixel space", () => {
    const logits = new Float32Array([10, -10]); // sigmoid ~1.0, ~0.0
    const boxes = new Float32Array([0.1, 0.2, 0.3, 0.4, 0, 0, 0, 0]);
    const out = postProcessSam3Detections(boxes, logits, 0.5, 100, 200, 2);

    expect(out.boxes).toHaveLength(1);
    // Float32 inputs carry rounding, so compare with tolerance.
    [10, 40, 30, 80].forEach((v, i) =>
      expect(out.boxes[0][i]).toBeCloseTo(v, 4),
    );
    expect(out.scores[0]).toBeCloseTo(1 / (1 + Math.exp(-10)), 6);
    expect(out.classes).toEqual([0]);
  });

  it("treats a score exactly at the threshold as a keep", () => {
    // logit 0 -> sigmoid 0.5; 0.5 is not < 0.5, so it is kept.
    const out = postProcessSam3Detections(
      new Float32Array([0.5, 0.5, 0.5, 0.5]),
      new Float32Array([0]),
      0.5,
      10,
      10,
      1,
    );
    expect(out.scores).toHaveLength(1);
    expect(out.scores[0]).toBeCloseTo(0.5, 6);
  });

  it("returns empty arrays when nothing clears the threshold", () => {
    const out = postProcessSam3Detections(
      new Float32Array([0, 0, 0, 0]),
      new Float32Array([-5]),
      0.9,
      100,
      100,
      1,
    );
    expect(out.boxes).toHaveLength(0);
    expect(out.scores).toHaveLength(0);
    expect(out.classes).toHaveLength(0);
  });
});

// ---------------------------------------------------------------------------
// Streaming download with progress
// ---------------------------------------------------------------------------

describe("fetchWithProgress", () => {
  const streamResponse = (chunks: Uint8Array[], total: number) => {
    let i = 0;
    return {
      ok: true,
      headers: {
        get: (h: string) =>
          h.toLowerCase() === "content-length" ? String(total) : null,
      },
      body: {
        getReader: () => ({
          read: async () =>
            i < chunks.length
              ? { done: false, value: chunks[i++] }
              : { done: true, value: undefined },
        }),
      },
      arrayBuffer: async () => new ArrayBuffer(total),
    } as unknown as Response;
  };

  it("reports incremental progress and returns the assembled buffer", async () => {
    const chunks = [new Uint8Array([1, 2, 3]), new Uint8Array([4, 5])];
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => streamResponse(chunks, 5)),
    );
    const fractions: number[] = [];
    const buf = await fetchWithProgress("https://x/data", (f) =>
      fractions.push(f),
    );
    expect(new Uint8Array(buf)).toEqual(new Uint8Array([1, 2, 3, 4, 5]));
    expect(fractions).toEqual([0.6, 1]);
    vi.unstubAllGlobals();
  });

  it("falls back to a single read when Content-Length is missing", async () => {
    const resp = {
      ok: true,
      headers: { get: () => null },
      body: {},
      arrayBuffer: async () => new Uint8Array([9, 9]).buffer,
    } as unknown as Response;
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => resp),
    );
    const onProgress = vi.fn();
    const buf = await fetchWithProgress("https://x/data", onProgress);
    expect(new Uint8Array(buf)).toEqual(new Uint8Array([9, 9]));
    expect(onProgress).not.toHaveBeenCalled();
    vi.unstubAllGlobals();
  });

  it("throws on a non-ok response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(
        async () =>
          ({
            ok: false,
            status: 500,
            statusText: "err",
          }) as unknown as Response,
      ),
    );
    await expect(fetchWithProgress("https://x/data")).rejects.toThrow(
      /Failed to fetch/i,
    );
    vi.unstubAllGlobals();
  });
});

// ---------------------------------------------------------------------------
// Public API guards (no ONNX sessions loaded)
// ---------------------------------------------------------------------------

describe("SAM 3 lifecycle guards", () => {
  it("loadSam3 rejects a config that is not text-promptable", async () => {
    const badConfig = {
      detectorKind: "object-detection",
    } as unknown as ModelConfig;
    await expect(loadSam3(badConfig)).rejects.toThrow(/non-text-promptable/i);
  });

  it("runSam3 throws when no sessions are loaded", async () => {
    await expect(
      runSam3("data:image/png;base64,AAAA", "seed", 0.5, 100, 100),
    ).rejects.toThrow(/not loaded/i);
  });

  it("unloadSam3 is a safe no-op when nothing is loaded", async () => {
    await expect(unloadSam3()).resolves.toBeUndefined();
  });
});
