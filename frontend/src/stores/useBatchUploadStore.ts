import { create } from "zustand";
import { WorkflowStatus } from "@common/types";

/**
 * Information about a batch upload session
 */
export interface BatchSessionInfo {
  sessionId: string;
  timestamp: number;
  totalFiles: number;
  completedFiles: number;
  failedFiles: number;
  status: "in_progress" | "completed" | "partial" | "failed";
}

/**
 * Information about an individual file upload workflow
 */
export interface UploadWorkflowInfo {
  workflowId: string; // Backend workflow ID (or temp ID if queued)
  file: File;
  fileName: string;
  fileSize: number;
  status: WorkflowStatus;
  startedAt: number;
  lastCheckedAt: number;
  error: string | null;
  queuePosition?: number; // Position in queue (for queued items)
  resultData?: unknown; // Store the workflow result when completed
}

/**
 * Batch upload store - stores batch session and upload workflow data.
 * No reactive triggers, no queue management.
 * Queue logic handled by BatchUploadQueueManager service.
 */
interface BatchUploadState {
  currentSession: BatchSessionInfo | null;
  uploads: Map<string, UploadWorkflowInfo>;

  // Session management
  createSession: (sessionId: string, totalFiles: number) => void;
  updateSessionProgress: () => void;
  clearSession: () => void;

  // Upload workflow management
  addUpload: (workflowId: string, file: File, queuePosition?: number) => void;
  updateUploadStatus: (
    workflowId: string,
    status: WorkflowStatus,
    error?: string | null,
    queuePosition?: number,
  ) => void;
  setUploadResult: (workflowId: string, resultData: unknown) => void;
  removeUpload: (workflowId: string) => void;
  getUpload: (workflowId: string) => UploadWorkflowInfo | undefined;
  clearAllUploads: () => void;

  // Utility queries
  getUploadsByStatus: (status: WorkflowStatus) => UploadWorkflowInfo[];
  hasActiveUploads: () => boolean;
}

export const useBatchUploadStore = create<BatchUploadState>()((set, get) => ({
  currentSession: null,
  uploads: new Map<string, UploadWorkflowInfo>(),

  // Session management
  createSession: (sessionId: string, totalFiles: number) => {
    set({
      currentSession: {
        sessionId,
        timestamp: Date.now(),
        totalFiles,
        completedFiles: 0,
        failedFiles: 0,
        status: "in_progress",
      },
      uploads: new Map(), // Clear previous uploads
    });
  },

  updateSessionProgress: () => {
    const state = get();
    if (!state.currentSession) return;

    const uploads = Array.from(state.uploads.values());
    const completedFiles = uploads.filter(
      (u) => u.status === "completed",
    ).length;
    const failedFiles = uploads.filter((u) => u.status === "failed").length;
    const totalFiles = state.currentSession.totalFiles;

    let status: "in_progress" | "completed" | "partial" | "failed" =
      "in_progress";
    if (completedFiles + failedFiles === totalFiles) {
      if (failedFiles === 0) {
        status = "completed";
      } else if (completedFiles === 0) {
        status = "failed";
      } else {
        status = "partial";
      }
    }

    set({
      currentSession: {
        ...state.currentSession,
        completedFiles,
        failedFiles,
        status,
      },
    });
  },

  clearSession: () => {
    set({
      currentSession: null,
      uploads: new Map(),
    });
  },

  // Upload workflow management
  addUpload: (workflowId: string, file: File, queuePosition?: number) => {
    const now = Date.now();
    const newUpload: UploadWorkflowInfo = {
      workflowId,
      file,
      fileName: file.name,
      fileSize: file.size,
      status: queuePosition !== undefined ? "queued" : "pending",
      startedAt: now,
      lastCheckedAt: now,
      error: null,
      queuePosition,
    };

    set((state) => {
      const newMap = new Map(state.uploads);
      newMap.set(workflowId, newUpload);
      return { uploads: newMap };
    });
  },

  updateUploadStatus: (
    workflowId: string,
    status: WorkflowStatus,
    error: string | null = null,
    queuePosition?: number,
  ) => {
    set((state) => {
      const upload = state.uploads.get(workflowId);
      if (!upload) return state;

      const updatedUpload: UploadWorkflowInfo = {
        ...upload,
        status,
        lastCheckedAt: Date.now(),
        error,
        queuePosition:
          queuePosition !== undefined ? queuePosition : upload.queuePosition,
      };

      const newMap = new Map(state.uploads);
      newMap.set(workflowId, updatedUpload);
      return { uploads: newMap };
    });

    // Update session progress after status change
    get().updateSessionProgress();
  },

  setUploadResult: (workflowId: string, resultData: unknown) => {
    set((state) => {
      const upload = state.uploads.get(workflowId);
      if (!upload) return state;

      const updatedUpload: UploadWorkflowInfo = {
        ...upload,
        resultData,
      };

      const newMap = new Map(state.uploads);
      newMap.set(workflowId, updatedUpload);
      return { uploads: newMap };
    });
  },

  removeUpload: (workflowId: string) => {
    set((state) => {
      const newMap = new Map(state.uploads);
      newMap.delete(workflowId);
      return { uploads: newMap };
    });
    get().updateSessionProgress();
  },

  getUpload: (workflowId: string) => {
    return get().uploads.get(workflowId);
  },

  clearAllUploads: () => {
    set({ uploads: new Map<string, UploadWorkflowInfo>() });
    get().updateSessionProgress();
  },

  // Utility queries
  getUploadsByStatus: (status: WorkflowStatus) => {
    const state = get();
    return Array.from(state.uploads.values()).filter(
      (u) => u.status === status,
    );
  },

  hasActiveUploads: () => {
    const state = get();
    return Array.from(state.uploads.values()).some(
      (u) =>
        u.status === "pending" ||
        u.status === "processing" ||
        u.status === "queued",
    );
  },
}));
