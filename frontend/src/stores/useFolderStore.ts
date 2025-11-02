/**
 * Folder Store (Zustand)
 *
 * Global state management for folder data.
 * Follows the pattern established by useSpeciesStore.
 */

import { create } from "zustand";
import { AzureStorageDirectoryItem } from "@common/types";

export interface FolderData {
  folderId: string;
  folderName: string;
  folderPrefix: string;
  description: string;
  pictureCount: number;
}

export interface ApiFolderData {
  directories: FolderData[];
}

interface FolderState {
  folderData: ApiFolderData | null;
  isLoading: boolean;
  error: string | null;
  curDir: AzureStorageDirectoryItem | null;
  setFolderData: (data: ApiFolderData) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearFolderData: () => void;
  setCurDir: (dir: AzureStorageDirectoryItem | null) => void;
  clearCurDir: () => void;
}

export const useFolderStore = create<FolderState>((set) => ({
  folderData: null,
  isLoading: false,
  error: null,
  curDir: null,
  setFolderData: (data) => set({ folderData: data, error: null }),
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error, isLoading: false }),
  clearFolderData: () =>
    set({ folderData: null, error: null, isLoading: false }),
  setCurDir: (dir) => set({ curDir: dir }),
  clearCurDir: () => set({ curDir: null }),
}));
