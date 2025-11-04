import { describe, it, expect, beforeEach } from "vitest";
import { act } from "@testing-library/react";
import { useModelStore } from "../useModelStore";
import type { ModelMetadata } from "@common/types";

describe("useModelStore", () => {
  const mockMetadata: ModelMetadata[] = [
    {
      modelName: "Swin transformer",
      description: "High accuracy transformer model",
      pipelineName: "nachet-pipeline",
      pipelineId: "123",
      createdBy: "CFIA",
      creationDate: "2024-01-15",
      dataset: "weed-seeds-v1",
      identifiable: ["seed1", "seed2"],
      metrics: ["accuracy: 0.95"],
      models: ["model-v1"],
      jobName: "training-job-1",
      version: "1.0.0",
      default: true,
    },
    {
      modelName: "ResNet-50",
      description: "Fast CNN model",
      pipelineName: "nachet-pipeline",
      pipelineId: "456",
      createdBy: "CFIA",
      creationDate: "2024-02-20",
      dataset: "weed-seeds-v2",
      identifiable: ["seed3", "seed4"],
      metrics: ["accuracy: 0.92"],
      models: ["model-v2"],
      jobName: "training-job-2",
    },
  ];

  beforeEach(() => {
    // Reset store to initial state
    act(() => {
      useModelStore.setState({
        selectedModel: "Swin transformer",
        metadata: [],
        isLoading: false,
      });
    });
  });

  describe("Initial State", () => {
    it("should have default selected model", () => {
      expect(useModelStore.getState().selectedModel).toBe("Swin transformer");
    });

    it("should have empty metadata array", () => {
      expect(useModelStore.getState().metadata).toEqual([]);
    });

    it("should have isLoading false", () => {
      expect(useModelStore.getState().isLoading).toBe(false);
    });
  });

  describe("setSelectedModel", () => {
    it("should set selected model", () => {
      act(() => {
        useModelStore.getState().setSelectedModel("ResNet-50");
      });

      expect(useModelStore.getState().selectedModel).toBe("ResNet-50");
    });

    it("should update selected model", () => {
      act(() => {
        useModelStore.getState().setSelectedModel("ResNet-50");
        useModelStore.getState().setSelectedModel("VGG-16");
      });

      expect(useModelStore.getState().selectedModel).toBe("VGG-16");
    });

    it("should handle empty string", () => {
      act(() => {
        useModelStore.getState().setSelectedModel("");
      });

      expect(useModelStore.getState().selectedModel).toBe("");
    });

    it("should not affect other state", () => {
      act(() => {
        useModelStore.getState().setMetadata(mockMetadata);
        useModelStore.getState().setLoading(true);
        useModelStore.getState().setSelectedModel("ResNet-50");
      });

      const state = useModelStore.getState();
      expect(state.selectedModel).toBe("ResNet-50");
      expect(state.metadata).toEqual(mockMetadata);
      expect(state.isLoading).toBe(true);
    });
  });

  describe("setMetadata", () => {
    it("should set metadata", () => {
      act(() => {
        useModelStore.getState().setMetadata(mockMetadata);
      });

      expect(useModelStore.getState().metadata).toEqual(mockMetadata);
    });

    it("should update metadata", () => {
      const updatedMetadata: ModelMetadata[] = [
        {
          modelName: "YOLO-v8",
          description: "Object detection model",
          pipelineName: "detection-pipeline",
          pipelineId: "789",
          createdBy: "CFIA",
          creationDate: "2024-03-10",
          dataset: "weed-seeds-v3",
          identifiable: ["seed5"],
          metrics: ["mAP: 0.88"],
          models: ["model-v3"],
          jobName: "training-job-3",
        },
      ];

      act(() => {
        useModelStore.getState().setMetadata(mockMetadata);
        useModelStore.getState().setMetadata(updatedMetadata);
      });

      const state = useModelStore.getState();
      expect(state.metadata).toEqual(updatedMetadata);
      expect(state.metadata).toHaveLength(1);
    });

    it("should handle empty metadata array", () => {
      act(() => {
        useModelStore.getState().setMetadata(mockMetadata);
        useModelStore.getState().setMetadata([]);
      });

      expect(useModelStore.getState().metadata).toEqual([]);
    });

    it("should not affect other state", () => {
      act(() => {
        useModelStore.getState().setSelectedModel("Custom Model");
        useModelStore.getState().setLoading(true);
        useModelStore.getState().setMetadata(mockMetadata);
      });

      const state = useModelStore.getState();
      expect(state.metadata).toEqual(mockMetadata);
      expect(state.selectedModel).toBe("Custom Model");
      expect(state.isLoading).toBe(true);
    });
  });

  describe("setLoading", () => {
    it("should set loading to true", () => {
      act(() => {
        useModelStore.getState().setLoading(true);
      });

      expect(useModelStore.getState().isLoading).toBe(true);
    });

    it("should set loading to false", () => {
      act(() => {
        useModelStore.getState().setLoading(true);
        useModelStore.getState().setLoading(false);
      });

      expect(useModelStore.getState().isLoading).toBe(false);
    });

    it("should toggle loading state", () => {
      act(() => {
        useModelStore.getState().setLoading(true);
      });
      expect(useModelStore.getState().isLoading).toBe(true);

      act(() => {
        useModelStore.getState().setLoading(false);
      });
      expect(useModelStore.getState().isLoading).toBe(false);

      act(() => {
        useModelStore.getState().setLoading(true);
      });
      expect(useModelStore.getState().isLoading).toBe(true);
    });

    it("should not affect other state", () => {
      act(() => {
        useModelStore.getState().setSelectedModel("ResNet-50");
        useModelStore.getState().setMetadata(mockMetadata);
        useModelStore.getState().setLoading(true);
      });

      const state = useModelStore.getState();
      expect(state.isLoading).toBe(true);
      expect(state.selectedModel).toBe("ResNet-50");
      expect(state.metadata).toEqual(mockMetadata);
    });
  });

  describe("State Integration", () => {
    it("should handle typical metadata loading workflow", () => {
      // Start loading
      act(() => {
        useModelStore.getState().setLoading(true);
      });

      expect(useModelStore.getState().isLoading).toBe(true);

      // Metadata loaded
      act(() => {
        useModelStore.getState().setMetadata(mockMetadata);
        useModelStore.getState().setLoading(false);
      });

      const state = useModelStore.getState();
      expect(state.isLoading).toBe(false);
      expect(state.metadata).toEqual(mockMetadata);
    });

    it("should handle model selection from metadata", () => {
      act(() => {
        useModelStore.getState().setMetadata(mockMetadata);
        useModelStore.getState().setSelectedModel(mockMetadata[1].modelName);
      });

      const state = useModelStore.getState();
      expect(state.selectedModel).toBe("ResNet-50");
      expect(state.metadata).toHaveLength(2);
    });

    it("should allow setting all state properties", () => {
      act(() => {
        useModelStore.getState().setSelectedModel("Custom Model");
        useModelStore.getState().setMetadata(mockMetadata);
        useModelStore.getState().setLoading(true);
      });

      const state = useModelStore.getState();
      expect(state.selectedModel).toBe("Custom Model");
      expect(state.metadata).toEqual(mockMetadata);
      expect(state.isLoading).toBe(true);
    });
  });

  describe("Edge Cases", () => {
    it("should handle metadata with optional fields", () => {
      const metadataWithOptionals: ModelMetadata[] = [
        {
          ...mockMetadata[0],
          version: "2.0.0",
          default: true,
        },
      ];

      act(() => {
        useModelStore.getState().setMetadata(metadataWithOptionals);
      });

      const state = useModelStore.getState();
      expect(state.metadata[0].version).toBe("2.0.0");
      expect(state.metadata[0].default).toBe(true);
    });

    it("should handle metadata without optional fields", () => {
      const metadataWithoutOptionals: ModelMetadata[] = [
        {
          modelName: "Basic Model",
          description: "Simple model",
          pipelineName: "basic-pipeline",
          pipelineId: "999",
          createdBy: "User",
          creationDate: "2024-01-01",
          dataset: "basic-dataset",
          identifiable: [],
          metrics: [],
          models: [],
          jobName: "basic-job",
        },
      ];

      act(() => {
        useModelStore.getState().setMetadata(metadataWithoutOptionals);
      });

      const state = useModelStore.getState();
      expect(state.metadata[0].version).toBeUndefined();
      expect(state.metadata[0].default).toBeUndefined();
    });

    it("should handle rapid state changes", () => {
      act(() => {
        useModelStore.getState().setLoading(true);
        useModelStore.getState().setSelectedModel("Model 1");
        useModelStore.getState().setMetadata(mockMetadata);
        useModelStore.getState().setLoading(false);
        useModelStore.getState().setSelectedModel("Model 2");
      });

      const state = useModelStore.getState();
      expect(state.selectedModel).toBe("Model 2");
      expect(state.metadata).toEqual(mockMetadata);
      expect(state.isLoading).toBe(false);
    });
  });
});
