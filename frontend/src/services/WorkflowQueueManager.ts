import {
  inferenceRequest,
  getWorkflowStatus,
  getWorkflowResults,
} from "@common";
import type { Images, ApiInferenceData } from "@common/types";
import { errorLogger } from "../logging";

interface QueueItem {
  imageIndex: number;
  imageId: string;
  tempId: string;
}

interface ActiveWorkflow {
  workflowId: string;
  imageIndex: number;
  imageId: string;
  pollingInterval: ReturnType<typeof setInterval> | null;
  initialDelay: ReturnType<typeof setTimeout> | null;
}

interface WorkflowQueueManagerConfig {
  backendUrl: string;
  accessToken: string;
  selectedModel: string;
  curDir: { folderId: string; folderName: string };
  images: Images[];
  onComplete: (
    workflowId: string,
    imageIndex: number,
    results: ApiInferenceData,
  ) => void;
  onError: (workflowId: string, imageIndex: number, error: Error) => void;
}

const POLLING_INTERVAL_MS = 10000; // 10 seconds
const INITIAL_DELAY_MS = 20000; // 20 seconds

/**
 * Non-reactive workflow queue manager.
 * Processes workflows one at a time in sequential order.
 * No React hooks, no useEffect, purely imperative.
 */
export class WorkflowQueueManager {
  private queue: QueueItem[] = [];
  private currentWorkflow: ActiveWorkflow | null = null;
  private config: WorkflowQueueManagerConfig | null = null;
  private isProcessing = false;

  /**
   * Update configuration (called when props change)
   */
  configure(config: WorkflowQueueManagerConfig): void {
    this.config = config;
  }

  /**
   * Add workflow to queue and start processing if idle
   */
  enqueue(imageIndex: number, imageId: string): void {
    const tempId = `temp-${Date.now()}-${Math.random()}`;

    this.queue.push({ imageIndex, imageId, tempId });

    console.log(
      `[QueueManager] Enqueued workflow for image ${imageIndex}. Queue size: ${this.queue.length}`,
    );

    // Start processing if not already active
    if (!this.currentWorkflow && !this.isProcessing) {
      this.processNext();
    }
  }

  /**
   * Process next queued workflow
   */
  private async processNext(): Promise<void> {
    if (!this.config) {
      console.warn("[QueueManager] No configuration set, cannot process queue");
      return;
    }

    if (this.isProcessing) {
      console.log("[QueueManager] Already processing, skipping");
      return;
    }

    if (this.currentWorkflow) {
      console.log(
        "[QueueManager] Workflow already active, waiting for completion",
      );
      return;
    }

    if (this.queue.length === 0) {
      console.log("[QueueManager] Queue empty, nothing to process");
      return;
    }

    this.isProcessing = true;
    const item = this.queue.shift()!;

    console.log(
      `[QueueManager] Processing workflow for image ${item.imageIndex}`,
    );

    try {
      // Find image data
      const image = this.config.images.find(
        (img) => img.index === item.imageIndex,
      );

      if (!image) {
        console.error(
          `[QueueManager] Image not found for index ${item.imageIndex}`,
        );
        this.isProcessing = false;
        this.config.onError(
          item.tempId,
          item.imageIndex,
          new Error("Image not found"),
        );
        // Continue with next item
        this.processNext();
        return;
      }

      // Submit to backend
      console.log(
        `[QueueManager] Submitting /inf request for image ${item.imageIndex}`,
      );

      const response = await inferenceRequest({
        backendUrl: this.config.backendUrl,
        selectedModel: this.config.selectedModel,
        imageObject: image as Images,
        curDir: this.config.curDir.folderName,
        accessToken: this.config.accessToken,
        folder_id: this.config.curDir.folderId,
      });

      console.log(`[QueueManager] Workflow submitted: ${response.workflow_id}`);

      // Set as current active workflow
      this.currentWorkflow = {
        workflowId: response.workflow_id,
        imageIndex: item.imageIndex,
        imageId: item.imageId,
        pollingInterval: null,
        initialDelay: null,
      };

      this.isProcessing = false;

      // Start polling after initial delay
      this.startPolling(response.workflow_id);
    } catch (error) {
      console.error("[QueueManager] Error submitting workflow:", error);
      this.isProcessing = false;
      this.config.onError(
        item.tempId,
        item.imageIndex,
        error instanceof Error ? error : new Error("Unknown error"),
      );
      // Continue with next item
      this.processNext();
    }
  }

  /**
   * Start polling for workflow status
   */
  private startPolling(workflowId: string): void {
    if (
      !this.currentWorkflow ||
      this.currentWorkflow.workflowId !== workflowId
    ) {
      console.warn(
        `[QueueManager] Cannot start polling for ${workflowId}, not current workflow`,
      );
      return;
    }

    console.log(
      `[QueueManager] Starting polling for ${workflowId} after ${INITIAL_DELAY_MS}ms delay`,
    );

    // Wait before first poll
    const initialDelay = setTimeout(() => {
      if (
        !this.currentWorkflow ||
        this.currentWorkflow.workflowId !== workflowId
      ) {
        return;
      }

      // First poll
      this.pollWorkflow(workflowId);

      // Set up interval for subsequent polls
      const interval = setInterval(() => {
        this.pollWorkflow(workflowId);
      }, POLLING_INTERVAL_MS);

      if (this.currentWorkflow) {
        this.currentWorkflow.pollingInterval = interval;
        this.currentWorkflow.initialDelay = null;
      }
    }, INITIAL_DELAY_MS);

    this.currentWorkflow.initialDelay = initialDelay;
  }

