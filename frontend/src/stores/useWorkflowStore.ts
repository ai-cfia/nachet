import { create } from "zustand";
import { persist } from "zustand/middleware";
import { WorkflowInfo } from "@common/types";

interface WorkflowState {
  workflows: Map<string, WorkflowInfo>;
  addWorkflow: (workflowId: string, imageId: string) => void;
  updateWorkflowStatus: (
    workflowId: string,
    status: string,
    error?: string | null,
  ) => void;
  removeWorkflow: (workflowId: string) => void;
  getWorkflow: (workflowId: string) => WorkflowInfo | undefined;
  clearAllWorkflows: () => void;
}

export const useWorkflowStore = create<WorkflowState>()(
  persist(
    (set, get) => ({
      workflows: new Map<string, WorkflowInfo>(),

      addWorkflow: (workflowId: string, imageId: string) => {
        const now = Date.now();
        const newWorkflow: WorkflowInfo = {
          workflow_id: workflowId,
          image_id: imageId,
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
        status: string,
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
    }),
    {
      name: "workflow-storage",
      // Custom serialization for Map
      storage: {
        getItem: (name) => {
          const str = localStorage.getItem(name);
          if (!str) return null;
          const { state } = JSON.parse(str);
          return {
            state: {
              ...state,
              workflows: new Map(Object.entries(state.workflows || {})),
            },
          };
        },
        setItem: (name, value) => {
          const workflows = Object.fromEntries(value.state.workflows);
          localStorage.setItem(
            name,
            JSON.stringify({
              state: {
                ...value.state,
                workflows,
              },
            }),
          );
        },
        removeItem: (name) => localStorage.removeItem(name),
      },
    },
  ),
);
