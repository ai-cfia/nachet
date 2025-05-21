import { describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import useDecoderTiff from "../useDecoderTiff";
import * as common from "../../common";

describe("useDecoderTiff", () => {
  vi.spyOn(common, "decodeTiff").mockImplementation(async () => {
    return {
      rgba: new Uint8Array(1),
      width: 1,
      height: 1,
    };
  });

  it("should return an object with a function to decode a tiff file", async () => {
    const { result } = renderHook(() => useDecoderTiff("test"));
    await waitFor(() => {
      expect(result.current).toHaveProperty("rgba");
      expect(result.current).toHaveProperty("width");
      expect(result.current).toHaveProperty("height");
    });
  });

  it("should call decodeTiff with the imageSrc", async () => {
    const { result } = renderHook(() => useDecoderTiff("test"));
    expect(common.decodeTiff).toHaveBeenCalledWith("test");
    await waitFor(() =>
      expect(result.current).toEqual({
        rgba: new Uint8Array(1),
        width: 1,
        height: 1,
      }),
    );
  });
});
