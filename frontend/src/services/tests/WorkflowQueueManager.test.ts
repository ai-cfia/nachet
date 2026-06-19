import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { WorkflowQueueManager } from "../WorkflowQueueManager";
import * as api from "@common/api";
import { errorLogger } from "../../logging";

// Mock dependencies
vi.mock("@common/api");
vi.mock("../../logging");

describe("WorkflowQueueManager", () => {
  let queueManager: WorkflowQueueManager;
  let mockWorkflowStore: any;
  let mockOnComplete: any;
  let mockOnError: any;
  let mockGetAccessToken: any;
  let mockConfig: any;

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();

    queueManager = new WorkflowQueueManager();

    mockWorkflowStore = {
      addWorkflow: vi.fn(),
      updateWorkflowStatus: vi.fn(),
      removeWorkflow: vi.fn(),
    };

    mockOnComplete = vi.fn();
    mockOnError = vi.fn();
    mockGetAccessToken = vi.fn().mockResolvedValue("test-token");

    mockConfig = {
      backendUrl: "http://test-backend.com",
      getAccessToken: mockGetAccessToken,
      scopes: ["test-scope"],
      pipelineId: "pipeline-1",
      pipelineName: "Test Pipeline",
      curDir: { folderId: "folder-1", folderName: "Test Folder" },
      images: [],
      workflowStore: mockWorkflowStore,
      setImageId: vi.fn(),
      onComplete: mockOnComplete,
      onError: mockOnError,
    };
  });

  afterEach(() => {
    vi.useRealTimers();
    queueManager.clear();
  });

  describe("configure", () => {
    it("should store configuration", () => {
      queueManager.configure(mockConfig);
      const status = queueManager.getStatus();
      expect(status).toBeDefined();
    });
  });

  describe("enqueue", () => {
    it("should add item to queue", () => {
      queueManager.configure(mockConfig);
      queueManager.enqueue(0, "image-1");

      const status = queueManager.getStatus();
      expect(status.queueSize).toBe(0); // Immediately starts processing
      expect(mockWorkflowStore.addWorkflow).toHaveBeenCalled();
    });

    it("should call addWorkflow with queue position", () => {
      queueManager.configure(mockConfig);

      // Mock inference to delay processing
      (api.inferenceRequest as any).mockImplementation(
        () => new Promise(() => {}),
      );

      queueManager.enqueue(0, "image-1");

      expect(mockWorkflowStore.addWorkflow).toHaveBeenCalledWith(
        expect.stringContaining("temp-"),
        "image-1",
        0,
        "pipeline-1",
        "Test Pipeline",
        1, // queue position
      );
    });

    it("should log error if not configured", () => {
      queueManager.enqueue(0, "image-1");
      expect(errorLogger.logError).toHaveBeenCalled();
    });

    it("should update queue positions when adding multiple items", () => {
      queueManager.configure(mockConfig);

      // Mock inference to delay processing
      (api.inferenceRequest as any).mockImplementation(
        () => new Promise(() => {}),
      );

      queueManager.enqueue(0, "image-1");
      queueManager.enqueue(1, "image-2");
      queueManager.enqueue(2, "image-3");

      // First item starts processing, next two are queued
      expect(mockWorkflowStore.addWorkflow).toHaveBeenCalledTimes(3);
    });
  });

  describe("processNext", () => {
    it("should process workflow submission successfully", async () => {
      const mockImage = {
        index: 0,
        imageName: "test.jpg",
        imageSrc: "data:image/jpeg;base64,test",
        rawFile: new File(["test"], "test.jpg", { type: "image/jpeg" }),
        imageDims: { width: 100, height: 100 },
      };

      mockConfig.images = [mockImage];
      queueManager.configure(mockConfig);

      (api.inferenceRequest as any).mockResolvedValue({
        workflowId: "workflow-1",
        imageId: "image-1",
      });

      (api.getWorkflowStatus as any).mockResolvedValue({
        overallStatus: "completed",
      });

      (api.getWorkflowResults as any).mockResolvedValue({
        boxes: [],
        labels: [],
      });

      queueManager.enqueue(0, "image-1");

      // Advance timers to process submission
      await vi.advanceTimersByTimeAsync(1000);

      expect(api.inferenceRequest).toHaveBeenCalledWith({
        backendUrl: "http://test-backend.com",
        selectedModel: "pipeline-1",
        imageObject: mockImage,
        curDir: "Test Folder",
        accessToken: "test-token",
        folderId: "folder-1",
      });
      expect(mockWorkflowStore.removeWorkflow).toHaveBeenCalled();
      expect(mockConfig.setImageId).toHaveBeenCalledWith(0, "image-1");
    });

    it("should handle missing image error", async () => {
      mockConfig.images = [];
      queueManager.configure(mockConfig);

      queueManager.enqueue(0, "image-1");
      await vi.advanceTimersByTimeAsync(1000);

      expect(errorLogger.logError).toHaveBeenCalled();
      expect(mockOnError).toHaveBeenCalled();
    });

    it("should handle submission errors", async () => {
      const mockImage = {
        index: 0,
        imageName: "test.jpg",
        imageSrc: "data:image/jpeg;base64,test",
        rawFile: new File(["test"], "test.jpg", { type: "image/jpeg" }),
        imageDims: { width: 100, height: 100 },
      };

      mockConfig.images = [mockImage];
      queueManager.configure(mockConfig);

      (api.inferenceRequest as any).mockRejectedValue(
        new Error("Submission failed"),
      );

      queueManager.enqueue(0, "image-1");
      await vi.advanceTimersByTimeAsync(1000);

      expect(errorLogger.logError).toHaveBeenCalled();
      expect(mockWorkflowStore.updateWorkflowStatus).toHaveBeenCalledWith(
        expect.any(String),
        "failed",
        "Submission failed",
      );
      expect(mockOnError).toHaveBeenCalled();
    });
  });

  describe("polling", () => {
    it("should poll workflow status after submission", async () => {
      const mockImage = {
        index: 0,
        imageName: "test.jpg",
        imageSrc: "data:image/jpeg;base64,test",
        rawFile: new File(["test"], "test.jpg", { type: "image/jpeg" }),
        imageDims: { width: 100, height: 100 },
      };

      mockConfig.images = [mockImage];
      queueManager.configure(mockConfig);

      (api.inferenceRequest as any).mockResolvedValue({
        workflowId: "workflow-1",
        imageId: "image-1",
      });

      let callCount = 0;
      (api.getWorkflowStatus as any).mockImplementation(async () => {
        callCount++;
        if (callCount < 3) {
          return { overallStatus: "processing" };
        }
        return { overallStatus: "completed" };
      });

      (api.getWorkflowResults as any).mockResolvedValue({
        boxes: [],
        labels: [],
      });

      queueManager.enqueue(0, "image-1");

      // Advance past initial delay and first poll
      await vi.advanceTimersByTimeAsync(25000);

      // Should update status during polling
      expect(mockWorkflowStore.updateWorkflowStatus).toHaveBeenCalledWith(
        "workflow-1",
        "processing",
      );
    });

    it("should handle completed workflow", async () => {
      const mockImage = {
        index: 0,
        imageName: "test.jpg",
        imageSrc: "data:image/jpeg;base64,test",
        rawFile: new File(["test"], "test.jpg", { type: "image/jpeg" }),
        imageDims: { width: 100, height: 100 },
      };

      mockConfig.images = [mockImage];
      queueManager.configure(mockConfig);

      (api.inferenceRequest as any).mockResolvedValue({
        workflowId: "workflow-1",
        imageId: "image-1",
      });

      (api.getWorkflowStatus as any).mockResolvedValue({
        overallStatus: "completed",
      });

      (api.getWorkflowResults as any).mockResolvedValue({
        boxes: [],
        labels: [],
      });

      queueManager.enqueue(0, "image-1");
      await vi.runAllTimersAsync();

      expect(api.getWorkflowResults).toHaveBeenCalledWith({
        backendUrl: "http://test-backend.com",
        workflowId: "workflow-1",
        accessToken: "test-token",
      });

      expect(mockOnComplete).toHaveBeenCalledWith(
        "workflow-1",
        0,
        { boxes: [], labels: [] },
        "pipeline-1",
        "Test Pipeline",
      );
    });

    it("should handle failed workflow", async () => {
      const mockImage = {
        index: 0,
        imageName: "test.jpg",
        imageSrc: "data:image/jpeg;base64,test",
        rawFile: new File(["test"], "test.jpg", { type: "image/jpeg" }),
        imageDims: { width: 100, height: 100 },
      };

      mockConfig.images = [mockImage];
      queueManager.configure(mockConfig);

      (api.inferenceRequest as any).mockResolvedValue({
        workflowId: "workflow-1",
        imageId: "image-1",
      });

      (api.getWorkflowStatus as any).mockResolvedValue({
        overallStatus: "failed",
        parent_workflow: {
          error_message: "Processing failed",
        },
      });

      queueManager.enqueue(0, "image-1");
      await vi.runAllTimersAsync();

      expect(mockOnError).toHaveBeenCalledWith(
        "workflow-1",
        0,
        expect.objectContaining({
          message: "Processing failed",
        }),
      );
    });

    it("should handle errors fetching results", async () => {
      const mockImage = {
        index: 0,
        imageName: "test.jpg",
        imageSrc: "data:image/jpeg;base64,test",
        rawFile: new File(["test"], "test.jpg", { type: "image/jpeg" }),
        imageDims: { width: 100, height: 100 },
      };

      mockConfig.images = [mockImage];
      queueManager.configure(mockConfig);

      (api.inferenceRequest as any).mockResolvedValue({
        workflowId: "workflow-1",
        imageId: "image-1",
      });

      (api.getWorkflowStatus as any).mockResolvedValue({
        overallStatus: "completed",
      });

      (api.getWorkflowResults as any).mockRejectedValue(
        new Error("Results fetch failed"),
      );

      queueManager.enqueue(0, "image-1");
      await vi.runAllTimersAsync();

      expect(errorLogger.logError).toHaveBeenCalled();
      expect(mockOnError).toHaveBeenCalledWith(
        "workflow-1",
        0,
        expect.objectContaining({
          message: "Results fetch failed",
        }),
      );
    });

    it("should not fail workflow on polling errors", async () => {
      const mockImage = {
        index: 0,
        imageName: "test.jpg",
        imageSrc: "data:image/jpeg;base64,test",
        rawFile: new File(["test"], "test.jpg", { type: "image/jpeg" }),
        imageDims: { width: 100, height: 100 },
      };

      mockConfig.images = [mockImage];
      queueManager.configure(mockConfig);

      (api.inferenceRequest as any).mockResolvedValue({
        workflowId: "workflow-1",
        imageId: "image-1",
      });

      let callCount = 0;
      (api.getWorkflowStatus as any).mockImplementation(async () => {
        callCount++;
        if (callCount === 1) {
          throw new Error("Network error");
        }
        return { overallStatus: "completed" };
      });

      (api.getWorkflowResults as any).mockResolvedValue({
        boxes: [],
        labels: [],
      });

      queueManager.enqueue(0, "image-1");

      // Advance to allow polling to happen
      await vi.advanceTimersByTimeAsync(25000);

      // Should log error but not call onError
      expect(errorLogger.logError).toHaveBeenCalled();
      // Eventually completes successfully
      await vi.advanceTimersByTimeAsync(15000);
      expect(mockOnComplete).toHaveBeenCalled();
    });
  });

  describe("getStatus", () => {
    it("should return queue status", () => {
      queueManager.configure(mockConfig);

      const status = queueManager.getStatus();
      expect(status).toEqual({
        queueSize: 0,
        hasActiveWorkflow: false,
        activeWorkflowId: null,
      });
    });

    it("should reflect active workflow", async () => {
      const mockImage = {
        index: 0,
        imageName: "test.jpg",
        imageSrc: "data:image/jpeg;base64,test",
        rawFile: new File(["test"], "test.jpg", { type: "image/jpeg" }),
        imageDims: { width: 100, height: 100 },
      };

      mockConfig.images = [mockImage];
      queueManager.configure(mockConfig);

      (api.inferenceRequest as any).mockResolvedValue({
        workflowId: "workflow-1",
        imageId: "image-1",
      });

      (api.getWorkflowStatus as any).mockResolvedValue({
        overallStatus: "processing",
      });

      queueManager.enqueue(0, "image-1");
      await vi.advanceTimersByTimeAsync(1000);

      const status = queueManager.getStatus();
      expect(status.hasActiveWorkflow).toBe(true);
      expect(status.activeWorkflowId).toBe("workflow-1");
    });
  });

  describe("clear", () => {
    it("should clear queue and stop polling", async () => {
      const mockImage = {
        index: 0,
        imageName: "test.jpg",
        imageSrc: "data:image/jpeg;base64,test",
        rawFile: new File(["test"], "test.jpg", { type: "image/jpeg" }),
        imageDims: { width: 100, height: 100 },
      };

      mockConfig.images = [mockImage];
      queueManager.configure(mockConfig);

      (api.inferenceRequest as any).mockResolvedValue({
        workflowId: "workflow-1",
        imageId: "image-1",
      });

      queueManager.enqueue(0, "image-1");
      await vi.advanceTimersByTimeAsync(1000);

      queueManager.clear();

      const status = queueManager.getStatus();
      expect(status.queueSize).toBe(0);
      expect(status.hasActiveWorkflow).toBe(false);
    });
  });

  describe("sequential processing", () => {
    it("should process workflows one at a time", async () => {
      const mockImages = [
        {
          index: 0,
          imageName: "test1.jpg",
          imageSrc: "data:image/jpeg;base64,test1",
          rawFile: new File(["test1"], "test1.jpg", { type: "image/jpeg" }),
          imageDims: { width: 100, height: 100 },
        },
        {
          index: 1,
          imageName: "test2.jpg",
          imageSrc: "data:image/jpeg;base64,test2",
          rawFile: new File(["test2"], "test2.jpg", { type: "image/jpeg" }),
          imageDims: { width: 100, height: 100 },
        },
      ];

      mockConfig.images = mockImages;
      queueManager.configure(mockConfig);

      let workflowCounter = 0;
      (api.inferenceRequest as any).mockImplementation(async () => {
        workflowCounter++;
        return {
          workflowId: `workflow-${workflowCounter}`,
          imageId: `image-${workflowCounter}`,
        };
      });

      (api.getWorkflowStatus as any).mockResolvedValue({
        overallStatus: "completed",
      });

      (api.getWorkflowResults as any).mockResolvedValue({
        boxes: [],
        labels: [],
      });

      // Enqueue both
      queueManager.enqueue(0, "image-1");
      queueManager.enqueue(1, "image-2");

      await vi.runAllTimersAsync();

      // Both should complete
      expect(mockOnComplete).toHaveBeenCalledTimes(2);
      expect(mockOnComplete).toHaveBeenNthCalledWith(
        1,
        "workflow-1",
        0,
        expect.any(Object),
        "pipeline-1",
        "Test Pipeline",
      );
      expect(mockOnComplete).toHaveBeenNthCalledWith(
        2,
        "workflow-2",
        1,
        expect.any(Object),
        "pipeline-1",
        "Test Pipeline",
      );
    });
  });
});
