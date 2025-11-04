import { describe, it, expect, beforeEach, vi } from "vitest";
import { act } from "@testing-library/react";
import { useWorkflowStore } from "../useWorkflowStore";
import type { WorkflowStatus } from "@common/types";

describe("useWorkflowStore", () => {
  beforeEach(() => {
    // Reset store to initial state
    act(() => {
      useWorkflowStore.setState({
        workflows: new Map(),
      });
    });
  });

  describe("Initial State", () => {
    it("should have empty workflows map", () => {
      const { workflows } = useWorkflowStore.getState();
      expect(workflows.size).toBe(0);
    });
  });

  describe("addWorkflow", () => {
    it("should add workflow with pending status", () => {
      act(() => {
        useWorkflowStore
          .getState()
          .addWorkflow(
            "workflow-123",
            "image-456",
            0,
            "pipeline-1",
            "Test Pipeline",
          );
      });

      const workflow = useWorkflowStore
        .getState()
        .workflows.get("workflow-123");
      expect(workflow).toBeDefined();
      expect(workflow?.workflowId).toBe("workflow-123");
      expect(workflow?.imageId).toBe("image-456");
      expect(workflow?.imageIndex).toBe(0);
      expect(workflow?.pipelineId).toBe("pipeline-1");
      expect(workflow?.pipelineName).toBe("Test Pipeline");
      expect(workflow?.status).toBe("pending");
      expect(workflow?.error).toBeNull();
    });

    it("should add workflow with queue position", () => {
      act(() => {
        useWorkflowStore
          .getState()
          .addWorkflow(
            "workflow-123",
            "image-456",
            0,
            "pipeline-1",
            "Test Pipeline",
            5,
          );
      });

      const workflow = useWorkflowStore
        .getState()
        .workflows.get("workflow-123");
      expect(workflow?.queuePosition).toBe(5);
    });

    it("should set timestamps", () => {
      const beforeTime = Date.now();

      act(() => {
        useWorkflowStore
          .getState()
          .addWorkflow(
            "workflow-123",
            "image-456",
            0,
            "pipeline-1",
            "Test Pipeline",
          );
      });

      const afterTime = Date.now();
      const workflow = useWorkflowStore
        .getState()
        .workflows.get("workflow-123");

      expect(workflow?.startedAt).toBeGreaterThanOrEqual(beforeTime);
      expect(workflow?.startedAt).toBeLessThanOrEqual(afterTime);
      expect(workflow?.lastCheckedAt).toBeGreaterThanOrEqual(beforeTime);
      expect(workflow?.lastCheckedAt).toBeLessThanOrEqual(afterTime);
    });
  });

  describe("updateWorkflowStatus", () => {
    beforeEach(() => {
      act(() => {
        useWorkflowStore
          .getState()
          .addWorkflow(
            "workflow-123",
            "image-456",
            0,
            "pipeline-1",
            "Test Pipeline",
          );
      });
    });

    it("should update workflow status", () => {
      const statuses: WorkflowStatus[] = [
        "queued",
        "pending",
        "processing",
        "completed",
      ];

      statuses.forEach((status) => {
        act(() => {
          useWorkflowStore
            .getState()
            .updateWorkflowStatus("workflow-123", status);
        });

        const workflow = useWorkflowStore
          .getState()
          .workflows.get("workflow-123");
        expect(workflow?.status).toBe(status);
      });
    });

    it("should update workflow status with error", () => {
      act(() => {
        useWorkflowStore
          .getState()
          .updateWorkflowStatus("workflow-123", "failed", "Network error");
      });

      const workflow = useWorkflowStore
        .getState()
        .workflows.get("workflow-123");
      expect(workflow?.status).toBe("failed");
      expect(workflow?.error).toBe("Network error");
    });

    it("should update queue position when provided", () => {
      act(() => {
        useWorkflowStore
          .getState()
          .updateWorkflowStatus("workflow-123", "queued", null, 3);
      });

      const workflow = useWorkflowStore
        .getState()
        .workflows.get("workflow-123");
      expect(workflow?.queuePosition).toBe(3);
    });

    it("should preserve queue position when not provided", () => {
      act(() => {
        useWorkflowStore
          .getState()
          .addWorkflow(
            "workflow-456",
            "image-789",
            1,
            "pipeline-1",
            "Test",
            10,
          );
        useWorkflowStore
          .getState()
          .updateWorkflowStatus("workflow-456", "processing");
      });

      const workflow = useWorkflowStore
        .getState()
        .workflows.get("workflow-456");
      expect(workflow?.queuePosition).toBe(10);
    });

    it("should update lastCheckedAt timestamp", () => {
      vi.useFakeTimers();
      const initialWorkflow = useWorkflowStore
        .getState()
        .workflows.get("workflow-123");
      const initialTime = initialWorkflow?.lastCheckedAt;

      vi.advanceTimersByTime(1000);

      act(() => {
        useWorkflowStore
          .getState()
          .updateWorkflowStatus("workflow-123", "processing");
      });

      const updatedWorkflow = useWorkflowStore
        .getState()
        .workflows.get("workflow-123");
      expect(updatedWorkflow?.lastCheckedAt).toBeGreaterThan(initialTime!);

      vi.useRealTimers();
    });

    it("should handle updating non-existent workflow", () => {
      act(() => {
        useWorkflowStore
          .getState()
          .updateWorkflowStatus("non-existent", "completed");
      });

      // Should not throw, state should remain unchanged
      expect(useWorkflowStore.getState().workflows.size).toBe(1);
    });
  });

  describe("removeWorkflow", () => {
    it("should remove workflow from map", () => {
      act(() => {
        useWorkflowStore
          .getState()
          .addWorkflow(
            "workflow-123",
            "image-456",
            0,
            "pipeline-1",
            "Test Pipeline",
          );
      });

      expect(useWorkflowStore.getState().workflows.has("workflow-123")).toBe(
        true,
      );

      act(() => {
        useWorkflowStore.getState().removeWorkflow("workflow-123");
      });

      expect(useWorkflowStore.getState().workflows.has("workflow-123")).toBe(
        false,
      );
    });

    it("should handle removing non-existent workflow", () => {
      act(() => {
        useWorkflowStore.getState().removeWorkflow("non-existent");
      });

      expect(useWorkflowStore.getState().workflows.size).toBe(0);
    });
  });

  describe("getWorkflow", () => {
    it("should retrieve workflow by ID", () => {
      act(() => {
        useWorkflowStore
          .getState()
          .addWorkflow(
            "workflow-123",
            "image-456",
            0,
            "pipeline-1",
            "Test Pipeline",
          );
      });

      const workflow = useWorkflowStore.getState().getWorkflow("workflow-123");
      expect(workflow).toBeDefined();
      expect(workflow?.workflowId).toBe("workflow-123");
    });

    it("should return undefined for non-existent workflow", () => {
      const workflow = useWorkflowStore.getState().getWorkflow("non-existent");
      expect(workflow).toBeUndefined();
    });
  });

  describe("clearAllWorkflows", () => {
    it("should clear all workflows", () => {
      act(() => {
        useWorkflowStore
          .getState()
          .addWorkflow("workflow-1", "image-1", 0, "pipeline-1", "Pipeline 1");
        useWorkflowStore
          .getState()
          .addWorkflow("workflow-2", "image-2", 1, "pipeline-2", "Pipeline 2");
      });

      expect(useWorkflowStore.getState().workflows.size).toBe(2);

      act(() => {
        useWorkflowStore.getState().clearAllWorkflows();
      });

      expect(useWorkflowStore.getState().workflows.size).toBe(0);
    });
  });

  describe("getWorkflowByImageIndex", () => {
    beforeEach(() => {
      act(() => {
        useWorkflowStore
          .getState()
          .addWorkflow("workflow-1", "image-1", 0, "pipeline-1", "Pipeline 1");
        useWorkflowStore
          .getState()
          .addWorkflow("workflow-2", "image-2", 1, "pipeline-1", "Pipeline 1");
        useWorkflowStore
          .getState()
          .addWorkflow("workflow-3", "image-3", 2, "pipeline-1", "Pipeline 1");
      });
    });

    it("should find workflow by image index", () => {
      const workflow = useWorkflowStore.getState().getWorkflowByImageIndex(1);
      expect(workflow).toBeDefined();
      expect(workflow?.workflowId).toBe("workflow-2");
      expect(workflow?.imageIndex).toBe(1);
    });

    it("should return only active workflows (not completed or failed)", () => {
      act(() => {
        useWorkflowStore
          .getState()
          .updateWorkflowStatus("workflow-1", "completed");
      });

      const workflow = useWorkflowStore.getState().getWorkflowByImageIndex(0);
      expect(workflow).toBeUndefined();
    });

    it("should exclude failed workflows", () => {
      act(() => {
        useWorkflowStore
          .getState()
          .updateWorkflowStatus("workflow-2", "failed", "Error");
      });

      const workflow = useWorkflowStore.getState().getWorkflowByImageIndex(1);
      expect(workflow).toBeUndefined();
    });

    it("should find processing workflows", () => {
      act(() => {
        useWorkflowStore
          .getState()
          .updateWorkflowStatus("workflow-3", "processing");
      });

      const workflow = useWorkflowStore.getState().getWorkflowByImageIndex(2);
      expect(workflow).toBeDefined();
      expect(workflow?.status).toBe("processing");
    });

    it("should return undefined for non-existent image index", () => {
      const workflow = useWorkflowStore.getState().getWorkflowByImageIndex(999);
      expect(workflow).toBeUndefined();
    });
  });

  describe("Edge Cases", () => {
    it("should handle multiple workflows for same image", () => {
      act(() => {
        useWorkflowStore
          .getState()
          .addWorkflow("workflow-1", "image-1", 0, "pipeline-1", "Pipeline 1");
        useWorkflowStore
          .getState()
          .addWorkflow("workflow-2", "image-1", 0, "pipeline-2", "Pipeline 2");
      });

      expect(useWorkflowStore.getState().workflows.size).toBe(2);

      // getWorkflowByImageIndex returns the first match
      const workflow = useWorkflowStore.getState().getWorkflowByImageIndex(0);
      expect(workflow).toBeDefined();
      expect(["workflow-1", "workflow-2"]).toContain(workflow?.workflowId);
    });

    it("should handle status update with null error", () => {
      act(() => {
        useWorkflowStore
          .getState()
          .addWorkflow("workflow-123", "image-456", 0, "pipeline-1", "Test");
        useWorkflowStore
          .getState()
          .updateWorkflowStatus("workflow-123", "processing", null);
      });

      const workflow = useWorkflowStore
        .getState()
        .workflows.get("workflow-123");
      expect(workflow?.error).toBeNull();
    });

    it("should handle clearing empty workflow map", () => {
      act(() => {
        useWorkflowStore.getState().clearAllWorkflows();
      });

      expect(useWorkflowStore.getState().workflows.size).toBe(0);
    });
  });
});
