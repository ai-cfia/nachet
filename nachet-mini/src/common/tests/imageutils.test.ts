// @vitest-environment jsdom
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  getScaledBounds,
  getUnscaledCoordinates,
  getImageDimensions,
  validateImageFile,
} from "../imageutils";
import type { BoxCoordinates } from "../types";

// ---------------------------------------------------------------------------
// MockImage factory — lets each test control dimensions and success/failure
// ---------------------------------------------------------------------------
let mockNaturalWidth = 1920;
let mockNaturalHeight = 1080;
let mockImageShouldFail = false;

class MockImage {
  naturalWidth = mockNaturalWidth;
  naturalHeight = mockNaturalHeight;
  onload: (() => void) | null = null;
  onerror: (() => void) | null = null;

  set src(_: string) {
    this.naturalWidth = mockNaturalWidth;
    this.naturalHeight = mockNaturalHeight;
    Promise.resolve().then(() => {
      if (mockImageShouldFail) this.onerror?.();
      else this.onload?.();
    });
  }
}

beforeEach(() => {
  mockNaturalWidth = 1920;
  mockNaturalHeight = 1080;
  mockImageShouldFail = false;
  vi.stubGlobal("Image", MockImage);
  vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:mock-url");
  vi.spyOn(URL, "revokeObjectURL").mockImplementation(() => {});
});

afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

// ---------------------------------------------------------------------------
// getScaledBounds
// ---------------------------------------------------------------------------
describe("getScaledBounds", () => {
  const box: BoxCoordinates = { topX: 100, topY: 50, bottomX: 300, bottomY: 150 };

  it("scales correctly when width is the limiting dimension", () => {
    // Container 800×600, image 1600×600 → scaleFactor = 800/1600 = 0.5
    // displayedWidth=800, displayedHeight=300, offsetX=0, offsetY=150
    const result = getScaledBounds(800, 600, 1600, 600, box);
    expect(result.scaledWidth).toBeCloseTo(100);   // (300-100)*0.5
    expect(result.scaledHeight).toBeCloseTo(50);    // (150-50)*0.5
    expect(result.scaledTopX).toBeCloseTo(50);      // 100*0.5 + 0
    expect(result.scaledTopY).toBeCloseTo(175);     // 50*0.5 + 150
  });

  it("scales correctly when height is the limiting dimension", () => {
    // Container 800×600, image 800×1200 → scaleFactor = 600/1200 = 0.5
    // displayedWidth=400, displayedHeight=600, offsetX=200, offsetY=0
    const result = getScaledBounds(800, 600, 800, 1200, box);
    expect(result.scaledWidth).toBeCloseTo(100);
    expect(result.scaledHeight).toBeCloseTo(50);
    expect(result.scaledTopX).toBeCloseTo(250);    // 100*0.5 + 200
    expect(result.scaledTopY).toBeCloseTo(25);     // 50*0.5 + 0
  });

  it("returns all zeros when itemWidth is 0", () => {
    const result = getScaledBounds(800, 600, 0, 600, box);
    expect(result).toEqual({ scaledWidth: 0, scaledHeight: 0, scaledTopX: 0, scaledTopY: 0 });
  });

  it("returns all zeros when itemHeight is 0", () => {
    const result = getScaledBounds(800, 600, 800, 0, box);
    expect(result).toEqual({ scaledWidth: 0, scaledHeight: 0, scaledTopX: 0, scaledTopY: 0 });
  });

  it("returns all zeros when container dimensions are 0 (infinite scale factor)", () => {
    const result = getScaledBounds(0, 0, 800, 600, box);
    expect(result).toEqual({ scaledWidth: 0, scaledHeight: 0, scaledTopX: 0, scaledTopY: 0 });
  });
});

// ---------------------------------------------------------------------------
// getUnscaledCoordinates
// ---------------------------------------------------------------------------
describe("getUnscaledCoordinates", () => {
  it("inverts getScaledBounds — roundtrip returns original coords", () => {
    const box: BoxCoordinates = { topX: 200, topY: 100, bottomX: 400, bottomY: 300 };
    const scaled = getScaledBounds(800, 600, 1600, 1200, box);

    const unscaled = getUnscaledCoordinates(
      800, 600, 1600, 1200,
      scaled.scaledTopX, scaled.scaledTopY,
    );
    expect(unscaled.imageX).toBeCloseTo(box.topX, 5);
    expect(unscaled.imageY).toBeCloseTo(box.topY, 5);
  });

  it("returns { imageX: 0, imageY: 0 } when itemWidth is 0", () => {
    expect(getUnscaledCoordinates(800, 600, 0, 600, 100, 100)).toEqual({ imageX: 0, imageY: 0 });
  });

  it("returns { imageX: 0, imageY: 0 } when itemHeight is 0", () => {
    expect(getUnscaledCoordinates(800, 600, 800, 0, 100, 100)).toEqual({ imageX: 0, imageY: 0 });
  });

  it("correctly subtracts letterbox offset", () => {
    // Container 800×600, image 800×1200 → scaleFactor=0.5, pillarbox offsetX=200
    // A display point at (200+50, 0+25) → image coords (100, 50)
    const result = getUnscaledCoordinates(800, 600, 800, 1200, 250, 25);
    expect(result.imageX).toBeCloseTo(100);
    expect(result.imageY).toBeCloseTo(50);
  });
});

