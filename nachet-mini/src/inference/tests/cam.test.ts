import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { computeCam } from "../cam";

const NUM_CLASSES = 101;
const NUM_FEATURES = 1536;

// A synthetic classifier head: every weight is zero except W[class 0][channel 0]
// = 1. That makes the CAM for class 0 exactly feature channel 0 across tokens,
// so we can predict the normalized output by hand.
const head = new Float32Array(NUM_CLASSES * NUM_FEATURES);
head[0] = 1;

// Build a (tokens x NUM_FEATURES) feature block where only channel 0 carries a
// signal; the value per token is given by `channel0`.
const makeFeatures = (channel0: number[]): Float32Array => {
  const f = new Float32Array(channel0.length * NUM_FEATURES);
  channel0.forEach((v, t) => {
    f[t * NUM_FEATURES] = v;
  });
  return f;
};

// A fresh URL per test keeps computeCam's per-URL head cache from bleeding a
// mocked response from one test into another.
let headUrl = "";
let urlCounter = 0;

beforeEach(() => {
  urlCounter += 1;
  headUrl = `https://huggingface.co/test/model/resolve/main/head-${urlCounter}.bin`;
  // computeCam fetches the head weights by URL and caches them; stub fetch to
  // return our synthetic head instead of hitting Hugging Face.
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async () =>
        ({
          ok: true,
          arrayBuffer: async () => head.buffer,
        }) as unknown as Response,
    ),
  );
});

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("computeCam", () => {
  it("derives the grid side from the token count", async () => {
    const { grid } = await computeCam(
      makeFeatures([0, 0, 0, 0]),
      4,
      NUM_FEATURES,
      [0],
      headUrl,
    );
    expect(grid).toBe(2);
  });

  it("fetches the head weights from the given URL", async () => {
    await computeCam(makeFeatures([0, 1, 2, 3]), 4, NUM_FEATURES, [0], headUrl);
    expect(fetch).toHaveBeenCalledWith(headUrl);
  });

  it("returns one map per requested class index", async () => {
    const { maps } = await computeCam(
      makeFeatures([0, 1, 2, 3]),
      4,
      NUM_FEATURES,
      [0, 0, 0],
      headUrl,
    );
    expect(maps).toHaveLength(3);
    for (const m of maps) expect(m).toHaveLength(4);
  });

  it("computes the per-token contribution and min-max normalizes to [0, 1]", async () => {
    const { maps } = await computeCam(
      makeFeatures([0, 1, 2, 3]),
      4,
      NUM_FEATURES,
      [0],
      headUrl,
    );
    const map = Array.from(maps[0]);
    expect(map[0]).toBeCloseTo(0, 6);
    expect(map[1]).toBeCloseTo(1 / 3, 6);
    expect(map[2]).toBeCloseTo(2 / 3, 6);
    expect(map[3]).toBeCloseTo(1, 6);
  });

  it("normalizes a uniform activation to all zeros (avoids divide-by-zero)", async () => {
    const { maps } = await computeCam(
      makeFeatures([5, 5, 5, 5]),
      4,
      NUM_FEATURES,
      [0],
      headUrl,
    );
    expect(Array.from(maps[0])).toEqual([0, 0, 0, 0]);
  });

  it("returns a blank map for an out-of-range class index", async () => {
    const { maps } = await computeCam(
      makeFeatures([0, 1, 2, 3]),
      4,
      NUM_FEATURES,
      [NUM_CLASSES],
      headUrl,
    );
    expect(Array.from(maps[0])).toEqual([0, 0, 0, 0]);
  });

  it("returns a blank map for a negative class index", async () => {
    const { maps } = await computeCam(
      makeFeatures([0, 1, 2, 3]),
      4,
      NUM_FEATURES,
      [-1],
      headUrl,
    );
    expect(Array.from(maps[0])).toEqual([0, 0, 0, 0]);
  });

  it("coerces BigInt class indices from int64 tensors", async () => {
    const { maps } = await computeCam(
      makeFeatures([0, 1, 2, 3]),
      4,
      NUM_FEATURES,
      [0n as unknown as number],
      headUrl,
    );
    // Same as class 0: normalized channel-0 signal.
    expect(Array.from(maps[0])[3]).toBeCloseTo(1, 6);
  });

  it("rejects when the channel count does not match the head", async () => {
    await expect(
      computeCam(makeFeatures([0, 1, 2, 3]), 4, 1000, [0], headUrl),
    ).rejects.toThrow(/channels/);
  });

  it("rejects when the token count is not a perfect square", async () => {
    await expect(
      computeCam(makeFeatures([0, 1, 2]), 3, NUM_FEATURES, [0], headUrl),
    ).rejects.toThrow(/non-square/);
  });

  it("rejects when the head weights fail to download", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({ ok: false, status: 404 }) as unknown as Response),
    );
    await expect(
      computeCam(makeFeatures([0, 1, 2, 3]), 4, NUM_FEATURES, [0], headUrl),
    ).rejects.toThrow(/HTTP 404/);
  });

  it("retries the download after a failed fetch (does not cache the failure)", async () => {
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce({ ok: false, status: 503 } as unknown as Response)
      .mockResolvedValue({
        ok: true,
        arrayBuffer: async () => head.buffer,
      } as unknown as Response);
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      computeCam(makeFeatures([0, 1, 2, 3]), 4, NUM_FEATURES, [0], headUrl),
    ).rejects.toThrow(/HTTP 503/);
    // A second call re-fetches rather than reusing the cached rejection.
    const { maps } = await computeCam(
      makeFeatures([0, 1, 2, 3]),
      4,
      NUM_FEATURES,
      [0],
      headUrl,
    );
    expect(Array.from(maps[0])[3]).toBeCloseTo(1, 6);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });
});
