import {
  inferenceRequest,
  getWorkflowStatus,
  getWorkflowResults,
} from "@common";
import type { Images, ApiInferenceData } from "@common/types";
import { errorLogger } from "../logging";
import { acquireAccessToken } from "../common/auth";
import type { IPublicClientApplication } from "@azure/msal-browser";

interface QueueItem {
  imageIndex: number;
  imageId: string;
  tempId: string;
  queuePosition: number;
  pipelineId: string;
  pipelineName: string;
}

interface ActiveWorkflow {
  workflowId: string;
  imageIndex: number;
  imageId: string;
  pipelineId: string;
  pipelineName: string;
  pollingInterval: ReturnType<typeof setInterval> | null;
  initialDelay: ReturnType<typeof setTimeout> | null;
}

interface WorkflowStore {
  addWorkflow: (
    workflowId: string,
    imageId: string,
    imageIndex: number,
    pipelineId: string,
    pipelineName: string,
    queuePosition?: number,
  ) => void;
  updateWorkflowStatus: (
    workflowId: string,
    status: string,
    error?: string | null,
    queuePosition?: number,
  ) => void;
  removeWorkflow: (workflowId: string) => void;
}

interface WorkflowQueueManagerConfig {
  backendUrl: string;
  msalInstance: IPublicClientApplication;
  scopes: string[];
  pipelineId: string;
  pipelineName: string;
  curDir: { folderId: string; folderName: string };
  images: Images[];
  workflowStore: WorkflowStore;
  setImageId: (imageIndex: number, imageId: string) => void;
  onComplete: (
    workflowId: string,
    imageIndex: number,
    results: ApiInferenceData,
    pipelineId: string,
    pipelineName: string,
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
    if (!this.config) {
      errorLogger.logError(
        "[QueueManager] No configuration set",
        new Error("Queue manager not configured"),
        { imageIndex, imageId },
      );
      return;
    }

    const tempId = `temp-${Date.now()}-${Math.random()}`;
    const queuePosition = this.queue.length + 1;

    // Capture current pipeline info at enqueue time
    this.queue.push({
      imageIndex,
      imageId,
      tempId,
      queuePosition,
      pipelineId: this.config.pipelineId,
      pipelineName: this.config.pipelineName,
    });

    // Add to workflow store with "queued" status
    this.config.workflowStore.addWorkflow(
      tempId,
      imageId,
      imageIndex,
      this.config.pipelineId,
      this.config.pipelineName,
      queuePosition,
    );
    this.config.workflowStore.updateWorkflowStatus(
      tempId,
      "queued",
      null,
      queuePosition,
    );

    // Update queue positions for all items
    this.updateQueuePositions();

    // Start processing if not already active
    if (!this.currentWorkflow && !this.isProcessing) {
      this.processNext();
    }
  }

  /**
   * Update queue positions for all queued items
   */
  private updateQueuePositions(): void {
    this.queue.forEach((item, index) => {
      item.queuePosition = index + 1;
    });
  }

