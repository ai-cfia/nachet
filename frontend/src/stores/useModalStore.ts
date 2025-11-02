import { create } from "zustand";

/**
 * Modal Store
 *
 * Centralized state management for modal/popup dialogs.
 * Eliminates prop drilling from body.tsx through component hierarchy.
 *
 * Currently manages 7 microscope-related modals:
 * - Save Capture
 * - Batch Upload
 * - Upload/Load Image
 * - Model Selection
 * - Device Info
 * - Switch Device
 * - Notification Log
 */

interface ModalState {
  // Modal open/closed states
  isSaveOpen: boolean;
  isBatchUploadOpen: boolean;
  isUploadOpen: boolean;
  isModelInfoOpen: boolean;
  isDeviceInfoOpen: boolean;
  isSwitchDeviceOpen: boolean;
  notificationLogOpen: boolean;

  // Shared data for SaveCapturePopup
  imageFormat: string;
  imageLabel: string;
  saveIndividualImage: string;

  // Actions to control Save Capture modal
  openSavePopup: () => void;
  closeSavePopup: () => void;

  // Actions to control Batch Upload modal
  openBatchUploadPopup: () => void;
  closeBatchUploadPopup: () => void;

  // Actions to control Upload/Load Image modal
  openUploadPopup: () => void;
  closeUploadPopup: () => void;

  // Actions to control Model Selection modal
  openModelInfoPopup: () => void;
  closeModelInfoPopup: () => void;

  // Actions to control Device Info modal
  openDeviceInfoPopup: () => void;
  closeDeviceInfoPopup: () => void;

  // Actions to control Switch Device modal
  openSwitchDevicePopup: () => void;
  closeSwitchDevicePopup: () => void;

  // Actions to control Notification Log modal
  openNotificationLog: () => void;
  closeNotificationLog: () => void;

  // Actions to update SaveCapturePopup data
  setImageFormat: (format: string | ((prev: string) => string)) => void;
  setImageLabel: (label: string | ((prev: string) => string)) => void;
  setSaveIndividualImage: (value: string | ((prev: string) => string)) => void;

  // Utility to close all modals
  closeAllModals: () => void;
}

export const useModalStore = create<ModalState>()((set) => ({
  // Initial state - all modals closed
  isSaveOpen: false,
  isBatchUploadOpen: false,
  isUploadOpen: false,
  isModelInfoOpen: false,
  isDeviceInfoOpen: false,
  isSwitchDeviceOpen: false,
  notificationLogOpen: false,

  // Initial data for SaveCapturePopup
  imageFormat: "image/png",
  imageLabel: "",
  saveIndividualImage: "0",

  // Save Capture modal actions
  openSavePopup: () => set({ isSaveOpen: true }),
  closeSavePopup: () => set({ isSaveOpen: false }),

  // Batch Upload modal actions
  openBatchUploadPopup: () => set({ isBatchUploadOpen: true }),
  closeBatchUploadPopup: () => set({ isBatchUploadOpen: false }),

  // Upload/Load Image modal actions
  openUploadPopup: () => set({ isUploadOpen: true }),
  closeUploadPopup: () => set({ isUploadOpen: false }),

  // Model Selection modal actions
  openModelInfoPopup: () => set({ isModelInfoOpen: true }),
  closeModelInfoPopup: () => set({ isModelInfoOpen: false }),

  // Device Info modal actions
  openDeviceInfoPopup: () => set({ isDeviceInfoOpen: true }),
  closeDeviceInfoPopup: () => set({ isDeviceInfoOpen: false }),

  // Switch Device modal actions
  openSwitchDevicePopup: () => set({ isSwitchDeviceOpen: true }),
  closeSwitchDevicePopup: () => set({ isSwitchDeviceOpen: false }),

  // Notification Log modal actions
  openNotificationLog: () => set({ notificationLogOpen: true }),
  closeNotificationLog: () => set({ notificationLogOpen: false }),

  // SaveCapturePopup data setters
  setImageFormat: (format) =>
    set((state) => ({
      imageFormat:
        typeof format === "function" ? format(state.imageFormat) : format,
    })),
  setImageLabel: (label) =>
    set((state) => ({
      imageLabel: typeof label === "function" ? label(state.imageLabel) : label,
    })),
  setSaveIndividualImage: (value) =>
    set((state) => ({
      saveIndividualImage:
        typeof value === "function" ? value(state.saveIndividualImage) : value,
    })),

  // Utility to close all modals at once
  closeAllModals: () =>
    set({
      isSaveOpen: false,
      isBatchUploadOpen: false,
      isUploadOpen: false,
      isModelInfoOpen: false,
      isDeviceInfoOpen: false,
      isSwitchDeviceOpen: false,
      notificationLogOpen: false,
    }),
}));
