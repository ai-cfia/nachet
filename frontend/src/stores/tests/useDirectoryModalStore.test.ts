import { describe, it, expect, beforeEach } from "vitest";
import { act } from "@testing-library/react";
import { useDirectoryModalStore } from "../useDirectoryModalStore";
import type { AzureStorageDirectoryItem } from "@common/types";

describe("useDirectoryModalStore", () => {
  const mockFolder: AzureStorageDirectoryItem = {
    folderId: "folder-123",
    folderName: "Test Folder",
    folderPrefix: "test-folder/",
    description: "Test folder description",
    pictureCount: 5,
  };

  beforeEach(() => {
    // Reset store to initial state
    act(() => {
      useDirectoryModalStore.setState({
        createDirectoryOpen: false,
        editDirectoryOpen: false,
        delDirectoryOpen: false,
        editingFolder: null,
      });
    });
  });

  describe("Initial State", () => {
    it("should have all modals closed", () => {
      const state = useDirectoryModalStore.getState();
      expect(state.createDirectoryOpen).toBe(false);
      expect(state.editDirectoryOpen).toBe(false);
      expect(state.delDirectoryOpen).toBe(false);
    });

    it("should have null editingFolder", () => {
      const state = useDirectoryModalStore.getState();
      expect(state.editingFolder).toBeNull();
    });
  });

  describe("Create Directory Modal", () => {
    it("should open create directory modal", () => {
      act(() => {
        useDirectoryModalStore.getState().openCreateDirectory();
      });

      expect(useDirectoryModalStore.getState().createDirectoryOpen).toBe(true);
    });

    it("should close create directory modal", () => {
      act(() => {
        useDirectoryModalStore.getState().openCreateDirectory();
        useDirectoryModalStore.getState().closeCreateDirectory();
      });

      expect(useDirectoryModalStore.getState().createDirectoryOpen).toBe(false);
    });
  });

  describe("Edit Directory Modal", () => {
    it("should open edit directory modal with folder", () => {
      act(() => {
        useDirectoryModalStore.getState().openEditDirectory(mockFolder);
      });

      const state = useDirectoryModalStore.getState();
      expect(state.editDirectoryOpen).toBe(true);
      expect(state.editingFolder).toEqual(mockFolder);
    });

    it("should close edit directory modal and clear editingFolder", () => {
      act(() => {
        useDirectoryModalStore.getState().openEditDirectory(mockFolder);
        useDirectoryModalStore.getState().closeEditDirectory();
      });

      const state = useDirectoryModalStore.getState();
      expect(state.editDirectoryOpen).toBe(false);
      expect(state.editingFolder).toBeNull();
    });
  });

  describe("Delete Directory Modal", () => {
    it("should open delete directory modal", () => {
      act(() => {
        useDirectoryModalStore.getState().openDeleteDirectory();
      });

      expect(useDirectoryModalStore.getState().delDirectoryOpen).toBe(true);
    });

    it("should close delete directory modal", () => {
      act(() => {
        useDirectoryModalStore.getState().openDeleteDirectory();
        useDirectoryModalStore.getState().closeDeleteDirectory();
      });

      expect(useDirectoryModalStore.getState().delDirectoryOpen).toBe(false);
    });
  });

  describe("setEditingFolder", () => {
    it("should set editing folder", () => {
      act(() => {
        useDirectoryModalStore.getState().setEditingFolder(mockFolder);
      });

      expect(useDirectoryModalStore.getState().editingFolder).toEqual(
        mockFolder,
      );
    });

    it("should clear editing folder with null", () => {
      act(() => {
        useDirectoryModalStore.getState().setEditingFolder(mockFolder);
        useDirectoryModalStore.getState().setEditingFolder(null);
      });

      expect(useDirectoryModalStore.getState().editingFolder).toBeNull();
    });

    it("should update editing folder", () => {
      const updatedFolder: AzureStorageDirectoryItem = {
        ...mockFolder,
        folderName: "Updated Folder",
        pictureCount: 10,
      };

      act(() => {
        useDirectoryModalStore.getState().setEditingFolder(mockFolder);
        useDirectoryModalStore.getState().setEditingFolder(updatedFolder);
      });

      const state = useDirectoryModalStore.getState();
      expect(state.editingFolder?.folderName).toBe("Updated Folder");
      expect(state.editingFolder?.pictureCount).toBe(10);
    });
  });

  describe("Modal State Isolation", () => {
    it("should not affect other modals when opening create directory", () => {
      act(() => {
        useDirectoryModalStore.getState().openCreateDirectory();
      });

      const state = useDirectoryModalStore.getState();
      expect(state.createDirectoryOpen).toBe(true);
      expect(state.editDirectoryOpen).toBe(false);
      expect(state.delDirectoryOpen).toBe(false);
    });

    it("should not affect other modals when opening edit directory", () => {
      act(() => {
        useDirectoryModalStore.getState().openEditDirectory(mockFolder);
      });

      const state = useDirectoryModalStore.getState();
      expect(state.createDirectoryOpen).toBe(false);
      expect(state.editDirectoryOpen).toBe(true);
      expect(state.delDirectoryOpen).toBe(false);
    });

    it("should not affect other modals when opening delete directory", () => {
      act(() => {
        useDirectoryModalStore.getState().openDeleteDirectory();
      });

      const state = useDirectoryModalStore.getState();
      expect(state.createDirectoryOpen).toBe(false);
      expect(state.editDirectoryOpen).toBe(false);
      expect(state.delDirectoryOpen).toBe(true);
    });

    it("should allow multiple modals to be open simultaneously", () => {
      act(() => {
        useDirectoryModalStore.getState().openCreateDirectory();
        useDirectoryModalStore.getState().openDeleteDirectory();
      });

      const state = useDirectoryModalStore.getState();
      expect(state.createDirectoryOpen).toBe(true);
      expect(state.delDirectoryOpen).toBe(true);
    });
  });

  describe("Workflow Scenarios", () => {
    it("should handle edit workflow - open with folder, close to clear", () => {
      act(() => {
        useDirectoryModalStore.getState().openEditDirectory(mockFolder);
      });

      expect(useDirectoryModalStore.getState().editingFolder).toEqual(
        mockFolder,
      );

      act(() => {
        useDirectoryModalStore.getState().closeEditDirectory();
      });

      expect(useDirectoryModalStore.getState().editingFolder).toBeNull();
    });

    it("should handle delete workflow - set folder, open delete modal", () => {
      act(() => {
        useDirectoryModalStore.getState().setEditingFolder(mockFolder);
        useDirectoryModalStore.getState().openDeleteDirectory();
      });

      const state = useDirectoryModalStore.getState();
      expect(state.editingFolder).toEqual(mockFolder);
      expect(state.delDirectoryOpen).toBe(true);
    });

    it("should preserve editingFolder when opening delete modal", () => {
      act(() => {
        useDirectoryModalStore.getState().openEditDirectory(mockFolder);
        useDirectoryModalStore.getState().closeEditDirectory();
        useDirectoryModalStore.getState().setEditingFolder(mockFolder);
        useDirectoryModalStore.getState().openDeleteDirectory();
      });

      expect(useDirectoryModalStore.getState().editingFolder).toEqual(
        mockFolder,
      );
    });
  });

  describe("Edge Cases", () => {
    it("should handle opening edit directory with different folders sequentially", () => {
      const folder1 = { ...mockFolder, folderId: "folder-1" };
      const folder2 = { ...mockFolder, folderId: "folder-2" };

      act(() => {
        useDirectoryModalStore.getState().openEditDirectory(folder1);
      });

      expect(useDirectoryModalStore.getState().editingFolder?.folderId).toBe(
        "folder-1",
      );

      act(() => {
        useDirectoryModalStore.getState().openEditDirectory(folder2);
      });

      expect(useDirectoryModalStore.getState().editingFolder?.folderId).toBe(
        "folder-2",
      );
    });

    it("should handle closing modals that are already closed", () => {
      act(() => {
        useDirectoryModalStore.getState().closeCreateDirectory();
        useDirectoryModalStore.getState().closeEditDirectory();
        useDirectoryModalStore.getState().closeDeleteDirectory();
      });

      const state = useDirectoryModalStore.getState();
      expect(state.createDirectoryOpen).toBe(false);
      expect(state.editDirectoryOpen).toBe(false);
      expect(state.delDirectoryOpen).toBe(false);
    });
  });
});
