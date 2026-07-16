import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { computeCam } from "../cam";

const NUM_CLASSES = 101;
const NUM_FEATURES = 1536;

// A synthetic classifier head: class 0 reads feature channel 0, class 1 reads
// channel 1 (all other weights zero). So each class's CAM is exactly that one
// feature channel across tokens, and we can predict the output by hand.
const head = new Float32Array(NUM_CLASSES * NUM_FEATURES);
head[0] = 1; // W[class 0][channel 0]
head[NUM_FEATURES + 1] = 1; // W[class 1][channel 1]

// Build a (tokens x NUM_FEATURES) feature block where only channel 0 carries a
// signal; the value per token is given by `channel0`.
const makeFeatures = (channel0: number[]): Float32Array => {
  const f = new Float32Array(channel0.length * NUM_FEATURES);
  channel0.forEach((v, t) => {
    f[t * NUM_FEATURES] = v;
  });
  return f;
};

// Build features that carry a signal in specific channels (others zero), one
// value per token — lets class 0 (channel 0) and class 1 (channel 1) be driven
// independently to exercise the shared cross-class scale.
const makeChannelFeatures = (
  perChannel: Record<number, number[]>,
): Float32Array => {
  const tokens = Math.max(...Object.values(perChannel).map((a) => a.length));
  const f = new Float32Array(tokens * NUM_FEATURES);
  for (const [ch, vals] of Object.entries(perChannel)) {
    vals.forEach((v, t) => {
      f[t * NUM_FEATURES + Number(ch)] = v;
    });
  }
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

  it("normalizes non-negative contributions to [0, 1]", async () => {
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

  it("scales by the max without subtracting a min (preserves magnitude)", async () => {
    // [2,3,4,5] → /max(5) → [0.4, 0.6, 0.8, 1]. No min subtraction, so a map
    // that never drops near zero stays warm across the board.
    const { maps } = await computeCam(
      makeFeatures([2, 3, 4, 5]),
      4,
      NUM_FEATURES,
      [0],
      headUrl,
    );
    const map = Array.from(maps[0]);
    expect(map[0]).toBeCloseTo(0.4, 6);
    expect(map[1]).toBeCloseTo(0.6, 6);
    expect(map[2]).toBeCloseTo(0.8, 6);
    expect(map[3]).toBeCloseTo(1, 6);
  });

  it("shares one scale across the top-k maps so weaker classes read dim", async () => {
    // class 0 has a strong patch (10), class 1 a weak one (2). With a shared
    // scale, class 1 must not saturate to 1 — it stays proportionally dim
    // (2/10 = 0.2) rather than each map filling [0, 1] on its own.
    const features = makeChannelFeatures({ 0: [0, 10, 0, 0], 1: [0, 0, 2, 0] });
    const { maps } = await computeCam(
      features,
      4,
      NUM_FEATURES,
      [0, 1],
      headUrl,
    );
    expect(Array.from(maps[0])).toEqual([0, 1, 0, 0]);
    expect(maps[1][2]).toBeCloseTo(0.2, 6);
    expect(maps[1][0]).toBeCloseTo(0, 6);
  });

  it("ReLUs all-negative contributions to a blank (all-cold) map", async () => {
    // Every token lowers the class score; none positively supports it, so the
    // map must be all zeros (blue) rather than stretching the least-negative
    // token to red as min-max normalization would.
    const { maps } = await computeCam(
      makeFeatures([-5, -3, -1, -2]),
      4,
      NUM_FEATURES,
      [0],
      headUrl,
    );
    expect(Array.from(maps[0])).toEqual([0, 0, 0, 0]);
  });

  it("keeps only positive support for mixed contributions", async () => {
    // [-2, 0, 3, 6] → ReLU [0, 0, 3, 6] → /max(6) → [0, 0, 0.5, 1].
    const { maps } = await computeCam(
      makeFeatures([-2, 0, 3, 6]),
      4,
      NUM_FEATURES,
      [0],
      headUrl,
    );
    const map = Array.from(maps[0]);
    expect(map[0]).toBeCloseTo(0, 6);
    expect(map[1]).toBeCloseTo(0, 6);
    expect(map[2]).toBeCloseTo(0.5, 6);
    expect(map[3]).toBeCloseTo(1, 6);
  });

  it("maps uniform positive support to a uniformly hot map", async () => {
    // Every token equals the max → all 1. (The divide-by-zero guard only kicks
    // in when nothing is positive; the all-negative case above covers that.)
    const { maps } = await computeCam(
      makeFeatures([5, 5, 5, 5]),
      4,
      NUM_FEATURES,
      [0],
      headUrl,
    );
    expect(Array.from(maps[0])).toEqual([1, 1, 1, 1]);
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
