import { describe, it, expect, beforeEach } from "vitest";
import { act } from "@testing-library/react";
import { useModalStore } from "../useModalStore";

describe("useModalStore", () => {
  beforeEach(() => {
    // Reset store to initial state
    act(() => {
      useModalStore.getState().closeAllModals();
    });
  });

  describe("Initial State", () => {
    it("should have all modals closed", () => {
      const state = useModalStore.getState();
      expect(state.isSaveOpen).toBe(false);
      expect(state.isBatchUploadOpen).toBe(false);
      expect(state.isUploadOpen).toBe(false);
      expect(state.isModelInfoOpen).toBe(false);
      expect(state.isSampleMetadataOpen).toBe(false);
      expect(state.isImageMetadataOpen).toBe(false);
      expect(state.isSwitchDeviceOpen).toBe(false);
      expect(state.notificationLogOpen).toBe(false);
    });

    it("should have default SaveCapturePopup data", () => {
      const state = useModalStore.getState();
      expect(state.imageFormat).toBe("image/png");
      expect(state.imageLabel).toBe("");
      expect(state.saveIndividualImage).toBe("0");
    });

    it("should have null imageMetadataImageIndex", () => {
      const state = useModalStore.getState();
      expect(state.imageMetadataImageIndex).toBeNull();
      expect(state.imageMetadataMode).toBe("edit");
    });
  });

  describe("Save Capture Modal", () => {
    it("should open save popup", () => {
      act(() => {
        useModalStore.getState().openSavePopup();
      });

      expect(useModalStore.getState().isSaveOpen).toBe(true);
    });

    it("should close save popup", () => {
      act(() => {
        useModalStore.getState().openSavePopup();
        useModalStore.getState().closeSavePopup();
      });

      expect(useModalStore.getState().isSaveOpen).toBe(false);
    });
  });

  describe("Batch Upload Modal", () => {
    it("should open batch upload popup", () => {
      act(() => {
        useModalStore.getState().openBatchUploadPopup();
      });

      expect(useModalStore.getState().isBatchUploadOpen).toBe(true);
    });

    it("should close batch upload popup", () => {
      act(() => {
        useModalStore.getState().openBatchUploadPopup();
        useModalStore.getState().closeBatchUploadPopup();
      });

      expect(useModalStore.getState().isBatchUploadOpen).toBe(false);
    });
  });

  describe("Upload/Load Image Modal", () => {
    it("should open upload popup", () => {
      act(() => {
        useModalStore.getState().openUploadPopup();
      });

      expect(useModalStore.getState().isUploadOpen).toBe(true);
    });

    it("should close upload popup", () => {
      act(() => {
        useModalStore.getState().openUploadPopup();
        useModalStore.getState().closeUploadPopup();
      });

      expect(useModalStore.getState().isUploadOpen).toBe(false);
    });
  });

  describe("Model Selection Modal", () => {
    it("should open model info popup", () => {
      act(() => {
        useModalStore.getState().openModelInfoPopup();
      });

      expect(useModalStore.getState().isModelInfoOpen).toBe(true);
    });

    it("should close model info popup", () => {
      act(() => {
        useModalStore.getState().openModelInfoPopup();
        useModalStore.getState().closeModelInfoPopup();
      });

      expect(useModalStore.getState().isModelInfoOpen).toBe(false);
    });
  });

  describe("Sample Metadata Modal", () => {
    it("should open sample metadata popup", () => {
      act(() => {
        useModalStore.getState().openSampleMetadataPopup();
      });

      expect(useModalStore.getState().isSampleMetadataOpen).toBe(true);
    });

    it("should close sample metadata popup", () => {
      act(() => {
        useModalStore.getState().openSampleMetadataPopup();
        useModalStore.getState().closeSampleMetadataPopup();
      });

      expect(useModalStore.getState().isSampleMetadataOpen).toBe(false);
    });
  });

  describe("Image Metadata Modal", () => {
    it("should open image metadata popup with default edit mode", () => {
      act(() => {
        useModalStore.getState().openImageMetadataPopup(5);
      });

      const state = useModalStore.getState();
      expect(state.isImageMetadataOpen).toBe(true);
      expect(state.imageMetadataImageIndex).toBe(5);
      expect(state.imageMetadataMode).toBe("edit");
    });

    it("should open image metadata popup with delete mode", () => {
      act(() => {
        useModalStore.getState().openImageMetadataPopup(3, "delete");
      });

      const state = useModalStore.getState();
      expect(state.isImageMetadataOpen).toBe(true);
      expect(state.imageMetadataImageIndex).toBe(3);
      expect(state.imageMetadataMode).toBe("delete");
    });

    it("should close image metadata popup and reset state", () => {
      act(() => {
        useModalStore.getState().openImageMetadataPopup(5, "delete");
        useModalStore.getState().closeImageMetadataPopup();
      });

      const state = useModalStore.getState();
      expect(state.isImageMetadataOpen).toBe(false);
      expect(state.imageMetadataImageIndex).toBeNull();
      expect(state.imageMetadataMode).toBe("edit");
    });
  });

  describe("Switch Device Modal", () => {
    it("should open switch device popup", () => {
      act(() => {
        useModalStore.getState().openSwitchDevicePopup();
      });

      expect(useModalStore.getState().isSwitchDeviceOpen).toBe(true);
    });

    it("should close switch device popup", () => {
      act(() => {
        useModalStore.getState().openSwitchDevicePopup();
        useModalStore.getState().closeSwitchDevicePopup();
      });

      expect(useModalStore.getState().isSwitchDeviceOpen).toBe(false);
    });
  });

  describe("Notification Log Modal", () => {
    it("should open notification log", () => {
      act(() => {
        useModalStore.getState().openNotificationLog();
      });

      expect(useModalStore.getState().notificationLogOpen).toBe(true);
    });

    it("should close notification log", () => {
      act(() => {
        useModalStore.getState().openNotificationLog();
        useModalStore.getState().closeNotificationLog();
      });

      expect(useModalStore.getState().notificationLogOpen).toBe(false);
    });
  });

  describe("SaveCapturePopup Data Setters", () => {
    it("should set image format with direct value", () => {
      act(() => {
        useModalStore.getState().setImageFormat("image/jpeg");
      });

      expect(useModalStore.getState().imageFormat).toBe("image/jpeg");
    });

    it("should set image format with function updater", () => {
      // Reset to ensure clean state
      act(() => {
        useModalStore.getState().setImageFormat("image/png");
      });

      act(() => {
        useModalStore.getState().setImageFormat((prev) => prev + "-test");
      });

      expect(useModalStore.getState().imageFormat).toBe("image/png-test");
    });

    it("should set image label with direct value", () => {
      act(() => {
        useModalStore.getState().setImageLabel("Test Label");
      });

      expect(useModalStore.getState().imageLabel).toBe("Test Label");
    });

    it("should set image label with function updater", () => {
      act(() => {
        useModalStore.getState().setImageLabel("Initial");
        useModalStore.getState().setImageLabel((prev) => prev + " Updated");
      });

      expect(useModalStore.getState().imageLabel).toBe("Initial Updated");
    });

    it("should set saveIndividualImage with direct value", () => {
      act(() => {
        useModalStore.getState().setSaveIndividualImage("5");
      });

      expect(useModalStore.getState().saveIndividualImage).toBe("5");
    });

    it("should set saveIndividualImage with function updater", () => {
      act(() => {
        useModalStore.getState().setSaveIndividualImage("10");
        useModalStore
          .getState()
          .setSaveIndividualImage((prev) => (parseInt(prev) + 5).toString());
      });

      expect(useModalStore.getState().saveIndividualImage).toBe("15");
    });
  });

  describe("closeAllModals", () => {
    it("should close all modals at once", () => {
      act(() => {
        useModalStore.getState().openSavePopup();
        useModalStore.getState().openBatchUploadPopup();
        useModalStore.getState().openUploadPopup();
        useModalStore.getState().openModelInfoPopup();
        useModalStore.getState().openSampleMetadataPopup();
        useModalStore.getState().openImageMetadataPopup(5, "delete");
        useModalStore.getState().openSwitchDevicePopup();
        useModalStore.getState().openNotificationLog();
      });

      const beforeClose = useModalStore.getState();
      expect(beforeClose.isSaveOpen).toBe(true);
      expect(beforeClose.isBatchUploadOpen).toBe(true);
      expect(beforeClose.isUploadOpen).toBe(true);

      act(() => {
        useModalStore.getState().closeAllModals();
      });

      const state = useModalStore.getState();
      expect(state.isSaveOpen).toBe(false);
      expect(state.isBatchUploadOpen).toBe(false);
      expect(state.isUploadOpen).toBe(false);
      expect(state.isModelInfoOpen).toBe(false);
      expect(state.isSampleMetadataOpen).toBe(false);
      expect(state.isImageMetadataOpen).toBe(false);
      expect(state.isSwitchDeviceOpen).toBe(false);
      expect(state.notificationLogOpen).toBe(false);
      expect(state.imageMetadataImageIndex).toBeNull();
      expect(state.imageMetadataMode).toBe("edit");
    });
  });

  describe("Modal Isolation", () => {
    it("should not affect other modals when opening one", () => {
      act(() => {
        useModalStore.getState().openSavePopup();
      });

      const state = useModalStore.getState();
      expect(state.isSaveOpen).toBe(true);
      expect(state.isBatchUploadOpen).toBe(false);
      expect(state.isUploadOpen).toBe(false);
      expect(state.isModelInfoOpen).toBe(false);
    });

    it("should allow multiple modals to be open simultaneously", () => {
      act(() => {
        useModalStore.getState().openSavePopup();
        useModalStore.getState().openModelInfoPopup();
      });

      const state = useModalStore.getState();
      expect(state.isSaveOpen).toBe(true);
      expect(state.isModelInfoOpen).toBe(true);
    });
  });
});
