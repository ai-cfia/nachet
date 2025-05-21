import { describe, it, vi } from "vitest";
import { getImageDims, loadCaptureToCache } from "../cacheutils";
import { Images } from "../types";

// TODO: Not sure decodeTiff is can be tested here due to browser dependencies
// describe("decodeTiff", () => {
//   // const imageTiff =
//   //   "data:image/tiff;base64,SUkqAAoAAADAABEAAAEDAAEAAAABAAAAAQEDAAEAAAABAAAAAgEDAAIAAAABAAEAAwEDAAEAAAABAAAABgEDAAEAAAAAAAAAEQEEAAEAAAAIAAAAEgEDAAEAAAABAAAAFQEDAAEAAAACAAAAFgEDAAEAAACAAAAAFwEEAAEAAAABAAAAGgEFAAEAAADcAAAAGwEFAAEAAADkAAAAHAEDAAEAAAABAAAAHQECAAgAAADsAAAAKAEDAAEAAAACAAAAUgEDAAEAAAACAAAAUwEDAAIAAAABAAEAAAAAAEgAAAABAAAASAAAAAEAAAAxeDEucG5nAA==";

//   it("should decode a tiff image", async () => {
//     // const bytes = await fetchArrayBuffer(imageTiff);
//     // expect(bytes).toEqual(new ArrayBuffer(0));
//     // const bytes = new ArrayBuffer(0);
//     // const decodedTiff = await utifToRGBA(bytes);
//     // expect(decodedTiff.width).toBe(0);
//     // expect(decodedTiff.height).toBe(0);
//     // expect(decodedTiff.rgba.length).toBe(0);
//     expect(1).toBe(1);
//   });
// });

describe("getImageDims", () => {
  // const imageTiff =
  //   "data:image/tiff;base64,SUkqAAoAAADAABEAAAEDAAEAAAABAAAAAQEDAAEAAAABAAAAAgEDAAIAAAABAAEAAwEDAAEAAAABAAAABgEDAAEAAAAAAAAAEQEEAAEAAAAIAAAAEgEDAAEAAAABAAAAFQEDAAEAAAACAAAAFgEDAAEAAACAAAAAFwEEAAEAAAABAAAAGgEFAAEAAADcAAAAGwEFAAEAAADkAAAAHAEDAAEAAAABAAAAHQECAAgAAADsAAAAKAEDAAEAAAACAAAAUgEDAAEAAAACAAAAUwEDAAIAAAABAAEAAAAAAEgAAAABAAAASAAAAAEAAAAxeDEucG5nAA==";
  const imagePNG =
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABAQMAAAAl21bKAAAAA1BMVEUAAACnej3aAAAAAXRSTlMAQObYZgAAAApJREFUCNdjYAAAAAIAAeIhvDMAAAAASUVORK5CYII=";

  global.Image = class MyImage extends Image {
    onload: () => number[];
    width: number;
    height: number;

    constructor() {
      super();
      this.width = 1;
      this.height = 1;
      this.onload = vi.fn();
      setTimeout(() => {
        this.onload();
      }, 50);
    }
  };

  it("should get the dimensions of a png image", async () => {
    const dims = await getImageDims(imagePNG);
    expect(dims).toEqual([1, 1]);
  }, 10000);

  // TODO: Not sure decodeTiff is can be tested here due to browser dependencies
  // it("should get the dimensions of a tiff image", async () => {
  //   const dims = await getImageDims(imageTiff);
  //   expect(dims).toEqual([0, 0]);
  // }, 10000);
});

describe("loadCaptureToCache", () => {
  let imageCache: Images[] = [
    {
      index: 0,
      src: "test",
      scores: [],
      classifications: [],
      boxes: [],
      annotated: false,
      imageDims: [0, 0],
      overlapping: [],
      overlappingIndices: [],
      topN: [],
    },
  ];

  const imagePNG =
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAA8sAAAJICAYAAABWonZtAAAAAXNSR0IArs4c6QAAIABJREFUeF5UvUusbmt2njXm/K9r7X1OVaVSjh1bBIxkAY04mAYNYwlBYsUNKhFRBCYuYxtjjJTIBAmkKAFEA5pISOAICLgDEsiABKIRiQ4RlwYiJoiLQiJELCLi8qUu5+y9/vuc6Hne8a11OJWK6+y91v/P+V3G5R3veMf0P/6VD+u0mWpa11rua61LVU1zLVP532mu2sxV82OtzTY/t12rHutUyzzVffVfaq657o9HbfebWueqZV3rdltru51qs1Stt7X2h6r7danjfltVj5q2U76nplrWqnVZaponn2Hl/97X2u6mKr6j5lqXR83T9PpM/vk61/1edVurrve1HlPVlqeZq6bHWsuDF6ra7GY/+7Euvsc6Vd1vVcvyqOenTa3rWjsea827PK5Vp5dH3R9zPaapav...";

  beforeEach(() => {
    imageCache = [
      {
        index: 0,
        src: "test",
        scores: [],
        classifications: [],
        boxes: [],
        annotated: false,
        imageDims: [0, 0],
        overlapping: [],
        overlappingIndices: [],
        topN: [],
      },
    ];
  });

  it("should load a capture to the cache", async () => {
    const newCache = await loadCaptureToCache(imagePNG, imageCache, 1);
    expect(newCache).toEqual([
      {
        index: 0,
        src: "test",
        scores: [],
        classifications: [],
        boxes: [],
        annotated: false,
        imageDims: [0, 0],
        overlapping: [],
        overlappingIndices: [],
        topN: [],
      },
      {
        index: 1,
        src: imagePNG,
        scores: [],
        classifications: [],
        boxes: [],
        annotated: false,
        imageDims: [1, 1],
        overlapping: [],
        overlappingIndices: [],
        topN: [],
      },
    ]);
  }, 10000);

  it("should load a capture to the cache with the correct index", async () => {
    const newCache = await loadCaptureToCache(imagePNG, imageCache, 0);
    expect(newCache).toEqual([
      {
        index: 0,
        src: "test",
        scores: [],
        classifications: [],
        boxes: [],
        annotated: false,
        imageDims: [0, 0],
        overlapping: [],
        overlappingIndices: [],
        topN: [],
      },
      {
        index: 0,
        src: imagePNG,
        scores: [],
        classifications: [],
        boxes: [],
        annotated: false,
        imageDims: [1, 1],
        overlapping: [],
        overlappingIndices: [],
        topN: [],
      },
    ]);
  }, 10000);

  it("should load a capture to an empty cache", async () => {
    const newCache = await loadCaptureToCache(imagePNG, [], 0);
    expect(newCache).toEqual([
      {
        index: 0,
        src: imagePNG,
        scores: [],
        classifications: [],
        boxes: [],
        annotated: false,
        imageDims: [1, 1],
        overlapping: [],
        overlappingIndices: [],
        topN: [],
      },
    ]);
  }, 10000);

  // should load empty string
  it("should not load a capture to an empty cache with an empty string", async () => {
    await expect(loadCaptureToCache("", [], 0)).rejects.toThrow(
      "Image source is null or empty",
    );
  });
});
