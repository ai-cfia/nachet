import { describe, it, expect, beforeEach } from "vitest";
import { act } from "@testing-library/react";
import { useInferenceResultsStore } from "../useInferenceResultsStore";
import { createMockApiInferenceData } from "./testUtils";
import type { ApiInferenceData } from "@common/types";

describe("useInferenceResultsStore", () => {
  beforeEach(() => {
    // Reset store to initial state
    act(() => {
      useInferenceResultsStore.setState({
        results: new Map(),
      });
    });
  });

  describe("Initial State", () => {
    it("should have empty results map", () => {
      const { results } = useInferenceResultsStore.getState();
      expect(results.size).toBe(0);
    });
  });

  describe("addResult", () => {
    const createDetailedMockData = (): ApiInferenceData =>
      createMockApiInferenceData({
        totalBoxes: 2,
        labelOccurrence: { "Weed Seed 1": 1, "Weed Seed 2": 1 },
        boxes: [
          {
            boxId: "box-1",
            objectTypeId: "1",
            classId: "1",
            label: "1 Weed Seed 1",
            score: 0.95,
            box: { topX: 10, topY: 20, bottomX: 50, bottomY: 60 },
            topN: [
              { score: 0.95, label: "Weed Seed 1" },
              { score: 0.05, label: "Other" },
            ],
            overlapping: false,
            overlappingIndices: 0,
            isVerified: false,
          },
          {
            boxId: "box-2",
            objectTypeId: "2",
            classId: "2",
            label: "2 Weed Seed 2",
            score: 0.88,
            box: { topX: 100, topY: 110, bottomX: 150, bottomY: 170 },
            topN: [
              { score: 0.88, label: "Weed Seed 2" },
              { score: 0.12, label: "Other" },
            ],
            overlapping: true,
            overlappingIndices: 1,
            isVerified: true,
          },
        ],
      }) as ApiInferenceData;

    it("should add inference result to store", () => {
      const inferenceData = createDetailedMockData();

      act(() => {
        useInferenceResultsStore
          .getState()
          .addResult(
            "workflow-123",
            "image-456",
            inferenceData,
            "pipeline-1",
            "Test Pipeline",
          );
      });

      const result = useInferenceResultsStore
        .getState()
        .getResult("workflow-123");
      expect(result).toBeDefined();
      expect(result?.workflowId).toBe("workflow-123");
      expect(result?.imageId).toBe("image-456");
      expect(result?.inferenceId).toBe("inf-123");
      expect(result?.pipelineId).toBe("pipeline-1");
      expect(result?.pipelineName).toBe("Test Pipeline");
    });

    it("should transform API box data correctly", () => {
      const inferenceData = createDetailedMockData();

      act(() => {
        useInferenceResultsStore
          .getState()
          .addResult(
            "workflow-123",
            "image-456",
            inferenceData,
            "pipeline-1",
            "Test Pipeline",
          );
      });

      const result = useInferenceResultsStore
        .getState()
        .getResult("workflow-123");
      expect(result?.boxes).toHaveLength(2);
      expect(result?.boxes[0]).toMatchObject({
        topX: 10,
        topY: 20,
        bottomX: 50,
        bottomY: 60,
        inferenceId: "inf-123",
        boxId: "box-1",
        classId: "1",
        label: "1 Weed Seed 1",
        isVerified: false,
      });
    });

    it("should strip numeric prefix from classifications", () => {
      const inferenceData = createDetailedMockData();

      act(() => {
        useInferenceResultsStore
          .getState()
          .addResult(
            "workflow-123",
            "image-456",
            inferenceData,
            "pipeline-1",
            "Test Pipeline",
          );
      });

      const result = useInferenceResultsStore
        .getState()
        .getResult("workflow-123");
      expect(result?.classifications).toEqual(["Weed Seed 1", "Weed Seed 2"]);
    });

    it("should extract scores from boxes", () => {
      const inferenceData = createDetailedMockData();

      act(() => {
        useInferenceResultsStore
          .getState()
          .addResult(
            "workflow-123",
            "image-456",
            inferenceData,
            "pipeline-1",
            "Test Pipeline",
          );
      });

      const result = useInferenceResultsStore
        .getState()
        .getResult("workflow-123");
      expect(result?.scores).toEqual([0.95, 0.88]);
    });

    it("should preserve topN data", () => {
      const inferenceData = createDetailedMockData();

      act(() => {
        useInferenceResultsStore
          .getState()
          .addResult(
            "workflow-123",
            "image-456",
            inferenceData,
            "pipeline-1",
            "Test Pipeline",
          );
      });

      const result = useInferenceResultsStore
        .getState()
        .getResult("workflow-123");
      expect(result?.topN).toHaveLength(2);
      expect(result?.topN[0]).toEqual([
        { score: 0.95, label: "Weed Seed 1" },
        { score: 0.05, label: "Other" },
      ]);
    });

    it("should set isActive to false by default", () => {
      const inferenceData = createDetailedMockData();

      act(() => {
        useInferenceResultsStore
          .getState()
          .addResult(
            "workflow-123",
            "image-456",
            inferenceData,
            "pipeline-1",
            "Test Pipeline",
          );
      });

      const result = useInferenceResultsStore
        .getState()
        .getResult("workflow-123");
      expect(result?.isActive).toBe(false);
    });

    it("should handle isVerified field when undefined", () => {
      const inferenceData = createMockApiInferenceData({
        boxes: [
          {
            boxId: "box-3",
            objectTypeId: "3",
            classId: "3",
            label: "3 Weed Seed 3",
            score: 0.9,
            box: { topX: 10, topY: 20, bottomX: 50, bottomY: 60 },
            topN: [],
            overlapping: false,
            overlappingIndices: 0,
            // isVerified is undefined
          },
        ],
      }) as ApiInferenceData;

      act(() => {
        useInferenceResultsStore
          .getState()
          .addResult(
            "workflow-123",
            "image-456",
            inferenceData,
            "pipeline-1",
            "Test Pipeline",
          );
      });

      const result = useInferenceResultsStore
        .getState()
        .getResult("workflow-123");
      expect(result?.boxes[0].isVerified).toBe(false);
    });
  });

  describe("getResult", () => {
    it("should retrieve result by workflow ID", () => {
      const inferenceData = createMockApiInferenceData();

      act(() => {
        useInferenceResultsStore
          .getState()
          .addResult(
            "workflow-123",
            "image-456",
            inferenceData,
            "pipeline-1",
            "Test Pipeline",
          );
      });

      const result = useInferenceResultsStore
        .getState()
        .getResult("workflow-123");
      expect(result?.workflowId).toBe("workflow-123");
    });

    it("should return undefined for non-existent workflow", () => {
      const result = useInferenceResultsStore
        .getState()
        .getResult("non-existent");
      expect(result).toBeUndefined();
    });
  });

  describe("getResultsForImage", () => {
    it("should retrieve all results for an image", () => {
      const inferenceData = createMockApiInferenceData();

      act(() => {
        useInferenceResultsStore
          .getState()
          .addResult(
            "workflow-1",
            "image-100",
            inferenceData,
            "pipeline-1",
            "Pipeline 1",
          );
        useInferenceResultsStore
          .getState()
          .addResult(
            "workflow-2",
            "image-100",
            inferenceData,
            "pipeline-2",
            "Pipeline 2",
          );
        useInferenceResultsStore
          .getState()
          .addResult(
            "workflow-3",
            "image-200",
            inferenceData,
            "pipeline-1",
            "Pipeline 1",
          );
      });

      const results = useInferenceResultsStore
        .getState()
        .getResultsForImage("image-100");
      expect(results).toHaveLength(2);
      expect(results.map((r) => r.workflowId)).toEqual([
        "workflow-1",
        "workflow-2",
      ]);
    });

    it("should return empty array when no results exist for image", () => {
      const results = useInferenceResultsStore
        .getState()
        .getResultsForImage("non-existent");
      expect(results).toEqual([]);
    });
  });

  describe("removeResult", () => {
    it("should remove result by workflow ID", () => {
      const inferenceData = createMockApiInferenceData();

      act(() => {
        useInferenceResultsStore
          .getState()
          .addResult(
            "workflow-123",
            "image-456",
            inferenceData,
            "pipeline-1",
            "Test Pipeline",
          );
      });

      expect(useInferenceResultsStore.getState().results.size).toBe(1);

      act(() => {
        useInferenceResultsStore.getState().removeResult("workflow-123");
      });

      expect(useInferenceResultsStore.getState().results.size).toBe(0);
    });

    it("should handle removing non-existent result", () => {
      act(() => {
        useInferenceResultsStore.getState().removeResult("non-existent");
      });

      expect(useInferenceResultsStore.getState().results.size).toBe(0);
    });
  });

  describe("clearResultsForImage", () => {
    it("should remove all results for specific image", () => {
      const inferenceData = createMockApiInferenceData();

      act(() => {
        useInferenceResultsStore
          .getState()
          .addResult(
            "workflow-1",
            "image-100",
            inferenceData,
            "pipeline-1",
            "Pipeline 1",
          );
        useInferenceResultsStore
          .getState()
          .addResult(
            "workflow-2",
            "image-100",
            inferenceData,
            "pipeline-2",
            "Pipeline 2",
          );
        useInferenceResultsStore
          .getState()
          .addResult(
            "workflow-3",
            "image-200",
            inferenceData,
            "pipeline-1",
            "Pipeline 1",
          );
      });

      act(() => {
        useInferenceResultsStore.getState().clearResultsForImage("image-100");
      });

      const results100 = useInferenceResultsStore
        .getState()
        .getResultsForImage("image-100");
      const results200 = useInferenceResultsStore
        .getState()
        .getResultsForImage("image-200");

      expect(results100).toHaveLength(0);
      expect(results200).toHaveLength(1);
    });
  });

  describe("clearAllResults", () => {
    it("should clear all results from store", () => {
      const inferenceData = createMockApiInferenceData();

      act(() => {
        useInferenceResultsStore
          .getState()
          .addResult(
            "workflow-1",
            "image-100",
            inferenceData,
            "pipeline-1",
            "Pipeline 1",
          );
        useInferenceResultsStore
          .getState()
          .addResult(
            "workflow-2",
            "image-200",
            inferenceData,
            "pipeline-2",
            "Pipeline 2",
          );
      });

      expect(useInferenceResultsStore.getState().results.size).toBe(2);

      act(() => {
        useInferenceResultsStore.getState().clearAllResults();
      });

      expect(useInferenceResultsStore.getState().results.size).toBe(0);
    });
  });

  describe("Active Result Management", () => {
    const inferenceData = createMockApiInferenceData();

    beforeEach(() => {
      act(() => {
        useInferenceResultsStore
          .getState()
          .addResult(
            "workflow-1",
            "image-100",
            inferenceData,
            "pipeline-1",
            "Pipeline 1",
          );
        useInferenceResultsStore
          .getState()
          .addResult(
            "workflow-2",
            "image-100",
            inferenceData,
            "pipeline-2",
            "Pipeline 2",
          );
        useInferenceResultsStore
          .getState()
          .addResult(
            "workflow-3",
            "image-200",
            inferenceData,
            "pipeline-1",
            "Pipeline 1",
          );
      });
    });

    it("should set active result for image", () => {
      act(() => {
        useInferenceResultsStore
          .getState()
          .setActiveResult("image-100", "workflow-2");
      });

      const result1 = useInferenceResultsStore
        .getState()
        .getResult("workflow-1");
      const result2 = useInferenceResultsStore
        .getState()
        .getResult("workflow-2");

      expect(result1?.isActive).toBe(false);
      expect(result2?.isActive).toBe(true);
    });

    it("should deactivate previous active result when setting new one", () => {
      act(() => {
        useInferenceResultsStore
          .getState()
          .setActiveResult("image-100", "workflow-1");
      });

      expect(
        useInferenceResultsStore.getState().getResult("workflow-1")?.isActive,
      ).toBe(true);

      act(() => {
        useInferenceResultsStore
          .getState()
          .setActiveResult("image-100", "workflow-2");
      });

      const result1 = useInferenceResultsStore
        .getState()
        .getResult("workflow-1");
      const result2 = useInferenceResultsStore
        .getState()
        .getResult("workflow-2");

      expect(result1?.isActive).toBe(false);
      expect(result2?.isActive).toBe(true);
    });

    it("should not affect results from other images", () => {
      act(() => {
        useInferenceResultsStore
          .getState()
          .setActiveResult("image-100", "workflow-1");
      });

      const result3 = useInferenceResultsStore
        .getState()
        .getResult("workflow-3");
      expect(result3?.isActive).toBe(false);
    });

    it("should get active result for image", () => {
      act(() => {
        useInferenceResultsStore
          .getState()
          .setActiveResult("image-100", "workflow-2");
      });

      const activeResult = useInferenceResultsStore
        .getState()
        .getActiveResult("image-100");
      expect(activeResult?.workflowId).toBe("workflow-2");
    });

    it("should return undefined when no active result for image", () => {
      const activeResult = useInferenceResultsStore
        .getState()
        .getActiveResult("image-100");
      expect(activeResult).toBeUndefined();
    });
  });

  describe("Edge Cases", () => {
    it("should handle empty boxes array", () => {
      const inferenceData = createMockApiInferenceData();

      act(() => {
        useInferenceResultsStore
          .getState()
          .addResult(
            "workflow-123",
            "image-456",
            inferenceData,
            "pipeline-1",
            "Test Pipeline",
          );
      });

      const result = useInferenceResultsStore
        .getState()
        .getResult("workflow-123");
      expect(result?.boxes).toEqual([]);
      expect(result?.scores).toEqual([]);
      expect(result?.classifications).toEqual([]);
    });

    it("should handle label without numeric prefix", () => {
      const inferenceData = createMockApiInferenceData({
        boxes: [
          {
            boxId: "box-1",
            objectTypeId: "1",
            classId: "1",
            label: "Weed Seed",
            score: 0.9,
            box: { topX: 10, topY: 20, bottomX: 50, bottomY: 60 },
            topN: [],
            overlapping: false,
            overlappingIndices: 0,
          },
        ],
      }) as ApiInferenceData;

      act(() => {
        useInferenceResultsStore
          .getState()
          .addResult(
            "workflow-123",
            "image-456",
            inferenceData,
            "pipeline-1",
            "Test Pipeline",
          );
      });

      const result = useInferenceResultsStore
        .getState()
        .getResult("workflow-123");
      expect(result?.classifications).toEqual(["Weed Seed"]);
    });

    it("should handle replacing existing result", () => {
      const inferenceData1 = createMockApiInferenceData({
        inferenceId: "inf-1",
      });
      const inferenceData2 = createMockApiInferenceData({
        inferenceId: "inf-2",
        totalBoxes: 2,
      });

      act(() => {
        useInferenceResultsStore
          .getState()
          .addResult(
            "workflow-123",
            "image-456",
            inferenceData1,
            "pipeline-1",
            "Pipeline 1",
          );
      });

      expect(
        useInferenceResultsStore.getState().getResult("workflow-123")
          ?.inferenceId,
      ).toBe("inf-1");

      act(() => {
        useInferenceResultsStore
          .getState()
          .addResult(
            "workflow-123",
            "image-456",
            inferenceData2,
            "pipeline-2",
            "Pipeline 2",
          );
      });

      const result = useInferenceResultsStore
        .getState()
        .getResult("workflow-123");
      expect(result?.inferenceId).toBe("inf-2");
      expect(result?.totalBoxes).toBe(2);
      expect(result?.pipelineId).toBe("pipeline-2");
    });
  });
});
