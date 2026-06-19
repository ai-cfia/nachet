import { getWorkflowStatus } from "@common";
import { batchUploadImage } from "@common/api";
import type { BatchUploadMetadata, WorkflowStatus } from "@common/types";
import { errorLogger } from "../logging";

interface QueueItem {
  file: File;
  metadata: Omit<BatchUploadMetadata, "imageDataUrl">;
  tempId: string;
  queuePosition: number;
}

interface ActiveWorkflow {
  workflowId: string;
  file: File;
  fileName: string;
  pollingInterval: ReturnType<typeof setInterval> | null;
  initialDelay: ReturnType<typeof setTimeout> | null;
}

interface UploadStore {
  addUpload: (workflowId: string, file: File, queuePosition?: number) => void;
  updateUploadStatus: (
    workflowId: string,
    status: WorkflowStatus,
    error?: string | null,
    queuePosition?: number,
  ) => void;
  setUploadResult: (workflowId: string, resultData: unknown) => void;
  removeUpload: (workflowId: string) => void;
}

interface BatchUploadQueueManagerConfig {
  backendUrl: string;
  getAccessToken: (scopes?: string[]) => Promise<string>;
  scopes: string[];
  uploadStore: UploadStore;
  onComplete: (workflowId: string, file: File, results: unknown) => void;
  onError: (workflowId: string, file: File, error: Error) => void;
}

const POLLING_INTERVAL_MS = 10000; // 10 seconds
const INITIAL_DELAY_MS = 20000; // 20 seconds
const DELAY_AFTER_FAILURE_MS = 10000; // 10 seconds after failures
const DELAY_AFTER_COMPLETION_MS = 10000; // 10 seconds after success

/**
 * Non-reactive batch upload queue manager.
 * Processes file uploads one at a time in sequential order.
 * No React hooks, no useEffect, purely imperative.
 * Follows the same pattern as WorkflowQueueManager.
 */
export class BatchUploadQueueManager {
  private queue: QueueItem[] = [];
  private currentWorkflow: ActiveWorkflow | null = null;
  private config: BatchUploadQueueManagerConfig | null = null;
  private isProcessing = false;

  /**
   * Update configuration (called when props change)
   */
  configure(config: BatchUploadQueueManagerConfig): void {
    this.config = config;
  }

  /**
   * Add file upload to queue and start processing if idle
   */
  enqueue(
    file: File,
    metadata: Omit<BatchUploadMetadata, "imageDataUrl">,
  ): void {
    if (!this.config) {
      errorLogger.logError(
        "[BatchUploadQueueManager] No configuration set",
        new Error("Queue manager not configured"),
        { fileName: file.name },
      );
      return;
    }

    const tempId = `temp-${Date.now()}-${Math.random()}`;
    const queuePosition = this.queue.length + 1;

    this.queue.push({ file, metadata, tempId, queuePosition });

    // Add to upload store with "queued" status
    this.config.uploadStore.addUpload(tempId, file, queuePosition);
    this.config.uploadStore.updateUploadStatus(
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
   * Process next queued upload
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
      // Acquire fresh access token
      const accessToken = await this.config.getAccessToken(this.config.scopes);

      // Convert file to base64 data URL
      const imageDataUrl = await this.fileToDataUrl(item.file);

      // Submit to backend
      const response = await batchUploadImage({
        backendUrl: this.config.backendUrl,
        accessToken,
        data: {
          ...item.metadata,
          imageDataUrl,
        },
      });

      // Check if upload returned workflow ID
      if (!response.workflowId) {
        throw new Error("Upload failed - no workflow ID returned");
      }

      // Remove temp workflow from store
      this.config.uploadStore.removeUpload(item.tempId);

      // Add real workflow with "pending" status
      this.config.uploadStore.addUpload(response.workflowId, item.file);

      // Set as current active workflow
      this.currentWorkflow = {
        workflowId: response.workflowId,
        file: item.file,
        fileName: item.file.name,
        pollingInterval: null,
        initialDelay: null,
      };

      this.isProcessing = false;

      // Update queue positions for remaining items
      this.updateQueuePositions();

      // Start polling after initial delay
      this.startPolling(response.workflowId);
    } catch (error) {
      // Extract error message (api.ts already extracts detail from response)
      const errorMessage =
        error instanceof Error ? error.message : "Unknown error";

      // Log with extracted error message
      errorLogger.logError(
        `[BatchUploadQueueManager] Error submitting upload: ${errorMessage}`,
        error instanceof Error ? error : new Error(errorMessage),
        { fileName: item.file.name },
      );

      this.isProcessing = false;

      // Update upload status to failed with extracted error message
      this.config.uploadStore.updateUploadStatus(
        item.tempId,
        "failed",
        errorMessage,
      );

      this.config.onError(
        item.tempId,
        item.file,
        error instanceof Error ? error : new Error(errorMessage),
      );

      // Update queue positions
      this.updateQueuePositions();

      // Continue with next item after delay (prevent spamming on failures)
      setTimeout(() => {
        this.processNext();
      }, DELAY_AFTER_FAILURE_MS);
    }
  }

