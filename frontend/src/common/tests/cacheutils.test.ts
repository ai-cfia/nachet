import { describe, it } from "vitest";
import { nextCacheIndex } from "../cacheutils";
import { Images } from "../types";

describe("nextCacheIndex", () => {
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

  const insertImage = (index: number, cache: Images[]): Images[] => {
    return [
      ...cache,
      {
        index: index,
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
  };

  it("sequential calls should return the correct index", () => {
    expect(nextCacheIndex(0, imageCache)).toEqual(1);
    imageCache = insertImage(1, imageCache);
    expect(nextCacheIndex(1, imageCache)).toEqual(2);
    imageCache = insertImage(2, imageCache);
    expect(nextCacheIndex(2, imageCache)).toEqual(3);
    imageCache = insertImage(3, imageCache);
    expect(nextCacheIndex(3, imageCache)).toEqual(4);
  });

  // deleting some items then calling nextCacheIndex
  it("should return the correct index after deleting some items", () => {
    imageCache = insertImage(1, imageCache);
    imageCache = insertImage(2, imageCache);
    imageCache = insertImage(3, imageCache);
    imageCache = insertImage(4, imageCache);
    expect(nextCacheIndex(0, imageCache)).toEqual(5);
    imageCache = imageCache.slice(0, -1);
    expect(imageCache[imageCache.length - 1].index).toEqual(3);
    expect(nextCacheIndex(3, imageCache)).toEqual(4);
    imageCache = insertImage(5, imageCache);
    imageCache = imageCache.filter((item) => item.index !== 2);
    expect(nextCacheIndex(2, imageCache)).toEqual(6);
  });

  // deleting all items then calling nextCacheIndex
  it("should return the correct index after deleting all items", () => {
    imageCache = insertImage(1, imageCache);
    imageCache = insertImage(2, imageCache);
    imageCache = insertImage(3, imageCache);
    imageCache = insertImage(4, imageCache);
    expect(nextCacheIndex(0, imageCache)).toEqual(5);
    imageCache = imageCache.slice(0, -1);
    expect(nextCacheIndex(1, imageCache)).toEqual(4);
    imageCache = imageCache.slice(0, -1);
    expect(nextCacheIndex(2, imageCache)).toEqual(3);
    imageCache = imageCache.slice(0, -1);
    expect(nextCacheIndex(3, imageCache)).toEqual(2);
    imageCache = imageCache.slice(0, -1);
    expect(nextCacheIndex(4, imageCache)).toEqual(1);
    imageCache = imageCache.slice(0, -1);
    expect(nextCacheIndex(5, imageCache)).toEqual(6);
  });
});
