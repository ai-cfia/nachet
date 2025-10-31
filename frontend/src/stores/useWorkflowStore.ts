import { create } from "zustand";
import { WorkflowInfo, WorkflowStatus } from "@common/types";

/**
 * Simplified workflow store - stores workflow data only.
 * No reactive triggers, no queue management.
 * Queue logic moved to WorkflowQueueManager service.
 */
interface WorkflowState {
  workflows: Map<string, WorkflowInfo>;
  addWorkflow: (
    workflowId: string,
    imageId: string,
    imageIndex: number,
  ) => void;
  updateWorkflowStatus: (
    workflowId: string,
    status: WorkflowStatus,
    error?: string | null,
  ) => void;
  removeWorkflow: (workflowId: string) => void;
  getWorkflow: (workflowId: string) => WorkflowInfo | undefined;
  clearAllWorkflows: () => void;
  getWorkflowByImageIndex: (imageIndex: number) => WorkflowInfo | undefined;
}

export const useWorkflowStore = create<WorkflowState>()((set, get) => ({
  workflows: new Map<string, WorkflowInfo>(),

  addWorkflow: (workflowId: string, imageId: string, imageIndex: number) => {
    const now = Date.now();
    const newWorkflow: WorkflowInfo = {
      workflow_id: workflowId,
      image_id: imageId,
      imageIndex,
      status: "pending",
      started_at: now,
      last_checked_at: now,
      error: null,
    };

    set((state) => {
      const newMap = new Map(state.workflows);
      newMap.set(workflowId, newWorkflow);
      return { workflows: newMap };
    });
  },

  updateWorkflowStatus: (
    workflowId: string,
    status: WorkflowStatus,
    error: string | null = null,
  ) => {
    set((state) => {
      const workflow = state.workflows.get(workflowId);
      if (!workflow) return state;

      const updatedWorkflow: WorkflowInfo = {
        ...workflow,
        status,
        last_checked_at: Date.now(),
        error,
      };

      const newMap = new Map(state.workflows);
      newMap.set(workflowId, updatedWorkflow);
      return { workflows: newMap };
    });
  },

  removeWorkflow: (workflowId: string) => {
    set((state) => {
      const newMap = new Map(state.workflows);
      newMap.delete(workflowId);
      return { workflows: newMap };
    });
  },

  getWorkflow: (workflowId: string) => {
    return get().workflows.get(workflowId);
  },

  clearAllWorkflows: () => {
    set({ workflows: new Map<string, WorkflowInfo>() });
  },

  getWorkflowByImageIndex: (imageIndex: number) => {
    const state = get();
    return Array.from(state.workflows.values()).find(
      (w) =>
        w.imageIndex === imageIndex &&
        w.status !== "completed" &&
        w.status !== "failed",
    );
  },
}));