  /**
   * Convert File to base64 data URL
   */
  private fileToDataUrl(file: File): Promise<string> {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => {
        if (typeof reader.result === "string") {
          resolve(reader.result);
        } else {
          reject(new Error("Failed to convert file to data URL"));
        }
      };
      reader.onerror = () => {
        reject(new Error("File read error"));
      };
      reader.readAsDataURL(file);
    });
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
      const accessToken = await this.config.getAccessToken(this.config.scopes);

      const statusResponse = await getWorkflowStatus({
        backendUrl: this.config.backendUrl,
        workflowId,
        accessToken,
      });

      // Update upload status in store
      this.config.uploadStore.updateUploadStatus(
        workflowId,
        statusResponse.overallStatus as WorkflowStatus,
      );

      // Check for terminal states
      if (statusResponse.overallStatus === "completed") {
        await this.handleCompletion(workflowId);
      } else if (statusResponse.overallStatus === "failed") {
        await this.handleFailure(workflowId, statusResponse);
      }
      // Otherwise continue polling (pending/processing states)
    } catch (error) {
      errorLogger.logError(
        `[BatchUploadQueueManager] Failed to poll workflow status`,
        error as Error,
        {
          workflowId,
        },
      );
      // Don't fail the workflow on polling errors, will retry on next interval
    }
  }

  /**
   * Handle workflow completion
   *
   * NOTE: Batch uploads do NOT call /workflow/{id}/results because they only
   * perform image processing (upload → defender scan → sanitize) without inference.
   * No ML models are run, so there are no inference results to retrieve.
   *
   * Once status is "completed", the image is sanitized and ready in the folder.
   */
  private async handleCompletion(workflowId: string): Promise<void> {
    if (
      !this.config ||
      !this.currentWorkflow ||
      this.currentWorkflow.workflowId !== workflowId
    ) {
      return;
    }

    const { file } = this.currentWorkflow;

    // Stop polling
    this.stopPolling();

    // Batch uploads: No inference results to fetch
    // The workflow only does: Upload → Defender Scan → Sanitize
    // Once completed, the image is ready in the folder (no /results endpoint needed)

    // Clear current workflow BEFORE calling callback
    this.currentWorkflow = null;

    // Call completion callback with null results (no inference performed)
    this.config.onComplete(workflowId, file, null);

    // Process next item in queue after brief delay
    setTimeout(() => {
      this.processNext();
    }, DELAY_AFTER_COMPLETION_MS);
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

    const { file } = this.currentWorkflow;

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
    this.config.onError(workflowId, file, new Error(errorMessage));

    // Process next item after delay (prevent spamming on failures)
    setTimeout(() => {
      this.processNext();
    }, DELAY_AFTER_FAILURE_MS);
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
      activeFileName: this.currentWorkflow?.fileName || null,
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
