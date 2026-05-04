import { create } from "zustand";

interface VersionCheckState {
  remoteVersion: string | null;
  dialogOpen: boolean;

  setRemoteVersion: (version: string) => void;
  openDialog: () => void;
  closeDialog: () => void;
}

export const useVersionCheckStore = create<VersionCheckState>((set) => ({
  remoteVersion: null,
  dialogOpen: false,

  setRemoteVersion: (remoteVersion) => set({ remoteVersion }),
  openDialog: () => set({ dialogOpen: true }),
  closeDialog: () => set({ dialogOpen: false }),
}));