  /**
   * Poll workflow status once
   */
  private async pollWorkflow(workflowId: string): Promise<void> {
    if (!this.config) {
      return;
    }

    if (
      !this.currentWorkflow ||
      this.currentWorkflow.workflowId !== workflowId
    ) {
      console.warn(
        `[QueueManager] Polling called for ${workflowId} but it's not current workflow`,
      );
      return;
    }

    try {
      console.log(`[QueueManager] Polling status for ${workflowId}`);

      const statusResponse = await getWorkflowStatus({
        backendUrl: this.config.backendUrl,
        workflowId,
        accessToken: this.config.accessToken,
      });

      console.log(`[QueueManager] Status: ${statusResponse.overall_status}`);

      // Check for terminal states
      if (statusResponse.overall_status === "completed") {
        await this.handleCompletion(workflowId);
      } else if (statusResponse.overall_status === "failed") {
        await this.handleFailure(workflowId, statusResponse);
      }
      // Otherwise continue polling (pending/processing states)
    } catch (error) {
      errorLogger.logError(
        `Failed to poll workflow ${workflowId}`,
        error as Error,
        { workflowId },
      );
      // Don't fail the workflow on polling errors, will retry on next interval
    }
  }

  /**
   * Handle workflow completion
   */
  private async handleCompletion(workflowId: string): Promise<void> {
    if (!this.config) {
      return;
    }

    if (
      !this.currentWorkflow ||
      this.currentWorkflow.workflowId !== workflowId
    ) {
      return;
    }

    console.log(`[QueueManager] Workflow completed: ${workflowId}`);

    const { imageIndex } = this.currentWorkflow;

    // Stop polling
    this.stopPolling();

    try {
      // Fetch results
      console.log(`[QueueManager] Fetching results for ${workflowId}`);

      const results = await getWorkflowResults({
        backendUrl: this.config.backendUrl,
        workflowId,
        accessToken: this.config.accessToken,
      });

      console.log(`[QueueManager] Results fetched successfully`);

      // Clear current workflow BEFORE calling callback
      this.currentWorkflow = null;

      // Call completion callback
      this.config.onComplete(workflowId, imageIndex, results);

      // Process next item in queue
      this.processNext();
    } catch (error) {
      errorLogger.logError(
        `Failed to fetch results for ${workflowId}`,
        error as Error,
        { workflowId },
      );

      // Clear current workflow
      this.currentWorkflow = null;

      // Call error callback
      this.config.onError(
        workflowId,
        imageIndex,
        error instanceof Error ? error : new Error("Failed to fetch results"),
      );

      // Process next item
      this.processNext();
    }
  }

  /**
   * Handle workflow failure
   */
  private async handleFailure(
    workflowId: string,
    statusResponse: any,
  ): Promise<void> {
    if (!this.config) {
      return;
    }

    if (
      !this.currentWorkflow ||
      this.currentWorkflow.workflowId !== workflowId
    ) {
      return;
    }

    const { imageIndex } = this.currentWorkflow;

    const errorMessage =
      statusResponse.parent_workflow?.error_message ||
      statusResponse.inference_workflow?.error_message ||
      statusResponse.processing_workflow?.error_message ||
      "Workflow processing failed";

    console.log(
      `[QueueManager] Workflow failed: ${workflowId} - ${errorMessage}`,
    );

    // Stop polling
    this.stopPolling();

    // Clear current workflow BEFORE calling callback
    this.currentWorkflow = null;

    // Call error callback
    this.config.onError(workflowId, imageIndex, new Error(errorMessage));

    // Process next item
    this.processNext();
  }

  /**
   * Stop polling current workflow
   */
  private stopPolling(): void {
    if (!this.currentWorkflow) {
      return;
    }

    if (this.currentWorkflow.pollingInterval) {
      clearInterval(this.currentWorkflow.pollingInterval);
      this.currentWorkflow.pollingInterval = null;
    }

    if (this.currentWorkflow.initialDelay) {
      clearTimeout(this.currentWorkflow.initialDelay);
      this.currentWorkflow.initialDelay = null;
    }

    console.log(
      `[QueueManager] Stopped polling for ${this.currentWorkflow.workflowId}`,
    );
  }

  /**
   * Get current queue status
   */
  getStatus() {
    return {
      queueSize: this.queue.length,
      hasActiveWorkflow: this.currentWorkflow !== null,
      activeWorkflowId: this.currentWorkflow?.workflowId || null,
    };
  }

  /**
   * Clear queue and stop all polling (cleanup)
   */
  clear(): void {
    console.log("[QueueManager] Clearing queue");
    this.stopPolling();
    this.queue = [];
    this.currentWorkflow = null;
    this.isProcessing = false;
  }
}
