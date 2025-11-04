import { describe, it, expect, beforeEach, vi } from "vitest";
import { act } from "@testing-library/react";
import { useBatchUploadStore } from "../useBatchUploadStore";
import { createMockFile } from "./testUtils";
import type { WorkflowStatus } from "@common/types";

describe("useBatchUploadStore", () => {
  beforeEach(() => {
    // Reset store to initial state before each test
    act(() => {
      useBatchUploadStore.setState({
        currentSession: null,
        uploads: new Map(),
      });
    });
  });

  describe("Session Management", () => {
    it("should create a new session with correct initial state", () => {
      act(() => {
        useBatchUploadStore.getState().createSession("session-123", 5);
      });

      const { currentSession } = useBatchUploadStore.getState();
      expect(currentSession).toBeDefined();
      expect(currentSession?.sessionId).toBe("session-123");
      expect(currentSession?.totalFiles).toBe(5);
      expect(currentSession?.completedFiles).toBe(0);
      expect(currentSession?.failedFiles).toBe(0);
      expect(currentSession?.status).toBe("in_progress");
      expect(currentSession?.timestamp).toBeGreaterThan(0);
    });

    it("should clear previous uploads when creating a new session", () => {
      const file = createMockFile();

      act(() => {
        useBatchUploadStore.getState().createSession("session-1", 1);
        useBatchUploadStore.getState().addUpload("workflow-1", file);
      });

      expect(useBatchUploadStore.getState().uploads.size).toBe(1);

      act(() => {
        useBatchUploadStore.getState().createSession("session-2", 3);
      });

      expect(useBatchUploadStore.getState().uploads.size).toBe(0);
    });

    it("should update session progress when uploads complete", () => {
      const file1 = createMockFile("file1.jpg");
      const file2 = createMockFile("file2.jpg");

      act(() => {
        useBatchUploadStore.getState().createSession("session-123", 2);
        useBatchUploadStore.getState().addUpload("workflow-1", file1);
        useBatchUploadStore.getState().addUpload("workflow-2", file2);
      });

      act(() => {
        useBatchUploadStore
          .getState()
          .updateUploadStatus("workflow-1", "completed");
      });

      let session = useBatchUploadStore.getState().currentSession;
      expect(session?.completedFiles).toBe(1);
      expect(session?.failedFiles).toBe(0);
      expect(session?.status).toBe("in_progress");

      act(() => {
        useBatchUploadStore
          .getState()
          .updateUploadStatus("workflow-2", "completed");
      });

      session = useBatchUploadStore.getState().currentSession;
      expect(session?.completedFiles).toBe(2);
      expect(session?.status).toBe("completed");
    });

    it("should mark session as failed when all uploads fail", () => {
      const file1 = createMockFile("file1.jpg");
      const file2 = createMockFile("file2.jpg");

      act(() => {
        useBatchUploadStore.getState().createSession("session-123", 2);
        useBatchUploadStore.getState().addUpload("workflow-1", file1);
        useBatchUploadStore.getState().addUpload("workflow-2", file2);
        useBatchUploadStore
          .getState()
          .updateUploadStatus("workflow-1", "failed", "Error 1");
        useBatchUploadStore
          .getState()
          .updateUploadStatus("workflow-2", "failed", "Error 2");
      });

      const session = useBatchUploadStore.getState().currentSession;
      expect(session?.failedFiles).toBe(2);
      expect(session?.completedFiles).toBe(0);
      expect(session?.status).toBe("failed");
    });

    it("should mark session as partial when some uploads fail", () => {
      const file1 = createMockFile("file1.jpg");
      const file2 = createMockFile("file2.jpg");

      act(() => {
        useBatchUploadStore.getState().createSession("session-123", 2);
        useBatchUploadStore.getState().addUpload("workflow-1", file1);
        useBatchUploadStore.getState().addUpload("workflow-2", file2);
        useBatchUploadStore
          .getState()
          .updateUploadStatus("workflow-1", "completed");
        useBatchUploadStore
          .getState()
          .updateUploadStatus("workflow-2", "failed", "Error");
      });

      const session = useBatchUploadStore.getState().currentSession;
      expect(session?.completedFiles).toBe(1);
      expect(session?.failedFiles).toBe(1);
      expect(session?.status).toBe("partial");
    });

    it("should clear session and all uploads", () => {
      const file = createMockFile();

      act(() => {
        useBatchUploadStore.getState().createSession("session-123", 1);
        useBatchUploadStore.getState().addUpload("workflow-1", file);
      });

      expect(useBatchUploadStore.getState().currentSession).toBeDefined();
      expect(useBatchUploadStore.getState().uploads.size).toBe(1);

      act(() => {
        useBatchUploadStore.getState().clearSession();
      });

      expect(useBatchUploadStore.getState().currentSession).toBeNull();
      expect(useBatchUploadStore.getState().uploads.size).toBe(0);
    });
  });

  describe("Upload Workflow Management", () => {
    it("should add upload with pending status by default", () => {
      const file = createMockFile("test.jpg", 2048);

      act(() => {
        useBatchUploadStore.getState().addUpload("workflow-123", file);
      });

      const upload = useBatchUploadStore.getState().uploads.get("workflow-123");
      expect(upload).toBeDefined();
      expect(upload?.workflowId).toBe("workflow-123");
      expect(upload?.fileName).toBe("test.jpg");
      expect(upload?.fileSize).toBe(2048);
      expect(upload?.status).toBe("pending");
      expect(upload?.error).toBeNull();
      expect(upload?.startedAt).toBeGreaterThan(0);
      expect(upload?.lastCheckedAt).toBeGreaterThan(0);
    });

    it("should add upload with queued status when queuePosition provided", () => {
      const file = createMockFile();

      act(() => {
        useBatchUploadStore.getState().addUpload("workflow-123", file, 5);
      });

      const upload = useBatchUploadStore.getState().uploads.get("workflow-123");
      expect(upload?.status).toBe("queued");
      expect(upload?.queuePosition).toBe(5);
    });

    it("should update upload status correctly", () => {
      const file = createMockFile();
      const statuses: WorkflowStatus[] = [
        "queued",
        "pending",
        "processing",
        "completed",
      ];

      act(() => {
        useBatchUploadStore.getState().addUpload("workflow-123", file);
      });

      statuses.forEach((status) => {
        act(() => {
          useBatchUploadStore
            .getState()
            .updateUploadStatus("workflow-123", status);
        });

        const upload = useBatchUploadStore
          .getState()
          .uploads.get("workflow-123");
        expect(upload?.status).toBe(status);
      });
    });

    it("should update upload status with error message", () => {
      const file = createMockFile();

      act(() => {
        useBatchUploadStore.getState().addUpload("workflow-123", file);
        useBatchUploadStore
          .getState()
          .updateUploadStatus("workflow-123", "failed", "Network error");
      });

      const upload = useBatchUploadStore.getState().uploads.get("workflow-123");
      expect(upload?.status).toBe("failed");
      expect(upload?.error).toBe("Network error");
    });

    it("should update queue position when provided", () => {
      const file = createMockFile();

      act(() => {
        useBatchUploadStore.getState().addUpload("workflow-123", file, 10);
      });

      expect(
        useBatchUploadStore.getState().uploads.get("workflow-123")
          ?.queuePosition,
      ).toBe(10);

      act(() => {
        useBatchUploadStore
          .getState()
          .updateUploadStatus("workflow-123", "queued", null, 5);
      });

      expect(
        useBatchUploadStore.getState().uploads.get("workflow-123")
          ?.queuePosition,
      ).toBe(5);
    });

    it("should update lastCheckedAt timestamp on status update", () => {
      const file = createMockFile();

      act(() => {
        useBatchUploadStore.getState().addUpload("workflow-123", file);
      });

      const initialTime = useBatchUploadStore
        .getState()
        .uploads.get("workflow-123")?.lastCheckedAt;

      // Wait a bit to ensure timestamp difference
      vi.useFakeTimers();
      vi.advanceTimersByTime(100);

      act(() => {
        useBatchUploadStore
          .getState()
          .updateUploadStatus("workflow-123", "processing");
      });

      const updatedTime = useBatchUploadStore
        .getState()
        .uploads.get("workflow-123")?.lastCheckedAt;

      expect(updatedTime).toBeGreaterThan(initialTime!);
      vi.useRealTimers();
    });

    it("should set upload result data", () => {
      const file = createMockFile();
      const resultData = { inferenceId: "inf-123", boxes: [] };

      act(() => {
        useBatchUploadStore.getState().addUpload("workflow-123", file);
        useBatchUploadStore
          .getState()
          .setUploadResult("workflow-123", resultData);
      });

      const upload = useBatchUploadStore.getState().uploads.get("workflow-123");
      expect(upload?.resultData).toEqual(resultData);
    });

    it("should remove upload from map", () => {
      const file = createMockFile();

      act(() => {
        useBatchUploadStore.getState().createSession("session-1", 1);
        useBatchUploadStore.getState().addUpload("workflow-123", file);
      });

      expect(useBatchUploadStore.getState().uploads.has("workflow-123")).toBe(
        true,
      );

      act(() => {
        useBatchUploadStore.getState().removeUpload("workflow-123");
      });

      expect(useBatchUploadStore.getState().uploads.has("workflow-123")).toBe(
        false,
      );
    });

    it("should update session progress after removing upload", () => {
      const file1 = createMockFile("file1.jpg");
      const file2 = createMockFile("file2.jpg");

      act(() => {
        useBatchUploadStore.getState().createSession("session-1", 2);
        useBatchUploadStore.getState().addUpload("workflow-1", file1);
        useBatchUploadStore.getState().addUpload("workflow-2", file2);
        useBatchUploadStore
          .getState()
          .updateUploadStatus("workflow-1", "completed");
        useBatchUploadStore.getState().removeUpload("workflow-1");
      });

      const session = useBatchUploadStore.getState().currentSession;
      expect(session?.completedFiles).toBe(0); // Should recalculate after removal
    });

    it("should get upload by workflowId", () => {
      const file = createMockFile();

      act(() => {
        useBatchUploadStore.getState().addUpload("workflow-123", file);
      });

      const upload = useBatchUploadStore.getState().getUpload("workflow-123");
      expect(upload).toBeDefined();
      expect(upload?.workflowId).toBe("workflow-123");
    });

    it("should return undefined for non-existent upload", () => {
      const upload = useBatchUploadStore
        .getState()
        .getUpload("non-existent-id");
      expect(upload).toBeUndefined();
    });

    it("should clear all uploads", () => {
      const file1 = createMockFile("file1.jpg");
      const file2 = createMockFile("file2.jpg");

      act(() => {
        useBatchUploadStore.getState().createSession("session-1", 2);
        useBatchUploadStore.getState().addUpload("workflow-1", file1);
        useBatchUploadStore.getState().addUpload("workflow-2", file2);
      });

      expect(useBatchUploadStore.getState().uploads.size).toBe(2);

      act(() => {
        useBatchUploadStore.getState().clearAllUploads();
      });

      expect(useBatchUploadStore.getState().uploads.size).toBe(0);
    });
  });

  describe("Utility Queries", () => {
    it("should get uploads by status", () => {
      const file1 = createMockFile("file1.jpg");
      const file2 = createMockFile("file2.jpg");
      const file3 = createMockFile("file3.jpg");

      act(() => {
        useBatchUploadStore.getState().addUpload("workflow-1", file1);
        useBatchUploadStore.getState().addUpload("workflow-2", file2);
        useBatchUploadStore.getState().addUpload("workflow-3", file3);
        useBatchUploadStore
          .getState()
          .updateUploadStatus("workflow-1", "completed");
        useBatchUploadStore
          .getState()
          .updateUploadStatus("workflow-2", "failed");
      });

      const completedUploads = useBatchUploadStore
        .getState()
        .getUploadsByStatus("completed");
      expect(completedUploads).toHaveLength(1);
      expect(completedUploads[0].workflowId).toBe("workflow-1");

      const failedUploads = useBatchUploadStore
        .getState()
        .getUploadsByStatus("failed");
      expect(failedUploads).toHaveLength(1);
      expect(failedUploads[0].workflowId).toBe("workflow-2");

      const pendingUploads = useBatchUploadStore
        .getState()
        .getUploadsByStatus("pending");
      expect(pendingUploads).toHaveLength(1);
      expect(pendingUploads[0].workflowId).toBe("workflow-3");
    });

    it("should detect active uploads", () => {
      const file1 = createMockFile("file1.jpg");
      const file2 = createMockFile("file2.jpg");

      // No uploads - should be false
      expect(useBatchUploadStore.getState().hasActiveUploads()).toBe(false);

      act(() => {
        useBatchUploadStore.getState().addUpload("workflow-1", file1);
      });

      // Pending upload - should be true
      expect(useBatchUploadStore.getState().hasActiveUploads()).toBe(true);

      act(() => {
        useBatchUploadStore
          .getState()
          .updateUploadStatus("workflow-1", "processing");
      });

      // Processing upload - should be true
      expect(useBatchUploadStore.getState().hasActiveUploads()).toBe(true);

      act(() => {
        useBatchUploadStore.getState().addUpload("workflow-2", file2, 1);
      });

      // Queued upload - should be true
      expect(useBatchUploadStore.getState().hasActiveUploads()).toBe(true);

      act(() => {
        useBatchUploadStore
          .getState()
          .updateUploadStatus("workflow-1", "completed");
        useBatchUploadStore
          .getState()
          .updateUploadStatus("workflow-2", "completed");
      });

      // All completed - should be false
      expect(useBatchUploadStore.getState().hasActiveUploads()).toBe(false);
    });

    it("should handle empty uploads map in queries", () => {
      const uploads = useBatchUploadStore
        .getState()
        .getUploadsByStatus("completed");
      expect(uploads).toEqual([]);

      const hasActive = useBatchUploadStore.getState().hasActiveUploads();
      expect(hasActive).toBe(false);
    });
  });

  describe("Edge Cases", () => {
    it("should handle updateUploadStatus for non-existent workflow", () => {
      act(() => {
        useBatchUploadStore
          .getState()
          .updateUploadStatus("non-existent", "completed");
      });

      // Should not throw, and state should remain unchanged
      expect(useBatchUploadStore.getState().uploads.size).toBe(0);
    });

    it("should handle setUploadResult for non-existent workflow", () => {
      act(() => {
        useBatchUploadStore
          .getState()
          .setUploadResult("non-existent", { data: "test" });
      });

      // Should not throw
      expect(useBatchUploadStore.getState().uploads.size).toBe(0);
    });

    it("should handle updateSessionProgress with no current session", () => {
      act(() => {
        useBatchUploadStore.getState().updateSessionProgress();
      });

      // Should not throw
      expect(useBatchUploadStore.getState().currentSession).toBeNull();
    });

    it("should preserve queue position when not explicitly updated", () => {
      const file = createMockFile();

      act(() => {
        useBatchUploadStore.getState().addUpload("workflow-1", file, 7);
        useBatchUploadStore
          .getState()
          .updateUploadStatus("workflow-1", "pending");
      });

      const upload = useBatchUploadStore.getState().uploads.get("workflow-1");
      expect(upload?.queuePosition).toBe(7); // Should preserve original position
    });
  });
});
