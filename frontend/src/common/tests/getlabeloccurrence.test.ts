import { describe, it, expect } from "vitest";
import { getLabelOccurrence } from "../cacheutils";

describe("getLabelOccurrence", () => {
  const createInferenceResult = (
    scores: number[],
    classifications: string[],
  ) => ({
    workflowId: "wf-test",
    imageId: "img-test",
    inferenceId: "inf-test",
    pipelineId: "pipe-test",
    pipelineName: "Test Pipeline",
    scores,
    classifications,
    boxes: [],
    topN: [],
    overlapping: [],
    overlappingIndices: [],
    labelOccurrence: {},
    totalBoxes: scores.length,
    models: [],
    completedAt: "2024-01-01T00:00:00Z",
    isActive: true,
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
    const inferenceResult = createInferenceResult(input.sco, input.cla);
    const labelOccurrence = getLabelOccurrence(inferenceResult);
    expect(labelOccurrence).toEqual(expected);
  });
});