  /**
   * Process next queued workflow
   */
  private async processNext(): Promise<void> {
    if (
      !this.config ||
      this.isProcessing ||
      this.currentWorkflow ||
      this.queue.length === 0
    ) {
      return;
    }

    this.isProcessing = true;
    const item = this.queue.shift()!;

    try {
      // Find image data
      const image = this.config.images.find(
        (img) => img.index === item.imageIndex,
      );

      if (!image) {
        errorLogger.logError(
          `[QueueManager] Image not found for index ${item.imageIndex}`,
          new Error("Image not found"),
          { imageIndex: item.imageIndex, imageId: item.imageId },
        );
        this.isProcessing = false;
        this.config.onError(
          item.tempId,
          item.imageIndex,
          new Error("Image not found"),
        );
        this.processNext();
        return;
      }

      // Acquire fresh access token
      const accessToken = await acquireAccessToken(
        this.config.msalInstance,
        this.config.scopes,
      );

      // Submit to backend using the pipeline info from queue item
      const response = await inferenceRequest({
        backendUrl: this.config.backendUrl,
        selectedModel: item.pipelineId,
        imageObject: image as Images,
        curDir: this.config.curDir.folderName,
        accessToken,
        folder_id: this.config.curDir.folderId,
      });

      // Store the image_id in the image store
      this.config.setImageId(item.imageIndex, response.image_id);

      // Remove temp workflow from store
      this.config.workflowStore.removeWorkflow(item.tempId);

      // Add real workflow with "pending" status
      this.config.workflowStore.addWorkflow(
        response.workflow_id,
        response.image_id,
        item.imageIndex,
        item.pipelineId,
        item.pipelineName,
      );

      // Set as current active workflow
      this.currentWorkflow = {
        workflowId: response.workflow_id,
        imageIndex: item.imageIndex,
        imageId: item.imageId,
        pipelineId: item.pipelineId,
        pipelineName: item.pipelineName,
        pollingInterval: null,
        initialDelay: null,
      };

      this.isProcessing = false;

      // Update queue positions for remaining items
      this.updateQueuePositions();

      // Start polling after initial delay
      this.startPolling(response.workflow_id);
    } catch (error) {
      // Extract error message (api.ts already extracts detail from response)
      const errorMessage =
        error instanceof Error ? error.message : "Unknown error";

      errorLogger.logError(
        `[QueueManager] Error submitting workflow: ${errorMessage}`,
        error instanceof Error ? error : new Error(errorMessage),
        { imageIndex: item.imageIndex, imageId: item.imageId },
      );
      this.isProcessing = false;

      // Update workflow status to failed
      this.config.workflowStore.updateWorkflowStatus(
        item.tempId,
        "failed",
        errorMessage,
      );

      this.config.onError(
        item.tempId,
        item.imageIndex,
        error instanceof Error ? error : new Error(errorMessage),
      );

      // Update queue positions
      this.updateQueuePositions();

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
      return;
    }

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
    if (
      !this.config ||
      !this.currentWorkflow ||
      this.currentWorkflow.workflowId !== workflowId
    ) {
      return;
    }

    try {
      // Acquire fresh access token
      const accessToken = await acquireAccessToken(
        this.config.msalInstance,
        this.config.scopes,
      );

      const statusResponse = await getWorkflowStatus({
        backendUrl: this.config.backendUrl,
        workflowId,
        accessToken,
      });

      // Update workflow status in store
      this.config.workflowStore.updateWorkflowStatus(
        workflowId,
        statusResponse.overall_status,
      );

      // Check for terminal states
      if (statusResponse.overall_status === "completed") {
        await this.handleCompletion(workflowId);
      } else if (statusResponse.overall_status === "failed") {
        await this.handleFailure(workflowId, statusResponse);
      }
      // Otherwise continue polling (pending/processing states)
    } catch (error) {
      errorLogger.logError(`Failed to poll workflow status`, error as Error, {
        workflowId,
      });
      // Don't fail the workflow on polling errors, will retry on next interval
    }
  }

  /**
   * Handle workflow completion
   */
  private async handleCompletion(workflowId: string): Promise<void> {
    if (
      !this.config ||
      !this.currentWorkflow ||
      this.currentWorkflow.workflowId !== workflowId
    ) {
      return;
    }

    const { imageIndex, pipelineId, pipelineName } = this.currentWorkflow;

    // Stop polling
    this.stopPolling();

    try {
      // Acquire fresh access token
      const accessToken = await acquireAccessToken(
        this.config.msalInstance,
        this.config.scopes,
      );

      // Fetch results
      const results = await getWorkflowResults({
        backendUrl: this.config.backendUrl,
        workflowId,
        accessToken,
      });

      // Clear current workflow BEFORE calling callback
      this.currentWorkflow = null;

      // Call completion callback with pipeline info
      this.config.onComplete(
        workflowId,
        imageIndex,
        results,
        pipelineId,
        pipelineName,
      );

      // Process next item in queue
      this.processNext();
    } catch (error) {
      errorLogger.logError(`Failed to fetch workflow results`, error as Error, {
        workflowId,
        imageIndex,
      });

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
    this.stopPolling();
    this.queue = [];
    this.currentWorkflow = null;
    this.isProcessing = false;
  }
}
