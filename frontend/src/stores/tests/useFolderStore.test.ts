import { describe, it, expect, beforeEach } from "vitest";
import { act } from "@testing-library/react";
import { useFolderStore } from "../useFolderStore";
import type { ApiFolderData } from "../useFolderStore";
import type { AzureStorageDirectoryItem } from "@common/types";

describe("useFolderStore", () => {
  const mockFolderData: ApiFolderData = {
    directories: [
      {
        folderId: "folder-1",
        folderName: "Folder 1",
        folderPrefix: "folder-1/",
        description: "First folder",
        pictureCount: 10,
      },
      {
        folderId: "folder-2",
        folderName: "Folder 2",
        folderPrefix: "folder-2/",
        description: "Second folder",
        pictureCount: 5,
      },
    ],
  };

  const mockCurDir: AzureStorageDirectoryItem = {
    folderId: "current-folder",
    folderName: "Current Folder",
    folderPrefix: "current/",
    description: "Current directory",
    pictureCount: 3,
  };

  beforeEach(() => {
    // Reset store to initial state
    act(() => {
      useFolderStore.setState({
        folderData: null,
        isLoading: false,
        error: null,
        curDir: null,
      });
    });
  });

  describe("Initial State", () => {
    it("should have null folderData", () => {
      expect(useFolderStore.getState().folderData).toBeNull();
    });

    it("should have isLoading false", () => {
      expect(useFolderStore.getState().isLoading).toBe(false);
    });

    it("should have null error", () => {
      expect(useFolderStore.getState().error).toBeNull();
    });

    it("should have null curDir", () => {
      expect(useFolderStore.getState().curDir).toBeNull();
    });
  });

  describe("setFolderData", () => {
    it("should set folder data", () => {
      act(() => {
        useFolderStore.getState().setFolderData(mockFolderData);
      });

      const state = useFolderStore.getState();
      expect(state.folderData).toEqual(mockFolderData);
      expect(state.error).toBeNull();
    });

    it("should clear error when setting folder data", () => {
      act(() => {
        useFolderStore.getState().setError("Previous error");
        useFolderStore.getState().setFolderData(mockFolderData);
      });

      expect(useFolderStore.getState().error).toBeNull();
    });

    it("should update existing folder data", () => {
      const updatedData: ApiFolderData = {
        directories: [
          {
            folderId: "folder-3",
            folderName: "Folder 3",
            folderPrefix: "folder-3/",
            description: "Third folder",
            pictureCount: 15,
          },
        ],
      };

      act(() => {
        useFolderStore.getState().setFolderData(mockFolderData);
        useFolderStore.getState().setFolderData(updatedData);
      });

      const state = useFolderStore.getState();
      expect(state.folderData).toEqual(updatedData);
      expect(state.folderData?.directories).toHaveLength(1);
    });
  });

  describe("setLoading", () => {
    it("should set loading to true", () => {
      act(() => {
        useFolderStore.getState().setLoading(true);
      });

      expect(useFolderStore.getState().isLoading).toBe(true);
    });

    it("should set loading to false", () => {
      act(() => {
        useFolderStore.getState().setLoading(true);
        useFolderStore.getState().setLoading(false);
      });

      expect(useFolderStore.getState().isLoading).toBe(false);
    });
  });

  describe("setError", () => {
    it("should set error message", () => {
      act(() => {
        useFolderStore.getState().setError("Failed to load folders");
      });

      const state = useFolderStore.getState();
      expect(state.error).toBe("Failed to load folders");
      expect(state.isLoading).toBe(false);
    });

    it("should set loading to false when setting error", () => {
      act(() => {
        useFolderStore.getState().setLoading(true);
        useFolderStore.getState().setError("Error occurred");
      });

      const state = useFolderStore.getState();
      expect(state.isLoading).toBe(false);
      expect(state.error).toBe("Error occurred");
    });

    it("should clear error with null", () => {
      act(() => {
        useFolderStore.getState().setError("Error message");
        useFolderStore.getState().setError(null);
      });

      expect(useFolderStore.getState().error).toBeNull();
    });
  });

  describe("clearFolderData", () => {
    it("should clear all state", () => {
      act(() => {
        useFolderStore.getState().setFolderData(mockFolderData);
        useFolderStore.getState().setLoading(true);
        useFolderStore.getState().setError("Some error");
        useFolderStore.getState().clearFolderData();
      });

      const state = useFolderStore.getState();
      expect(state.folderData).toBeNull();
      expect(state.error).toBeNull();
      expect(state.isLoading).toBe(false);
    });

    it("should handle clearing when already cleared", () => {
      act(() => {
        useFolderStore.getState().clearFolderData();
      });

      const state = useFolderStore.getState();
      expect(state.folderData).toBeNull();
      expect(state.error).toBeNull();
      expect(state.isLoading).toBe(false);
    });
  });

  describe("setCurDir", () => {
    it("should set current directory", () => {
      act(() => {
        useFolderStore.getState().setCurDir(mockCurDir);
      });

      expect(useFolderStore.getState().curDir).toEqual(mockCurDir);
    });

    it("should update current directory", () => {
      const updatedDir: AzureStorageDirectoryItem = {
        ...mockCurDir,
        folderName: "Updated Folder",
        pictureCount: 20,
      };

      act(() => {
        useFolderStore.getState().setCurDir(mockCurDir);
        useFolderStore.getState().setCurDir(updatedDir);
      });

      const state = useFolderStore.getState();
      expect(state.curDir?.folderName).toBe("Updated Folder");
      expect(state.curDir?.pictureCount).toBe(20);
    });

    it("should set curDir to null", () => {
      act(() => {
        useFolderStore.getState().setCurDir(mockCurDir);
        useFolderStore.getState().setCurDir(null);
      });

      expect(useFolderStore.getState().curDir).toBeNull();
    });
  });

  describe("clearCurDir", () => {
    it("should clear current directory", () => {
      act(() => {
        useFolderStore.getState().setCurDir(mockCurDir);
        useFolderStore.getState().clearCurDir();
      });

      expect(useFolderStore.getState().curDir).toBeNull();
    });

    it("should handle clearing when already null", () => {
      act(() => {
        useFolderStore.getState().clearCurDir();
      });

      expect(useFolderStore.getState().curDir).toBeNull();
    });
  });

  describe("Loading Workflow", () => {
    it("should follow typical loading workflow", () => {
      // Start loading
      act(() => {
        useFolderStore.getState().setLoading(true);
      });

      expect(useFolderStore.getState().isLoading).toBe(true);

      // Success case
      act(() => {
        useFolderStore.getState().setFolderData(mockFolderData);
        useFolderStore.getState().setLoading(false);
      });

      const state = useFolderStore.getState();
      expect(state.isLoading).toBe(false);
      expect(state.folderData).toEqual(mockFolderData);
      expect(state.error).toBeNull();
    });

    it("should handle error workflow", () => {
      // Start loading
      act(() => {
        useFolderStore.getState().setLoading(true);
      });

      // Error occurs
      act(() => {
        useFolderStore.getState().setError("Network error");
      });

      const state = useFolderStore.getState();
      expect(state.isLoading).toBe(false);
      expect(state.error).toBe("Network error");
      expect(state.folderData).toBeNull();
    });
  });

  describe("State Independence", () => {
    it("should manage folderData and curDir independently", () => {
      act(() => {
        useFolderStore.getState().setFolderData(mockFolderData);
        useFolderStore.getState().setCurDir(mockCurDir);
      });

      const state = useFolderStore.getState();
      expect(state.folderData).toEqual(mockFolderData);
      expect(state.curDir).toEqual(mockCurDir);
    });

    it("should preserve curDir when clearing folderData", () => {
      act(() => {
        useFolderStore.getState().setFolderData(mockFolderData);
        useFolderStore.getState().setCurDir(mockCurDir);
        useFolderStore.getState().clearFolderData();
      });

      const state = useFolderStore.getState();
      expect(state.folderData).toBeNull();
      expect(state.curDir).toEqual(mockCurDir);
    });

    it("should preserve folderData when clearing curDir", () => {
      act(() => {
        useFolderStore.getState().setFolderData(mockFolderData);
        useFolderStore.getState().setCurDir(mockCurDir);
        useFolderStore.getState().clearCurDir();
      });

      const state = useFolderStore.getState();
      expect(state.folderData).toEqual(mockFolderData);
      expect(state.curDir).toBeNull();
    });
  });

  describe("Edge Cases", () => {
    it("should handle empty directories array", () => {
      const emptyData: ApiFolderData = {
        directories: [],
      };

      act(() => {
        useFolderStore.getState().setFolderData(emptyData);
      });

      expect(useFolderStore.getState().folderData?.directories).toHaveLength(0);
    });

    it("should handle multiple error updates", () => {
      act(() => {
        useFolderStore.getState().setError("Error 1");
        useFolderStore.getState().setError("Error 2");
        useFolderStore.getState().setError("Error 3");
      });

      expect(useFolderStore.getState().error).toBe("Error 3");
    });

    it("should handle rapid state changes", () => {
      act(() => {
        useFolderStore.getState().setLoading(true);
        useFolderStore.getState().setFolderData(mockFolderData);
        useFolderStore.getState().setLoading(false);
        useFolderStore.getState().setCurDir(mockCurDir);
        useFolderStore.getState().clearCurDir();
      });

      const state = useFolderStore.getState();
      expect(state.isLoading).toBe(false);
      expect(state.folderData).toEqual(mockFolderData);
      expect(state.curDir).toBeNull();
    });
  });
});
