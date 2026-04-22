// @vitest-environment jsdom
import { describe, it, expect } from "vitest";
import { computeSha256 } from "../hash";

const PNG_PREFIX = "data:image/png;base64,";
const JPEG_PREFIX = "data:image/jpeg;base64,";
// base64("hello")
const HELLO_B64 = "aGVsbG8=";
// base64("world")
const WORLD_B64 = "d29ybGQ=";

describe("computeSha256", () => {
  it("returns a 64-character lowercase hex string", async () => {
    const result = await computeSha256(PNG_PREFIX + HELLO_B64);
    expect(result).toHaveLength(64);
    expect(result).toMatch(/^[0-9a-f]+$/);
  });

  it("is deterministic — same input always returns the same hash", async () => {
    const input = PNG_PREFIX + HELLO_B64;
    const r1 = await computeSha256(input);
    const r2 = await computeSha256(input);
    expect(r1).toBe(r2);
  });

  it("strips the data-URL prefix — png and jpeg with identical payload produce the same hash", async () => {
    const pngHash = await computeSha256(PNG_PREFIX + HELLO_B64);
    const jpegHash = await computeSha256(JPEG_PREFIX + HELLO_B64);
    expect(pngHash).toBe(jpegHash);
  });

  it("returns different hashes for different payloads", async () => {
    const r1 = await computeSha256(PNG_PREFIX + HELLO_B64);
    const r2 = await computeSha256(PNG_PREFIX + WORLD_B64);
    expect(r1).not.toBe(r2);
  });

  it("handles raw base64 strings without a data URL prefix", async () => {
    const fromDataUrl = await computeSha256(PNG_PREFIX + HELLO_B64);
    const fromRaw = await computeSha256(HELLO_B64);
    expect(fromDataUrl).toBe(fromRaw);
  });

  it("handles data URLs with additional parameters (like name=...)", async () => {
    const standardHash = await computeSha256(PNG_PREFIX + HELLO_B64);
    const paramHash = await computeSha256(
      "data:image/png;name=test.png;base64," + HELLO_B64,
    );
    expect(standardHash).toBe(paramHash);
  });

  it("handles data URLs without a specific MIME type", async () => {
    const standardHash = await computeSha256(PNG_PREFIX + HELLO_B64);
    const noMimeHash = await computeSha256("data:;base64," + HELLO_B64);
    expect(standardHash).toBe(noMimeHash);
  });

  it("handles an empty payload", async () => {
    // Hash of an empty string
    const result = await computeSha256("data:image/png;base64,");
    expect(result).toBe(
      "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    );
  });

  it("throws an error when provided with invalid base64 characters", async () => {
    await expect(
      computeSha256("data:image/png;base64,!!!invalid!!!"),
    ).rejects.toThrow();
  });
});
