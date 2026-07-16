import { describe, it, expect } from "vitest";
import { jetColor } from "../heatmapColors";

describe("jetColor", () => {
  it("maps the cold end (0) to blue", () => {
    expect(jetColor(0)).toEqual([0, 0, 128]);
  });

  it("maps the hot end (1) to red", () => {
    expect(jetColor(1)).toEqual([128, 0, 0]);
  });

  it("maps the midpoint (0.5) to green", () => {
    expect(jetColor(0.5)).toEqual([128, 255, 128]);
  });

  it("maps the lower quarter (0.25) to cyan", () => {
    expect(jetColor(0.25)).toEqual([0, 128, 255]);
  });

  it("maps the upper quarter (0.75) to orange", () => {
    expect(jetColor(0.75)).toEqual([255, 128, 0]);
  });

  it("clamps values below 0 to the cold end", () => {
    expect(jetColor(-1)).toEqual(jetColor(0));
    expect(jetColor(-0.0001)).toEqual([0, 0, 128]);
  });

  it("clamps values above 1 to the hot end", () => {
    expect(jetColor(2)).toEqual(jetColor(1));
    expect(jetColor(1.0001)).toEqual([128, 0, 0]);
  });

  it("returns integer channel values in [0, 255]", () => {
    for (let i = 0; i <= 20; i++) {
      const [r, g, b] = jetColor(i / 20);
      for (const c of [r, g, b]) {
        expect(Number.isInteger(c)).toBe(true);
        expect(c).toBeGreaterThanOrEqual(0);
        expect(c).toBeLessThanOrEqual(255);
      }
    }
  });
});
