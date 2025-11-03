import { create } from "zustand";
import { InferenceResult, ApiInferenceData } from "@common/types";

interface InferenceResultsState {
  // Storage - Map for O(1) lookup
  results: Map<string, InferenceResult>;

  // Actions
  addResult: (
    workflowId: string,
    imageId: string,
    inferenceData: ApiInferenceData,
    pipelineId: string,
    pipelineName: string,
  ) => void;

  getResult: (workflowId: string) => InferenceResult | undefined;

  getResultsForImage: (imageId: string) => InferenceResult[];

  removeResult: (workflowId: string) => void;

  clearResultsForImage: (imageId: string) => void;

  clearAllResults: () => void;

  // Active result management
  setActiveResult: (imageId: string, workflowId: string) => void;

  getActiveResult: (imageId: string) => InferenceResult | undefined;
}

export const useInferenceResultsStore = create<InferenceResultsState>(
  (set, get) => ({
    results: new Map<string, InferenceResult>(),

    addResult: (
      workflowId,
      imageId,
      inferenceData,
      pipelineId,
      pipelineName,
    ) => {
      const newResult: InferenceResult = {
        workflow_id: workflowId,
        image_id: imageId,
        inference_id: inferenceData.inference_id,
        pipeline_id: pipelineId,
        pipeline_name: pipelineName,
        scores: inferenceData.boxes.map((box) => box.score),
        classifications: inferenceData.boxes.map((box) =>
          box.label.replace(/^\d+\s+/, ""),
        ),
        boxes: inferenceData.boxes.map((box) => {
          return {
            ...box.box,
            inferenceId: inferenceData.inference_id,
            boxId: box.box_id,
            classId: box.object_type_id,
            label: box.label,
            is_verified:
              box.is_verified !== undefined ? box.is_verified : false,
          };
        }),
        topN: inferenceData.boxes.map((box) => box.topN),
        overlapping: inferenceData.boxes.map((box) => box.overlapping),
        overlappingIndices: inferenceData.boxes.map(
          (box) => box.overlappingIndices,
        ),
        labelOccurrence: inferenceData.labelOccurrence,
        totalBoxes: inferenceData.totalBoxes,
        models: inferenceData.models,
        completed_at: new Date().toISOString(),
        is_active: false,
      };

      set((state) => {
        const newMap = new Map(state.results);
        newMap.set(workflowId, newResult);
        return { results: newMap };
      });
    },

    getResult: (workflowId) => {
      return get().results.get(workflowId);
    },

    getResultsForImage: (imageId) => {
      return Array.from(get().results.values()).filter(
        (result) => result.image_id === imageId,
      );
    },

    removeResult: (workflowId) => {
      set((state) => {
        const newMap = new Map(state.results);
        newMap.delete(workflowId);
        return { results: newMap };
      });
    },

    clearResultsForImage: (imageId) => {
      set((state) => {
        const newMap = new Map(state.results);
        Array.from(newMap.values()).forEach((result) => {
          if (result.image_id === imageId) {
            newMap.delete(result.workflow_id);
          }
        });
        return { results: newMap };
      });
    },

    clearAllResults: () => {
      set({ results: new Map() });
    },

    setActiveResult: (imageId, workflowId) => {
      set((state) => {
        const newMap = new Map(state.results);
        // Deactivate all results for this image
        Array.from(newMap.values()).forEach((result) => {
          if (result.image_id === imageId) {
            newMap.set(result.workflow_id, {
              ...result,
              is_active: result.workflow_id === workflowId,
            });
          }
        });
        return { results: newMap };
      });
    },

    getActiveResult: (imageId) => {
      return Array.from(get().results.values()).find(
        (result) => result.image_id === imageId && result.is_active,
      );
    },
  }),
);