// ---------------------------------------------------------------------------
// getImageDimensions
// ---------------------------------------------------------------------------
describe("getImageDimensions", () => {
  it("resolves with the image's natural dimensions", async () => {
    mockNaturalWidth = 1280;
    mockNaturalHeight = 720;
    const file = new File([""], "test.png", { type: "image/png" });
    const dims = await getImageDimensions(file);
    expect(dims).toEqual({ width: 1280, height: 720 });
  });

  it("calls createObjectURL and revokeObjectURL", async () => {
    const file = new File([""], "test.png", { type: "image/png" });
    await getImageDimensions(file);
    expect(URL.createObjectURL).toHaveBeenCalledWith(file);
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:mock-url");
  });

  it("rejects with 'Failed to load image' when the image errors", async () => {
    mockImageShouldFail = true;
    const file = new File([""], "bad.png", { type: "image/png" });
    await expect(getImageDimensions(file)).rejects.toThrow("Failed to load image");
  });

  it("calls revokeObjectURL even when load fails", async () => {
    mockImageShouldFail = true;
    const file = new File([""], "bad.png", { type: "image/png" });
    await expect(getImageDimensions(file)).rejects.toThrow();
    expect(URL.revokeObjectURL).toHaveBeenCalledWith("blob:mock-url");
  });
});

// ---------------------------------------------------------------------------
// validateImageFile
// ---------------------------------------------------------------------------
const makePng = (bytes = 1000) =>
  new File([new Uint8Array(bytes)], "test.png", { type: "image/png" });
const makeJpeg = () =>
  new File([new Uint8Array(100)], "test.jpg", { type: "image/jpeg" });
const makeGif = () =>
  new File([new Uint8Array(100)], "test.gif", { type: "image/gif" });
const makeLarge = () =>
  new File([new Uint8Array(11 * 1024 * 1024)], "big.png", { type: "image/png" });

describe("validateImageFile", () => {
  it("accepts a valid PNG file", async () => {
    mockNaturalWidth = 1920;
    mockNaturalHeight = 1080;
    const result = await validateImageFile(makePng());
    expect(result.isValid).toBe(true);
    expect(result.errorKeys).toEqual([]);
    expect(result.dimensions).toEqual({ width: 1920, height: 1080 });
  });

  it("accepts a valid JPEG file", async () => {
    mockNaturalWidth = 640;
    mockNaturalHeight = 480;
    const result = await validateImageFile(makeJpeg());
    expect(result.isValid).toBe(true);
    expect(result.errorKeys).toEqual([]);
  });

  it("rejects a GIF with invalidType", async () => {
    const result = await validateImageFile(makeGif());
    expect(result.isValid).toBe(false);
    expect(result.errorKeys).toContain("invalidType");
  });

  it("rejects a file over 10 MB with fileTooLarge", async () => {
    const result = await validateImageFile(makeLarge());
    expect(result.isValid).toBe(false);
    expect(result.errorKeys).toContain("fileTooLarge");
  });

  it("rejects an image with width > 4608", async () => {
    mockNaturalWidth = 4609;
    mockNaturalHeight = 1080;
    const result = await validateImageFile(makePng());
    expect(result.isValid).toBe(false);
    expect(result.errorKeys).toContain("dimensionsTooLarge");
  });

  it("rejects an image with height > 2592", async () => {
    mockNaturalWidth = 1920;
    mockNaturalHeight = 2593;
    const result = await validateImageFile(makePng());
    expect(result.isValid).toBe(false);
    expect(result.errorKeys).toContain("dimensionsTooLarge");
  });

  it("accumulates multiple errors (wrong type + too large)", async () => {
    const bigGif = new File(
      [new Uint8Array(11 * 1024 * 1024)],
      "big.gif",
      { type: "image/gif" },
    );
    const result = await validateImageFile(bigGif);
    expect(result.errorKeys).toContain("invalidType");
    expect(result.errorKeys).toContain("fileTooLarge");
    expect(result.isValid).toBe(false);
  });

  it("returns unreadableDimensions when the image fails to load", async () => {
    mockImageShouldFail = true;
    const result = await validateImageFile(makePng());
    expect(result.isValid).toBe(false);
    expect(result.errorKeys).toContain("unreadableDimensions");
    expect(result.dimensions).toBeUndefined();
  });
});
