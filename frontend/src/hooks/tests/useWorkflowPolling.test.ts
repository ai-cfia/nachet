import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { act, renderHook } from "@testing-library/react";
import { useWorkflowPolling } from "../useWorkflowPolling";
import { useWorkflowStore } from "@stores/useWorkflowStore";
import * as commonApi from "@common/index";
import { useNachetAuth } from "@auth";
import { errorLogger } from "../../logging";
import type { ApiInferenceData, WorkflowStatusResponse } from "@common/types";

// Mock dependencies
vi.mock("@common/index", () => ({
  getWorkflowStatus: vi.fn(),
  getWorkflowResults: vi.fn(),
}));

vi.mock("../../logging", () => ({
  errorLogger: {
    logError: vi.fn(),
  },
}));

vi.mock("@auth");

describe("useWorkflowPolling", () => {
  const mockWorkflowId = "workflow-123";
  const mockBackendUrl = "http://localhost:8080";
  const mockOnComplete = vi.fn();
  const mockOnError = vi.fn();

  const createMockStatusResponse = (
    overallStatus: string,
    parentWorkflowError?: string | null,
    inferenceWorkflowError?: string | null,
    processingWorkflowError?: string | null,
  ): WorkflowStatusResponse => ({
    workflowId: mockWorkflowId,
    workflowType: "inference",
    imageId: "image-123",
    overallStatus,
    authorization: {
      userId: "user-123",
      isOwner: true,
      isCfiaAdmin: false,
    },
    parentWorkflow: parentWorkflowError
      ? {
          workflowId: "parent-123",
          status: "failed",
          progressPercentage: 0,
          createdAt: null,
          completedAt: null,
          failedAt: new Date().toISOString(),
          errorMessage: parentWorkflowError,
          malwareDetected: null,
        }
      : null,
    processingWorkflow: processingWorkflowError
      ? ({
          status: "failed",
          errorMessage: processingWorkflowError,
        } as any)
      : null,
    inferenceWorkflow: inferenceWorkflowError
      ? ({
          status: "failed",
          errorMessage: inferenceWorkflowError,
        } as any)
      : null,
  });

  const mockInferenceResults: ApiInferenceData = {
    filename: "test-image.jpg",
    imageId: "image-123",
    inferenceId: "inference-123",
    boxes: [
      {
        topN: [{ score: 0.95, label: "seed-1" }],
        score: 0.95,
        label: "seed-1",
        classId: "1",
        objectTypeId: "obj-1",
        boxId: "box-1",
        box: { topX: 0.1, topY: 0.1, bottomX: 0.9, bottomY: 0.9 },
        overlapping: false,
        overlappingIndices: 0,
      },
    ],
    labelOccurrence: { "seed-1": 1 },
    totalBoxes: 1,
    models: [{ name: "model-1", version: "1.0" }],
  };

  beforeEach(() => {
    // Clear all mocks
    vi.clearAllMocks();
    vi.useFakeTimers();

    // Reset workflow store
    useWorkflowStore.setState({
      workflows: new Map(),
    });

    vi.mocked(useNachetAuth).mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
    } as ReturnType<typeof useNachetAuth>);
  });

  afterEach(() => {
    vi.clearAllTimers();
    vi.useRealTimers();
  });

  describe("Initial State", () => {
    it("should not start polling when enabled is false", () => {
      renderHook(() =>
        useWorkflowPolling({
          workflowId: mockWorkflowId,
          backendUrl: mockBackendUrl,
          enabled: false,
          onComplete: mockOnComplete,
        }),
      );

      // Fast-forward past initial delay
      act(() => vi.advanceTimersByTime(25000));

      expect(commonApi.getWorkflowStatus).not.toHaveBeenCalled();
    });

    it("should not start polling when workflowId is empty", () => {
      renderHook(() =>
        useWorkflowPolling({
          workflowId: "",
          backendUrl: mockBackendUrl,
          enabled: true,
          onComplete: mockOnComplete,
        }),
      );

      act(() => vi.advanceTimersByTime(25000));

      expect(commonApi.getWorkflowStatus).not.toHaveBeenCalled();
    });

    it("should not start polling when backendUrl is empty", () => {
      renderHook(() =>
        useWorkflowPolling({
          workflowId: mockWorkflowId,
          backendUrl: "",
          enabled: true,
          onComplete: mockOnComplete,
        }),
      );

      act(() => vi.advanceTimersByTime(25000));

      expect(commonApi.getWorkflowStatus).not.toHaveBeenCalled();
    });

    it("should not start polling when the user is not authenticated", () => {
      vi.mocked(useNachetAuth).mockReturnValue({
        isAuthenticated: false,
        isLoading: false,
      } as ReturnType<typeof useNachetAuth>);

      renderHook(() =>
        useWorkflowPolling({
          workflowId: mockWorkflowId,
          backendUrl: mockBackendUrl,
          enabled: true,
          onComplete: mockOnComplete,
        }),
      );

      act(() => vi.advanceTimersByTime(25000));

      expect(commonApi.getWorkflowStatus).not.toHaveBeenCalled();
    });
  });

  describe("Polling Behavior", () => {
    it("should wait 20 seconds before first poll", async () => {
      vi.mocked(commonApi.getWorkflowStatus).mockResolvedValue(
        createMockStatusResponse("pending"),
      );

      renderHook(() =>
        useWorkflowPolling({
          workflowId: mockWorkflowId,
          backendUrl: mockBackendUrl,
          enabled: true,
          onComplete: mockOnComplete,
        }),
      );

      // Before initial delay
      await act(() => vi.advanceTimersByTimeAsync(19000));
      expect(commonApi.getWorkflowStatus).not.toHaveBeenCalled();

      // After initial delay
      await act(() => vi.advanceTimersByTimeAsync(1000));
      expect(commonApi.getWorkflowStatus).toHaveBeenCalledTimes(1);
    });

    it("should poll every 10 seconds after initial delay", async () => {
      vi.mocked(commonApi.getWorkflowStatus).mockResolvedValue(
        createMockStatusResponse("in_progress"),
      );

      renderHook(() =>
        useWorkflowPolling({
          workflowId: mockWorkflowId,
          backendUrl: mockBackendUrl,
          enabled: true,
          onComplete: mockOnComplete,
        }),
      );

      // First poll after initial delay
      await act(() => vi.advanceTimersByTimeAsync(20000));
      expect(commonApi.getWorkflowStatus).toHaveBeenCalledTimes(1);

      // Second poll after 10 seconds
      await act(() => vi.advanceTimersByTimeAsync(10000));
      expect(commonApi.getWorkflowStatus).toHaveBeenCalledTimes(2);

      // Third poll after another 10 seconds
      await act(() => vi.advanceTimersByTimeAsync(10000));
      expect(commonApi.getWorkflowStatus).toHaveBeenCalledTimes(3);
    });

    it("should update workflow status in store during polling", async () => {
      // Add workflow to store
      useWorkflowStore
        .getState()
        .addWorkflow(
          mockWorkflowId,
          "image-123",
          0,
          "pipeline-1",
          "Test Pipeline",
        );

      vi.mocked(commonApi.getWorkflowStatus).mockResolvedValue(
        createMockStatusResponse("in_progress"),
      );

      renderHook(() =>
        useWorkflowPolling({
          workflowId: mockWorkflowId,
          backendUrl: mockBackendUrl,
          enabled: true,
          onComplete: mockOnComplete,
        }),
      );

      await act(() => vi.advanceTimersByTimeAsync(20000));
      const workflow = useWorkflowStore
        .getState()
        .workflows.get(mockWorkflowId);
      expect(workflow?.status).toBe("in_progress");
    });
  });

  describe("Completed Workflow", () => {
    it("should fetch results and call onComplete when workflow completes", async () => {
      useWorkflowStore
        .getState()
        .addWorkflow(
          mockWorkflowId,
          "image-123",
          0,
          "pipeline-1",
          "Test Pipeline",
        );

      vi.mocked(commonApi.getWorkflowStatus).mockResolvedValue(
        createMockStatusResponse("completed"),
      );

      vi.mocked(commonApi.getWorkflowResults).mockResolvedValue(
        mockInferenceResults,
      );

      renderHook(() =>
        useWorkflowPolling({
          workflowId: mockWorkflowId,
          backendUrl: mockBackendUrl,
          enabled: true,
          onComplete: mockOnComplete,
        }),
      );

      await act(() => vi.advanceTimersByTimeAsync(20000));

      expect(commonApi.getWorkflowStatus).toHaveBeenCalledWith({
        backendUrl: mockBackendUrl,
        workflowId: mockWorkflowId,
      });

      expect(commonApi.getWorkflowResults).toHaveBeenCalledWith({
        backendUrl: mockBackendUrl,
        workflowId: mockWorkflowId,
      });

      expect(mockOnComplete).toHaveBeenCalledWith(mockInferenceResults);
    });

    it("should remove workflow from store after successful completion", async () => {
      useWorkflowStore
        .getState()
        .addWorkflow(
          mockWorkflowId,
          "image-123",
          0,
          "pipeline-1",
          "Test Pipeline",
        );

      vi.mocked(commonApi.getWorkflowStatus).mockResolvedValue(
        createMockStatusResponse("completed"),
      );

      vi.mocked(commonApi.getWorkflowResults).mockResolvedValue(
        mockInferenceResults,
      );

      renderHook(() =>
        useWorkflowPolling({
          workflowId: mockWorkflowId,
          backendUrl: mockBackendUrl,
          enabled: true,
          onComplete: mockOnComplete,
        }),
      );

      await act(() => vi.advanceTimersByTimeAsync(20000));

      const workflow = useWorkflowStore
        .getState()
        .workflows.get(mockWorkflowId);
      expect(workflow).toBeUndefined();
    });

    it("should stop polling after workflow completes", async () => {
      vi.mocked(commonApi.getWorkflowStatus).mockResolvedValue(
        createMockStatusResponse("completed"),
      );

      vi.mocked(commonApi.getWorkflowResults).mockResolvedValue(
        mockInferenceResults,
      );

      renderHook(() =>
        useWorkflowPolling({
          workflowId: mockWorkflowId,
          backendUrl: mockBackendUrl,
          enabled: true,
          onComplete: mockOnComplete,
        }),
      );

      // First poll
      await act(() => vi.advanceTimersByTimeAsync(20000));
      expect(commonApi.getWorkflowStatus).toHaveBeenCalledTimes(1);

      // Should not poll again
      await act(() => vi.advanceTimersByTimeAsync(10000));
      expect(commonApi.getWorkflowStatus).toHaveBeenCalledTimes(1);
    });
  });

  describe("Failed Workflow", () => {
    it("should handle failed workflow with parent error message", async () => {
      useWorkflowStore
        .getState()
        .addWorkflow(
          mockWorkflowId,
          "image-123",
          0,
          "pipeline-1",
          "Test Pipeline",
        );

      vi.mocked(commonApi.getWorkflowStatus).mockResolvedValue(
        createMockStatusResponse("failed", "Parent workflow error"),
      );

      renderHook(() =>
        useWorkflowPolling({
          workflowId: mockWorkflowId,
          backendUrl: mockBackendUrl,
          enabled: true,
          onComplete: mockOnComplete,
          onError: mockOnError,
        }),
      );

      await act(() => vi.advanceTimersByTimeAsync(20000));

      expect(mockOnError).toHaveBeenCalledWith(
        expect.objectContaining({
          message: "Parent workflow error",
        }),
      );
    });

    it("should handle failed workflow with inference error message", async () => {
      useWorkflowStore
        .getState()
        .addWorkflow(
          mockWorkflowId,
          "image-123",
          0,
          "pipeline-1",
          "Test Pipeline",
        );

      vi.mocked(commonApi.getWorkflowStatus).mockResolvedValue(
        createMockStatusResponse("failed", null, "Inference failed"),
      );

      renderHook(() =>
        useWorkflowPolling({
          workflowId: mockWorkflowId,
          backendUrl: mockBackendUrl,
          enabled: true,
          onComplete: mockOnComplete,
          onError: mockOnError,
        }),
      );

      await act(() => vi.advanceTimersByTimeAsync(20000));

      expect(mockOnError).toHaveBeenCalledWith(
        expect.objectContaining({
          message: "Inference failed",
        }),
      );
    });

    it("should handle failed workflow with processing error message", async () => {
      useWorkflowStore
        .getState()
        .addWorkflow(
          mockWorkflowId,
          "image-123",
          0,
          "pipeline-1",
          "Test Pipeline",
        );

      vi.mocked(commonApi.getWorkflowStatus).mockResolvedValue(
        createMockStatusResponse("failed", null, null, "Processing failed"),
      );

      renderHook(() =>
        useWorkflowPolling({
          workflowId: mockWorkflowId,
          backendUrl: mockBackendUrl,
          enabled: true,
          onComplete: mockOnComplete,
          onError: mockOnError,
        }),
      );

      await act(() => vi.advanceTimersByTimeAsync(20000));

      expect(mockOnError).toHaveBeenCalledWith(
        expect.objectContaining({
          message: "Processing failed",
        }),
      );
    });

    it("should use default error message when no specific error provided", async () => {
      useWorkflowStore
        .getState()
        .addWorkflow(
          mockWorkflowId,
          "image-123",
          0,
          "pipeline-1",
          "Test Pipeline",
        );

      vi.mocked(commonApi.getWorkflowStatus).mockResolvedValue(
        createMockStatusResponse("failed"),
      );

      renderHook(() =>
        useWorkflowPolling({
          workflowId: mockWorkflowId,
          backendUrl: mockBackendUrl,
          enabled: true,
          onComplete: mockOnComplete,
          onError: mockOnError,
        }),
      );

      await act(() => vi.advanceTimersByTimeAsync(20000));

      expect(mockOnError).toHaveBeenCalledWith(
        expect.objectContaining({
          message: "Workflow processing failed",
        }),
      );
    });

    it("should update workflow status to failed in store", async () => {
      useWorkflowStore
        .getState()
        .addWorkflow(
          mockWorkflowId,
          "image-123",
          0,
          "pipeline-1",
          "Test Pipeline",
        );

      vi.mocked(commonApi.getWorkflowStatus).mockResolvedValue(
        createMockStatusResponse("failed", "Test error"),
      );

      renderHook(() =>
        useWorkflowPolling({
          workflowId: mockWorkflowId,
          backendUrl: mockBackendUrl,
          enabled: true,
          onComplete: mockOnComplete,
          onError: mockOnError,
        }),
      );

      await act(() => vi.advanceTimersByTimeAsync(20000));

      const workflow = useWorkflowStore
        .getState()
        .workflows.get(mockWorkflowId);
      expect(workflow?.status).toBe("failed");
      expect(workflow?.error).toBe("Test error");
    });

    it("should NOT remove failed workflow from store", async () => {
      useWorkflowStore
        .getState()
        .addWorkflow(
          mockWorkflowId,
          "image-123",
          0,
          "pipeline-1",
          "Test Pipeline",
        );

      vi.mocked(commonApi.getWorkflowStatus).mockResolvedValue(
        createMockStatusResponse("failed", "Test error"),
      );

      renderHook(() =>
        useWorkflowPolling({
          workflowId: mockWorkflowId,
          backendUrl: mockBackendUrl,
          enabled: true,
          onComplete: mockOnComplete,
          onError: mockOnError,
        }),
      );

      await act(() => vi.advanceTimersByTimeAsync(20000));

      const workflow = useWorkflowStore
        .getState()
        .workflows.get(mockWorkflowId);
      expect(workflow).toBeDefined();
      expect(workflow?.status).toBe("failed");
    });

    it("should stop polling after workflow fails", async () => {
      vi.mocked(commonApi.getWorkflowStatus).mockResolvedValue(
        createMockStatusResponse("failed", "Test error"),
      );

      renderHook(() =>
        useWorkflowPolling({
          workflowId: mockWorkflowId,
          backendUrl: mockBackendUrl,
          enabled: true,
          onComplete: mockOnComplete,
          onError: mockOnError,
        }),
      );

      // First poll
      await act(() => vi.advanceTimersByTimeAsync(20000));
      expect(commonApi.getWorkflowStatus).toHaveBeenCalledTimes(1);

      // Should not poll again
      await act(() => vi.advanceTimersByTimeAsync(10000));
      expect(commonApi.getWorkflowStatus).toHaveBeenCalledTimes(1);
    });

    it("should log error when workflow fails", async () => {
      vi.mocked(commonApi.getWorkflowStatus).mockResolvedValue(
        createMockStatusResponse("failed", "Test error"),
      );

      renderHook(() =>
        useWorkflowPolling({
          workflowId: mockWorkflowId,
          backendUrl: mockBackendUrl,
          enabled: true,
          onComplete: mockOnComplete,
          onError: mockOnError,
        }),
      );

      await act(() => vi.advanceTimersByTimeAsync(20000));

      expect(errorLogger.logError).toHaveBeenCalledWith(
        expect.stringContaining("Workflow workflow-123 failed"),
        expect.any(Error),
        expect.objectContaining({ workflowId: mockWorkflowId }),
      );
    });
  });

  describe("Error Handling", () => {
    it("should handle getWorkflowStatus API errors", async () => {
      useWorkflowStore
        .getState()
        .addWorkflow(
          mockWorkflowId,
          "image-123",
          0,
          "pipeline-1",
          "Test Pipeline",
        );

      const apiError = new Error("Network error");
      vi.mocked(commonApi.getWorkflowStatus).mockRejectedValue(apiError);

      renderHook(() =>
        useWorkflowPolling({
          workflowId: mockWorkflowId,
          backendUrl: mockBackendUrl,
          enabled: true,
          onComplete: mockOnComplete,
          onError: mockOnError,
        }),
      );

      await act(() => vi.advanceTimersByTimeAsync(20000));

      expect(errorLogger.logError).toHaveBeenCalledWith(
        expect.stringContaining("Failed to poll workflow status"),
        apiError,
        expect.objectContaining({ workflowId: mockWorkflowId }),
      );
    });

    it("should call onError callback when status polling fails", async () => {
      const apiError = new Error("Network error");
      vi.mocked(commonApi.getWorkflowStatus).mockRejectedValue(apiError);

      renderHook(() =>
        useWorkflowPolling({
          workflowId: mockWorkflowId,
          backendUrl: mockBackendUrl,
          enabled: true,
          onComplete: mockOnComplete,
          onError: mockOnError,
        }),
      );

      await act(() => vi.advanceTimersByTimeAsync(20000));

      expect(mockOnError).toHaveBeenCalledWith(apiError);
    });

    it("should handle getWorkflowResults API errors", async () => {
      vi.mocked(commonApi.getWorkflowStatus).mockResolvedValue(
        createMockStatusResponse("completed"),
      );

      const resultsError = new Error("Failed to fetch results");
      vi.mocked(commonApi.getWorkflowResults).mockRejectedValue(resultsError);

      renderHook(() =>
        useWorkflowPolling({
          workflowId: mockWorkflowId,
          backendUrl: mockBackendUrl,
          enabled: true,
          onComplete: mockOnComplete,
          onError: mockOnError,
        }),
      );

      await act(() => vi.advanceTimersByTimeAsync(20000));

      expect(errorLogger.logError).toHaveBeenCalledWith(
        expect.stringContaining("Failed to fetch workflow results"),
        resultsError,
        expect.objectContaining({ workflowId: mockWorkflowId }),
      );
    });

    it("should mark workflow as failed when results fetch fails", async () => {
      useWorkflowStore
        .getState()
        .addWorkflow(
          mockWorkflowId,
          "image-123",
          0,
          "pipeline-1",
          "Test Pipeline",
        );

      vi.mocked(commonApi.getWorkflowStatus).mockResolvedValue(
        createMockStatusResponse("completed"),
      );

      vi.mocked(commonApi.getWorkflowResults).mockRejectedValue(
        new Error("Failed to fetch results"),
      );

      renderHook(() =>
        useWorkflowPolling({
          workflowId: mockWorkflowId,
          backendUrl: mockBackendUrl,
          enabled: true,
          onComplete: mockOnComplete,
          onError: mockOnError,
        }),
      );

      await act(() => vi.advanceTimersByTimeAsync(20000));

      const workflow = useWorkflowStore
        .getState()
        .workflows.get(mockWorkflowId);
      expect(workflow?.status).toBe("failed");
      expect(workflow?.error).toBe("Failed to fetch results");
    });

    it("should call onError when results fetch fails", async () => {
      vi.mocked(commonApi.getWorkflowStatus).mockResolvedValue(
        createMockStatusResponse("completed"),
      );

      const resultsError = new Error("Failed to fetch results");
      vi.mocked(commonApi.getWorkflowResults).mockRejectedValue(resultsError);

      renderHook(() =>
        useWorkflowPolling({
          workflowId: mockWorkflowId,
          backendUrl: mockBackendUrl,
          enabled: true,
          onComplete: mockOnComplete,
          onError: mockOnError,
        }),
      );

      await act(() => vi.advanceTimersByTimeAsync(20000));

      expect(mockOnError).toHaveBeenCalledWith(resultsError);
    });

    it("should not crash when onError callback is not provided", async () => {
      const apiError = new Error("Network error");
      vi.mocked(commonApi.getWorkflowStatus).mockRejectedValue(apiError);

      renderHook(() =>
        useWorkflowPolling({
          workflowId: mockWorkflowId,
          backendUrl: mockBackendUrl,
          enabled: true,
          onComplete: mockOnComplete,
          // No onError provided
        }),
      );

      await act(() => vi.advanceTimersByTimeAsync(20000));

      expect(errorLogger.logError).toHaveBeenCalled();

      // Should not throw
      expect(mockOnError).not.toHaveBeenCalled();
    });
  });

  describe("Cleanup", () => {
    it("should clear interval on unmount", async () => {
      vi.mocked(commonApi.getWorkflowStatus).mockResolvedValue(
        createMockStatusResponse("pending"),
      );

      const { unmount } = renderHook(() =>
        useWorkflowPolling({
          workflowId: mockWorkflowId,
          backendUrl: mockBackendUrl,
          enabled: true,
          onComplete: mockOnComplete,
        }),
      );

      // Start polling
      await act(() => vi.advanceTimersByTimeAsync(20000));
      expect(commonApi.getWorkflowStatus).toHaveBeenCalledTimes(1);

      // Unmount
      unmount();

      // Should not poll after unmount
      await act(() => vi.advanceTimersByTimeAsync(10000));
      expect(commonApi.getWorkflowStatus).toHaveBeenCalledTimes(1);
    });

    it("should clear initial delay timeout on unmount before first poll", () => {
      renderHook(() =>
        useWorkflowPolling({
          workflowId: mockWorkflowId,
          backendUrl: mockBackendUrl,
          enabled: true,
          onComplete: mockOnComplete,
        }),
      ).unmount();

      // Should not poll even after initial delay time
      act(() => vi.advanceTimersByTime(25000));
      expect(commonApi.getWorkflowStatus).not.toHaveBeenCalled();
    });

    it("should restart polling when enabled changes from false to true", async () => {
      vi.mocked(commonApi.getWorkflowStatus).mockResolvedValue(
        createMockStatusResponse("pending"),
      );

      const { rerender } = renderHook(
        ({ enabled }) =>
          useWorkflowPolling({
            workflowId: mockWorkflowId,
            backendUrl: mockBackendUrl,
            enabled,
            onComplete: mockOnComplete,
          }),
        { initialProps: { enabled: false } },
      );

      // No polling when disabled
      act(() => vi.advanceTimersByTime(25000));
      expect(commonApi.getWorkflowStatus).not.toHaveBeenCalled();

      // Enable polling
      rerender({ enabled: true });
      await act(() => vi.advanceTimersByTimeAsync(20000));

      expect(commonApi.getWorkflowStatus).toHaveBeenCalledTimes(1);
    });
  });

  describe("Concurrent Polling Prevention", () => {
    it("should prevent concurrent polls", async () => {
      let resolveFirstPoll!: () => void;
      const firstPollPromise = new Promise<WorkflowStatusResponse>(
        (resolve) => {
          resolveFirstPoll = () =>
            resolve(createMockStatusResponse("in_progress"));
        },
      );

      vi.mocked(commonApi.getWorkflowStatus).mockReturnValueOnce(
        firstPollPromise,
      );

      renderHook(() =>
        useWorkflowPolling({
          workflowId: mockWorkflowId,
          backendUrl: mockBackendUrl,
          enabled: true,
          onComplete: mockOnComplete,
        }),
      );

      // Trigger first poll
      await act(() => vi.advanceTimersByTimeAsync(20000));

      // Try to trigger second poll while first is still pending
      await act(() => vi.advanceTimersByTimeAsync(10000));

      // Resolve first poll
      resolveFirstPoll();
      await act(() => vi.advanceTimersByTimeAsync(0));

      // Should only have been called once (concurrent call prevented)
      expect(commonApi.getWorkflowStatus).toHaveBeenCalledTimes(1);
    });
  });

  describe("Callback changes", () => {
    it.each(["completed", "failed"])(
      "keeps a pending %s response with its original workflow callbacks",
      async (status) => {
        let resolveStatus!: (response: WorkflowStatusResponse) => void;
        vi.mocked(commonApi.getWorkflowStatus).mockReturnValue(
          new Promise((resolve) => {
            resolveStatus = resolve;
          }),
        );
        vi.mocked(commonApi.getWorkflowResults).mockResolvedValue(
          mockInferenceResults,
        );
        const nextOnComplete = vi.fn();
        const nextOnError = vi.fn();
        const { rerender } = renderHook(
          ({ workflowId, onComplete, onError }) =>
            useWorkflowPolling({
              workflowId,
              backendUrl: mockBackendUrl,
              enabled: true,
              onComplete,
              onError,
            }),
          {
            initialProps: {
              workflowId: mockWorkflowId,
              onComplete: mockOnComplete,
              onError: mockOnError,
            },
          },
        );

        await act(() => vi.advanceTimersByTimeAsync(20000));
        rerender({
          workflowId: "next-workflow",
          onComplete: nextOnComplete,
          onError: nextOnError,
        });
        await act(async () => {
          resolveStatus(createMockStatusResponse(status));
          await Promise.resolve();
        });

        if (status === "completed") {
          expect(mockOnComplete).toHaveBeenCalledWith(mockInferenceResults);
        } else {
          expect(mockOnError).toHaveBeenCalledWith(expect.any(Error));
        }
        expect(nextOnComplete).not.toHaveBeenCalled();
        expect(nextOnError).not.toHaveBeenCalled();
      },
    );

    it("keeps the polling interval with inline callbacks", async () => {
      vi.mocked(commonApi.getWorkflowStatus).mockResolvedValue(
        createMockStatusResponse("pending"),
      );
      const { result } = renderHook(() =>
        useWorkflowPolling({
          workflowId: mockWorkflowId,
          backendUrl: mockBackendUrl,
          enabled: true,
          onComplete: (results) => mockOnComplete(results),
          onError: (error) => mockOnError(error),
        }),
      );

      await act(() => vi.advanceTimersByTimeAsync(20000));
      expect(result.current.isPolling).toBe(true);
      expect(commonApi.getWorkflowStatus).toHaveBeenCalledTimes(1);
      await act(() => vi.advanceTimersByTimeAsync(10000));
      expect(commonApi.getWorkflowStatus).toHaveBeenCalledTimes(2);
      expect(result.current.isPolling).toBe(true);
    });

    it("uses the latest completion callback without restarting the timer", async () => {
      vi.mocked(commonApi.getWorkflowStatus).mockResolvedValue(
        createMockStatusResponse("completed"),
      );
      vi.mocked(commonApi.getWorkflowResults).mockResolvedValue(
        mockInferenceResults,
      );
      const nextOnComplete = vi.fn();
      const { rerender } = renderHook(
        ({ onComplete }) =>
          useWorkflowPolling({
            workflowId: mockWorkflowId,
            backendUrl: mockBackendUrl,
            enabled: true,
            onComplete,
          }),
        { initialProps: { onComplete: mockOnComplete } },
      );

      await act(() => vi.advanceTimersByTimeAsync(10000));
      rerender({ onComplete: nextOnComplete });
      await act(() => vi.advanceTimersByTimeAsync(10000));
      expect(nextOnComplete).toHaveBeenCalledWith(mockInferenceResults);
      expect(mockOnComplete).not.toHaveBeenCalled();
    });

    it("uses the latest error callback when a pending request fails", async () => {
      let rejectStatus!: (error: Error) => void;
      vi.mocked(commonApi.getWorkflowStatus).mockReturnValue(
        new Promise((_resolve, reject) => {
          rejectStatus = reject;
        }),
      );
      const nextOnError = vi.fn();
      const { rerender } = renderHook(
        ({ onError }) =>
          useWorkflowPolling({
            workflowId: mockWorkflowId,
            backendUrl: mockBackendUrl,
            enabled: true,
            onComplete: mockOnComplete,
            onError,
          }),
        { initialProps: { onError: mockOnError } },
      );

      await act(() => vi.advanceTimersByTimeAsync(20000));
      rerender({ onError: nextOnError });
      const error = new Error("Status unavailable");
      await act(async () => {
        rejectStatus(error);
        await Promise.resolve();
      });
      expect(nextOnError).toHaveBeenCalledWith(error);
      expect(mockOnError).not.toHaveBeenCalled();
    });
  });

  describe("Return Value", () => {
    it("resets polling status and the initial delay when disabled and re-enabled", async () => {
      vi.mocked(commonApi.getWorkflowStatus).mockResolvedValue(
        createMockStatusResponse("pending"),
      );
      const { result, rerender } = renderHook(
        ({ enabled }) =>
          useWorkflowPolling({
            workflowId: mockWorkflowId,
            backendUrl: mockBackendUrl,
            enabled,
            onComplete: mockOnComplete,
          }),
        { initialProps: { enabled: true } },
      );

      await act(() => vi.advanceTimersByTimeAsync(20000));
      expect(result.current.isPolling).toBe(true);

      rerender({ enabled: false });
      expect(result.current.isPolling).toBe(false);
      rerender({ enabled: true });
      expect(result.current.isPolling).toBe(false);

      await act(() => vi.advanceTimersByTimeAsync(19999));
      expect(commonApi.getWorkflowStatus).toHaveBeenCalledTimes(1);
      await act(() => vi.advanceTimersByTimeAsync(1));
      expect(result.current.isPolling).toBe(true);
      expect(commonApi.getWorkflowStatus).toHaveBeenCalledTimes(2);
    });

    it("returns false after a terminal workflow status", async () => {
      vi.mocked(commonApi.getWorkflowStatus).mockResolvedValue(
        createMockStatusResponse("failed"),
      );
      const { result } = renderHook(() =>
        useWorkflowPolling({
          workflowId: mockWorkflowId,
          backendUrl: mockBackendUrl,
          enabled: true,
          onComplete: mockOnComplete,
          onError: mockOnError,
        }),
      );

      await act(() => vi.advanceTimersByTimeAsync(20000));
      expect(result.current.isPolling).toBe(false);
      expect(mockOnError).toHaveBeenCalled();
    });

    it("should return isPolling false when not enabled", () => {
      const { result } = renderHook(() =>
        useWorkflowPolling({
          workflowId: mockWorkflowId,
          backendUrl: mockBackendUrl,
          enabled: false,
          onComplete: mockOnComplete,
        }),
      );

      expect(result.current.isPolling).toBe(false);
    });

    it("should return isPolling true after polling starts", async () => {
      vi.mocked(commonApi.getWorkflowStatus).mockResolvedValue(
        createMockStatusResponse("pending"),
      );

      const { result } = renderHook(() =>
        useWorkflowPolling({
          workflowId: mockWorkflowId,
          backendUrl: mockBackendUrl,
          enabled: true,
          onComplete: mockOnComplete,
        }),
      );

      // Before polling starts
      expect(result.current.isPolling).toBe(false);

      // After initial delay - polling should start
      await act(() => vi.advanceTimersByTimeAsync(20000));
      expect(result.current.isPolling).toBe(true);

      // The API should have been called, confirming polling started
      expect(commonApi.getWorkflowStatus).toHaveBeenCalled();
    });
  });
});
