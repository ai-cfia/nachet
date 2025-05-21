import { describe, it } from "vitest";
import { getLabelOccurrence } from "../cacheutils";
import { Images } from "../types";

describe("getLabelOccurrence", () => {
  let image: Images = {
    index: 0,
    src: "test",
    scores: [0.1, 0.2, 0.3, 0.4, 0.5],
    classifications: ["a", "b", "c", "d", "e"],
    boxes: [],
    annotated: true,
    imageDims: [0, 0],
    overlapping: [],
    overlappingIndices: [],
    topN: [],
  };

  beforeEach(() => {
    image = {
      index: 0,
      src: "test",
      scores: [0.1, 0.2, 0.3, 0.4, 0.5],
      classifications: ["a", "b", "c", "d", "e"],
      boxes: [],
      annotated: true,
      imageDims: [0, 0],
      overlapping: [],
      overlappingIndices: [],
      topN: [],
    };
  });

  it.each([
    [
      "should return the correct label occurrence single",
      { sco: [0.1, 0.2, 0.3, 0.4, 0.5], cla: ["a", "b", "c", "d", "e"] },
      { a: 1, b: 1, c: 1, d: 1, e: 1 },
    ],
    [
      "should return the correct label occurrence multiple",
      {
        sco: [0.1, 0.2, 0.3, 0.4, 0.5, 0.1, 0.2, 0.3, 0.4, 0.5],
        cla: ["a", "b", "c", "d", "e", "a", "b", "c", "d", "e"],
      },
      { a: 2, b: 2, c: 2, d: 2, e: 2 },
    ],
    [
      "should return the correct label occurrence none",
      { sco: [], cla: [] },
      {},
    ],
    [
      "should return the correct label occurrence one",
      { sco: [0.1], cla: ["a"] },
      { a: 1 },
    ],
    [
      "should return the correct label occurrence two",
      { sco: [0.1, 0.1], cla: ["a", "a"] },
      { a: 2 },
    ],
    [
      "should return the correct label occurrence three",
      { sco: [0.1, 0.1, 0.1], cla: ["a", "a", "a"] },
      { a: 3 },
    ],
  ])(`%s`, (_, input, expected) => {
    image.classifications = input.cla;
    image.scores = input.sco;
    const labelOccurrence = getLabelOccurrence(image);
    expect(labelOccurrence).toEqual(expected);
  });
});
