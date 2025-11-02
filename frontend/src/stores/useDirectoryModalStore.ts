/**
 * Directory Modal Store (Zustand)
 *
 * Global state management for directory-related modal states.
 * Manages create, edit, and delete directory modal open/close states.
 */

import { create } from "zustand";
import { AzureStorageDirectoryItem } from "@common/types";

interface DirectoryModalState {
  createDirectoryOpen: boolean;
  editDirectoryOpen: boolean;
  delDirectoryOpen: boolean;
  editingFolder: AzureStorageDirectoryItem | null;

  openCreateDirectory: () => void;
  closeCreateDirectory: () => void;
  openEditDirectory: (folder: AzureStorageDirectoryItem) => void;
  closeEditDirectory: () => void;
  openDeleteDirectory: () => void;
  closeDeleteDirectory: () => void;
  setEditingFolder: (folder: AzureStorageDirectoryItem | null) => void;
}

export const useDirectoryModalStore = create<DirectoryModalState>((set) => ({
  createDirectoryOpen: false,
  editDirectoryOpen: false,
  delDirectoryOpen: false,
  editingFolder: null,

  openCreateDirectory: () => set({ createDirectoryOpen: true }),
  closeCreateDirectory: () => set({ createDirectoryOpen: false }),
  openEditDirectory: (folder) =>
    set({ editDirectoryOpen: true, editingFolder: folder }),
  closeEditDirectory: () =>
    set({ editDirectoryOpen: false, editingFolder: null }),
  openDeleteDirectory: () => set({ delDirectoryOpen: true }),
  closeDeleteDirectory: () => set({ delDirectoryOpen: false }),
  setEditingFolder: (folder) => set({ editingFolder: folder }),
}));
