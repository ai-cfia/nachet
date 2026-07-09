import { describe, it, expect } from "vitest";
import {
  preprocessImageForSam3,
  SAM3_IMAGE_SIZE,
  SAM3_IMAGE_MEAN,
  SAM3_IMAGE_STD,
  SAM3_PIXEL_TENSOR_LENGTH,
  SAM3_PIXEL_TENSOR_SHAPE,
} from "../sam3Preprocess";

// Build a solid-color source image. Since preprocessImageForSam3 stretches the
// source to fill the whole 1008x1008 canvas, a uniform fill yields a uniform
// output plane per channel — making the normalization math exact to assert.
const solidImage = (
  r: number,
  g: number,
  b: number,
  size = 8,
): OffscreenCanvas => {
  const canvas = new OffscreenCanvas(size, size);
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("no 2d context in test");
  ctx.fillStyle = `rgb(${r}, ${g}, ${b})`;
  ctx.fillRect(0, 0, size, size);
  return canvas;
};

const PLANE = SAM3_IMAGE_SIZE * SAM3_IMAGE_SIZE;
// Sample a middle-ish pixel to avoid any corner rounding from the stretch.
const MID = Math.floor(PLANE / 2);

/** Expected normalized value for a raw 0-255 pixel on a given channel. */
const expected = (pixel: number, channel: number) =>
  (pixel / 255 - SAM3_IMAGE_MEAN[channel]) / SAM3_IMAGE_STD[channel];

describe("sam3Preprocess constants", () => {
  it("targets the baked 1008x1008 size", () => {
    expect(SAM3_IMAGE_SIZE).toBe(1008);
  });

  it("uses ImageNet mean/std", () => {
    expect(SAM3_IMAGE_MEAN).toEqual([0.485, 0.456, 0.406]);
    expect(SAM3_IMAGE_STD).toEqual([0.229, 0.224, 0.225]);
  });

  it("derives tensor length and shape from the image size", () => {
    expect(SAM3_PIXEL_TENSOR_LENGTH).toBe(3 * 1008 * 1008);
    expect(SAM3_PIXEL_TENSOR_SHAPE).toEqual([1, 3, 1008, 1008]);
  });
});

describe("preprocessImageForSam3", () => {
  it("returns an NCHW Float32Array of the expected length", () => {
    const out = preprocessImageForSam3(solidImage(128, 128, 128));
    expect(out).toBeInstanceOf(Float32Array);
    expect(out.length).toBe(SAM3_PIXEL_TENSOR_LENGTH);
  });

  it("normalizes a white image to (1 - mean) / std per channel", () => {
    const out = preprocessImageForSam3(solidImage(255, 255, 255));
    expect(out[MID]).toBeCloseTo(expected(255, 0), 4); // R plane
    expect(out[PLANE + MID]).toBeCloseTo(expected(255, 1), 4); // G plane
    expect(out[2 * PLANE + MID]).toBeCloseTo(expected(255, 2), 4); // B plane
  });

  it("normalizes a black image to -mean / std per channel", () => {
    const out = preprocessImageForSam3(solidImage(0, 0, 0));
    expect(out[MID]).toBeCloseTo(expected(0, 0), 4);
    expect(out[PLANE + MID]).toBeCloseTo(expected(0, 1), 4);
    expect(out[2 * PLANE + MID]).toBeCloseTo(expected(0, 2), 4);
  });

  it("separates channels into planar R,G,B order (HWC -> CHW)", () => {
    // Pure red: R plane should reflect 255, G and B planes reflect 0.
    const out = preprocessImageForSam3(solidImage(255, 0, 0));
    expect(out[MID]).toBeCloseTo(expected(255, 0), 4); // R
    expect(out[PLANE + MID]).toBeCloseTo(expected(0, 1), 4); // G
    expect(out[2 * PLANE + MID]).toBeCloseTo(expected(0, 2), 4); // B
    // Sanity: the three planes are genuinely different values.
    expect(out[MID]).not.toBeCloseTo(out[PLANE + MID], 2);
  });
});
