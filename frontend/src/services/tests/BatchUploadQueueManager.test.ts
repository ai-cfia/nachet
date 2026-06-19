import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { BatchUploadQueueManager } from "../BatchUploadQueueManager";
import * as api from "@common/api";
import { errorLogger } from "../../logging";

// Mock dependencies
vi.mock("@common/api");
vi.mock("../../logging");

describe("BatchUploadQueueManager", () => {
  let queueManager: BatchUploadQueueManager;
  let mockUploadStore: any;
  let mockOnComplete: any;
  let mockOnError: any;
  let mockGetAccessToken: any;
  let mockConfig: any;

  beforeEach(() => {
    vi.clearAllMocks();
    vi.useFakeTimers();

    queueManager = new BatchUploadQueueManager();

    mockUploadStore = {
      addUpload: vi.fn(),
      updateUploadStatus: vi.fn(),
      setUploadResult: vi.fn(),
      removeUpload: vi.fn(),
    };

    mockOnComplete = vi.fn();
    mockOnError = vi.fn();
    mockGetAccessToken = vi.fn().mockResolvedValue("test-token");

    mockConfig = {
      backendUrl: "http://test-backend.com",
      getAccessToken: mockGetAccessToken,
      scopes: ["test-scope"],
      uploadStore: mockUploadStore,
      onComplete: mockOnComplete,
      onError: mockOnError,
    };

    // Mock FileReader for file conversion
    global.FileReader = class {
      result: string = "data:image/jpeg;base64,testdata";
      onload: (() => void) | null = null;
      onerror: (() => void) | null = null;

      readAsDataURL() {
        setTimeout(() => {
          if (this.onload) this.onload();
        }, 0);
      }
    } as any;
  });

  afterEach(() => {
    vi.useRealTimers();
    queueManager.clear();
  });

  // Helper to create complete metadata with all required fields
  const createMockMetadata = (overrides = {}) => ({
    folderId: "folder-1",
    folderName: "Test Folder",
    pipelineId: "pipeline-1",
    pipelineName: "Test Pipeline",
    seedSampleId: "sample-1",
    sessionId: "session-1",
    seedId: "seed-1",
    sampleIdPrefix: "TEST",
    sampleDescription: "Test sample",
    deviceBrandId: "brand-1",
    deviceModelId: "model-1",
    deviceLensId: "lens-1",
    trayCode: "T001",
    magnification: 10,
    ...overrides,
  });

  describe("configure", () => {
    it("should store configuration", () => {
      queueManager.configure(mockConfig);
      const status = queueManager.getStatus();
      expect(status).toBeDefined();
    });
  });

  describe("enqueue", () => {
    it("should add file to queue", async () => {
      queueManager.configure(mockConfig);

      const mockFile = new File(["test"], "test.jpg", { type: "image/jpeg" });
      const metadata = createMockMetadata();

      queueManager.enqueue(mockFile, metadata);

      expect(mockUploadStore.addUpload).toHaveBeenCalled();
      expect(mockUploadStore.updateUploadStatus).toHaveBeenCalledWith(
        expect.stringContaining("temp-"),
        "queued",
        null,
        1, // queue position
      );
    });

    it("should log error if not configured", () => {
      const mockFile = new File(["test"], "test.jpg", { type: "image/jpeg" });
      const metadata = createMockMetadata();

      queueManager.enqueue(mockFile, metadata);
      expect(errorLogger.logError).toHaveBeenCalled();
    });

    it("should update queue positions when adding multiple files", () => {
      queueManager.configure(mockConfig);

      // Mock batch upload to delay processing
      (api.batchUploadImage as any).mockImplementation(
        () => new Promise(() => {}),
      );

      const mockFile1 = new File(["test1"], "test1.jpg", {
        type: "image/jpeg",
      });
      const mockFile2 = new File(["test2"], "test2.jpg", {
        type: "image/jpeg",
      });
      const mockFile3 = new File(["test3"], "test3.jpg", {
        type: "image/jpeg",
      });

      const metadata = createMockMetadata();

      queueManager.enqueue(mockFile1, metadata);
      queueManager.enqueue(mockFile2, metadata);
      queueManager.enqueue(mockFile3, metadata);

      expect(mockUploadStore.addUpload).toHaveBeenCalledTimes(3);
    });
  });

  describe("processNext", () => {
    it("should process file upload successfully", async () => {
      queueManager.configure(mockConfig);

      const mockFile = new File(["test"], "test.jpg", { type: "image/jpeg" });
      const metadata = createMockMetadata();

      (api.batchUploadImage as any).mockResolvedValue({
        workflowId: "workflow-1",
      });

      (api.getWorkflowStatus as any).mockResolvedValue({
        overallStatus: "completed",
      });

      queueManager.enqueue(mockFile, metadata);
      await vi.advanceTimersByTimeAsync(25000);

      expect(api.batchUploadImage).toHaveBeenCalledWith({
        backendUrl: "http://test-backend.com",
        accessToken: "test-token",
        data: expect.objectContaining({
          ...metadata,
          imageDataUrl: "data:image/jpeg;base64,testdata",
        }),
      });
      expect(mockUploadStore.removeUpload).toHaveBeenCalled();
    });

    it("should handle upload errors", async () => {
      queueManager.configure(mockConfig);

      const mockFile = new File(["test"], "test.jpg", { type: "image/jpeg" });
      const metadata = createMockMetadata();

      (api.batchUploadImage as any).mockRejectedValue(
        new Error("Upload failed"),
      );

      queueManager.enqueue(mockFile, metadata);
      await vi.advanceTimersByTimeAsync(1000);

      expect(errorLogger.logError).toHaveBeenCalled();
      expect(mockUploadStore.updateUploadStatus).toHaveBeenCalledWith(
        expect.any(String),
        "failed",
        "Upload failed",
      );
      expect(mockOnError).toHaveBeenCalled();
    });

    it("should handle missing workflow ID in response", async () => {
      queueManager.configure(mockConfig);

      const mockFile = new File(["test"], "test.jpg", { type: "image/jpeg" });
      const metadata = createMockMetadata();

      (api.batchUploadImage as any).mockResolvedValue({
        // No workflowId
      });

      queueManager.enqueue(mockFile, metadata);
      await vi.advanceTimersByTimeAsync(1000);

      expect(errorLogger.logError).toHaveBeenCalled();
      expect(mockOnError).toHaveBeenCalled();
    });
  });

  describe("polling", () => {
    it("should poll workflow status after upload", async () => {
      queueManager.configure(mockConfig);

      const mockFile = new File(["test"], "test.jpg", { type: "image/jpeg" });
      const metadata = createMockMetadata();

      (api.batchUploadImage as any).mockResolvedValue({
        workflowId: "workflow-1",
      });

      let callCount = 0;
      (api.getWorkflowStatus as any).mockImplementation(async () => {
        callCount++;
        if (callCount < 3) {
          return { overallStatus: "processing" };
        }
        return { overallStatus: "completed" };
      });

      queueManager.enqueue(mockFile, metadata);
      await vi.advanceTimersByTimeAsync(25000);

      expect(mockUploadStore.updateUploadStatus).toHaveBeenCalledWith(
        "workflow-1",
        "processing",
      );
    });

    it("should handle completed workflow without results", async () => {
      queueManager.configure(mockConfig);

      const mockFile = new File(["test"], "test.jpg", { type: "image/jpeg" });
      const metadata = createMockMetadata();

      (api.batchUploadImage as any).mockResolvedValue({
        workflowId: "workflow-1",
      });

      (api.getWorkflowStatus as any).mockResolvedValue({
        overallStatus: "completed",
      });

      queueManager.enqueue(mockFile, metadata);
      await vi.advanceTimersByTimeAsync(25000);

      // Batch uploads don't fetch results, just call onComplete with null
      expect(mockOnComplete).toHaveBeenCalledWith("workflow-1", mockFile, null);
    });

    it("should handle failed workflow", async () => {
      queueManager.configure(mockConfig);

      const mockFile = new File(["test"], "test.jpg", { type: "image/jpeg" });
      const metadata = createMockMetadata();

      (api.batchUploadImage as any).mockResolvedValue({
        workflowId: "workflow-1",
      });

      (api.getWorkflowStatus as any).mockResolvedValue({
        overallStatus: "failed",
        parent_workflow: {
          error_message: "Processing failed",
        },
      });

      queueManager.enqueue(mockFile, metadata);
      await vi.advanceTimersByTimeAsync(25000);

      expect(mockOnError).toHaveBeenCalledWith(
        "workflow-1",
        mockFile,
        expect.objectContaining({
          message: "Processing failed",
        }),
      );
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
        activeFileName: null,
      });
    });

    it("should reflect active workflow", async () => {
      queueManager.configure(mockConfig);

      const mockFile = new File(["test"], "test.jpg", { type: "image/jpeg" });
      const metadata = createMockMetadata();

      (api.batchUploadImage as any).mockResolvedValue({
        workflowId: "workflow-1",
      });

      (api.getWorkflowStatus as any).mockResolvedValue({
        overallStatus: "processing",
      });

      queueManager.enqueue(mockFile, metadata);
      await vi.advanceTimersByTimeAsync(1000);

      const status = queueManager.getStatus();
      expect(status.hasActiveWorkflow).toBe(true);
      expect(status.activeWorkflowId).toBe("workflow-1");
      expect(status.activeFileName).toBe("test.jpg");
    });
  });

  describe("clear", () => {
    it("should clear queue and stop polling", async () => {
      queueManager.configure(mockConfig);

      const mockFile = new File(["test"], "test.jpg", { type: "image/jpeg" });
      const metadata = createMockMetadata();

      (api.batchUploadImage as any).mockResolvedValue({
        workflowId: "workflow-1",
      });

      queueManager.enqueue(mockFile, metadata);
      await vi.advanceTimersByTimeAsync(1000);

      queueManager.clear();

      const status = queueManager.getStatus();
      expect(status.queueSize).toBe(0);
      expect(status.hasActiveWorkflow).toBe(false);
    });
  });

  describe("sequential processing", () => {
    it("should process uploads one at a time", async () => {
      queueManager.configure(mockConfig);

      const mockFile1 = new File(["test1"], "test1.jpg", {
        type: "image/jpeg",
      });
      const mockFile2 = new File(["test2"], "test2.jpg", {
        type: "image/jpeg",
      });

      const metadata = createMockMetadata();

      let uploadCounter = 0;
      (api.batchUploadImage as any).mockImplementation(async () => {
        uploadCounter++;
        return { workflowId: `workflow-${uploadCounter}` };
      });

      (api.getWorkflowStatus as any).mockResolvedValue({
        overallStatus: "completed",
      });

      queueManager.enqueue(mockFile1, metadata);
      queueManager.enqueue(mockFile2, metadata);

      // Allow both uploads to complete with delays between them
      await vi.advanceTimersByTimeAsync(60000);

      // Both should complete
      expect(mockOnComplete).toHaveBeenCalledTimes(2);
      expect(mockOnComplete).toHaveBeenNthCalledWith(
        1,
        "workflow-1",
        mockFile1,
        null,
      );
      expect(mockOnComplete).toHaveBeenNthCalledWith(
        2,
        "workflow-2",
        mockFile2,
        null,
      );
    });
  });

  describe("file conversion", () => {
    it("should convert file to data URL", async () => {
      queueManager.configure(mockConfig);

      const mockFile = new File(["test"], "test.jpg", { type: "image/jpeg" });
      const metadata = createMockMetadata();

      (api.batchUploadImage as any).mockResolvedValue({
        workflowId: "workflow-1",
      });

      (api.getWorkflowStatus as any).mockResolvedValue({
        overallStatus: "completed",
      });

      queueManager.enqueue(mockFile, metadata);
      await vi.advanceTimersByTimeAsync(1000);

      expect(api.batchUploadImage).toHaveBeenCalledWith(
        expect.objectContaining({
          data: expect.objectContaining({
            imageDataUrl: "data:image/jpeg;base64,testdata",
          }),
        }),
      );
    });
  });
});
