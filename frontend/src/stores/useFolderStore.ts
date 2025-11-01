/**
 * Folder Store (Zustand)
 *
 * Global state management for folder data.
 * Follows the pattern established by useSpeciesStore.
 */

import { create } from "zustand";

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
  setFolderData: (data: ApiFolderData) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  clearFolderData: () => void;
}

export const useFolderStore = create<FolderState>((set) => ({
  folderData: null,
  isLoading: false,
  error: null,
  setFolderData: (data) => set({ folderData: data, error: null }),
  setLoading: (loading) => set({ isLoading: loading }),
  setError: (error) => set({ error, isLoading: false }),
  clearFolderData: () =>
    set({ folderData: null, error: null, isLoading: false }),
}));
