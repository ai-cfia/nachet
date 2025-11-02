import { useEffect, useRef, useCallback } from "react";
import { getWorkflowStatus, getWorkflowResults } from "@common/index";
import { useWorkflowStore } from "@stores/useWorkflowStore";
import { ApiInferenceData, WorkflowStatus } from "@common/types";
import { errorLogger } from "../logging";

const POLLING_INTERVAL_MS = 10000; // 10 seconds
const INITIAL_DELAY_MS = 20000; // 20 seconds - wait before first poll

// Terminal states that should stop polling
const TERMINAL_STATES = ["completed", "failed"] as const;
type TerminalState = (typeof TERMINAL_STATES)[number];

const isTerminalState = (status: string): status is TerminalState => {
  return TERMINAL_STATES.includes(status as TerminalState);
};

interface UseWorkflowPollingParams {
  workflowId: string;
  backendUrl: string;
  accessToken: string;
  enabled: boolean;
  onComplete: (results: ApiInferenceData) => void;
  onError?: (error: Error) => void;
}

/**
 * Custom hook for polling workflow status and fetching results when complete
 * @param workflowId - The workflow ID to poll
 * @param backendUrl - Backend API URL
 * @param accessToken - Authentication token
 * @param enabled - Whether polling is enabled
 * @param onComplete - Callback when workflow completes successfully
 * @param onError - Optional callback when workflow fails
 */
export const useWorkflowPolling = ({
  workflowId,
  backendUrl,
  accessToken,
  enabled,
  onComplete,
  onError,
}: UseWorkflowPollingParams) => {
  const updateWorkflowStatus = useWorkflowStore(
    (state) => state.updateWorkflowStatus,
  );
  const removeWorkflow = useWorkflowStore((state) => state.removeWorkflow);

  const pollingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(
    null,
  );
  const isPollingRef = useRef(false);

  /**
   * Stop polling and clean up the interval
   */
  const stopPolling = useCallback(() => {
    if (pollingIntervalRef.current) {
      clearInterval(pollingIntervalRef.current);
      pollingIntervalRef.current = null;
      console.log(`[Workflow] Stopped polling for workflow_id=${workflowId}`);
    }
  }, [workflowId]);

  const pollWorkflowStatus = useCallback(async () => {
    // Prevent concurrent polling
    if (isPollingRef.current) return;
    isPollingRef.current = true;

    try {
      console.log(`[Workflow] Polling status for workflow_id=${workflowId}`);

      // Poll the workflow status endpoint
      const statusResponse = await getWorkflowStatus({
        backendUrl,
        workflowId,
        accessToken,
      });

      console.log(
        `[Workflow] Status received: overall_status=${statusResponse.overall_status}`,
        statusResponse,
      );

      // Update the store with the current status
      updateWorkflowStatus(
        workflowId,
        statusResponse.overall_status as WorkflowStatus,
      );

      // Check if workflow has reached a terminal state (completed or failed)
      if (!isTerminalState(statusResponse.overall_status)) {
        // Status is still "pending" or "in_progress", continue polling
        console.log(
          `[Workflow] Status is ${statusResponse.overall_status}, continuing to poll`,
        );
        return;
      }

      // Terminal state reached - stop polling
      console.log(
        `[Workflow] Terminal state reached: ${statusResponse.overall_status}`,
      );
      stopPolling();

      // Handle completed workflow
      if (statusResponse.overall_status === "completed") {
        console.log(
          `[Workflow] Workflow completed, fetching results for workflow_id=${workflowId}`,
        );

        try {
          // Fetch the results from the results endpoint
          const results = await getWorkflowResults({
            backendUrl,
            workflowId,
            accessToken,
          });

          console.log(
            `[Workflow] Successfully fetched results for workflow_id=${workflowId}`,
            results,
          );

          // Call the completion callback with results
          onComplete(results);

          // Clean up the workflow from the store
          removeWorkflow(workflowId);
        } catch (error) {
          errorLogger.logError(
            `Failed to fetch workflow results for ${workflowId}`,
            error as Error,
            { workflowId },
          );
          updateWorkflowStatus(workflowId, "failed", "Failed to fetch results");
          if (onError) {
            onError(error as Error);
          }
        }
      }
      // Handle failed workflow
      else if (statusResponse.overall_status === "failed") {
        const errorMessage =
          statusResponse.parent_workflow?.error_message ||
          statusResponse.inference_workflow?.error_message ||
          statusResponse.processing_workflow?.error_message ||
          "Workflow processing failed";

        console.log(
          `[Workflow] Workflow failed for workflow_id=${workflowId}: ${errorMessage}`,
        );

        updateWorkflowStatus(workflowId, "failed", errorMessage);

        errorLogger.logError(
          `Workflow ${workflowId} failed: ${errorMessage}`,
          new Error(errorMessage),
          { workflowId, statusResponse },
        );

        if (onError) {
          onError(new Error(errorMessage));
        }

        // Note: We don't remove failed workflows from the store so users can see the error
      }
    } catch (error) {
      errorLogger.logError(
        `Failed to poll workflow status for ${workflowId}`,
        error as Error,
        { workflowId },
      );
      updateWorkflowStatus(
        workflowId,
        "failed",
        "Failed to check workflow status",
      );
      if (onError) {
        onError(error as Error);
      }
    } finally {
      isPollingRef.current = false;
    }
  }, [
    workflowId,
    backendUrl,
    accessToken,
    updateWorkflowStatus,
    removeWorkflow,
    onComplete,
    onError,
    stopPolling,
  ]);

  useEffect(() => {
    if (!enabled || !workflowId || !backendUrl || !accessToken) {
      return;
    }

    // Wait minimum 20 seconds before first poll to give backend time to start processing
    const initialDelayTimeout = setTimeout(() => {
      // First poll after initial delay
      pollWorkflowStatus();

      // Set up interval for subsequent polls
      pollingIntervalRef.current = setInterval(() => {
        pollWorkflowStatus();
      }, POLLING_INTERVAL_MS);
    }, INITIAL_DELAY_MS);

    // Cleanup on unmount or when dependencies change
    return () => {
      clearTimeout(initialDelayTimeout);
      if (pollingIntervalRef.current) {
        clearInterval(pollingIntervalRef.current);
        pollingIntervalRef.current = null;
      }
    };
  }, [enabled, workflowId, backendUrl, accessToken, pollWorkflowStatus]);

  return {
    isPolling: enabled && pollingIntervalRef.current !== null,
  };
};
