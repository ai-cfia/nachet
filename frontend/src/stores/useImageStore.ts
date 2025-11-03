import { create } from "zustand";
import { Images } from "@common/types";
import { loadCaptureToCache, nextCacheIndex } from "@common/cacheutils";
import { useDeviceStore } from "./useDeviceStore";

interface ImageState {
  images: Images[];
  currentIndex: number;
  addCapturedImage: (src: string) => Promise<void>;
  addWorkflowToImage: (
    imageIndex: number,
    workflowId: string,
    setAsActive?: boolean,
  ) => void;
  setActiveWorkflow: (imageIndex: number, workflowId: string) => void;
  removeImage: (index: number) => number;
  clearImages: () => void;
  setImages: (images: Images[]) => void;
  setCurrentIndex: (index: number) => void;
  getCurrentImage: () => Images | undefined;
  getImageIndexByImageId: (imageId: string) => number | undefined;
  setImageId: (imageIndex: number, imageId: string) => void;
  updateImageMetadata: (
    imageIndex: number,
    metadata: Partial<
      Pick<
        Images,
        | "imageName"
        | "imageDescription"
        | "deviceBrandId"
        | "deviceModelId"
        | "deviceLensId"
        | "trayCode"
        | "magnification"
      >
    >,
  ) => void;
}

export const useImageStore = create<ImageState>()((set, get) => ({
  images: [],
  currentIndex: 0,

  addCapturedImage: async (src: string) => {
    const state = get();
    const nextIndex = nextCacheIndex(state.currentIndex, state.images);

    // Get current device and sample metadata from device store
    const { deviceSelection, sampleMetadata } = useDeviceStore.getState();

    // Prepare metadata object with only non-empty values
    const metadata = {
      ...(deviceSelection.selectedBrandId && {
        deviceBrandId: deviceSelection.selectedBrandId,
      }),
      ...(deviceSelection.selectedModelId && {
        deviceModelId: deviceSelection.selectedModelId,
      }),
      ...(deviceSelection.selectedLensId && {
        deviceLensId: deviceSelection.selectedLensId,
      }),
      ...(sampleMetadata.trayCode && { trayCode: sampleMetadata.trayCode }),
      ...(sampleMetadata.magnification > 0 && {
        magnification: sampleMetadata.magnification,
      }),
      ...(sampleMetadata.sampleIdPrefix && {
        sampleIdPrefix: sampleMetadata.sampleIdPrefix,
      }),
      ...(sampleMetadata.sampleDescription && {
        imageDescription: sampleMetadata.sampleDescription,
      }),
    };

    // loadCaptureToCache returns a promise that resolves to the new cache
    const newImages = await loadCaptureToCache(
      src,
      state.images,
      nextIndex,
      metadata,
    );

    set({ images: newImages, currentIndex: nextIndex });
  },

  addWorkflowToImage: (imageIndex, workflowId, setAsActive = true) => {
    const state = get();
    const newImages = state.images.map((img) => {
      if (img.index === imageIndex) {
        const newWorkflowIds = img.workflowIds
          ? [...img.workflowIds, workflowId]
          : [workflowId];
        return {
          ...img,
          workflowIds: newWorkflowIds,
          activeWorkflowId: setAsActive ? workflowId : img.activeWorkflowId,
        };
      }
      return img;
    });
    set({ images: newImages });
  },

  setActiveWorkflow: (imageIndex, workflowId) => {
    const state = get();
    const newImages = state.images.map((img) =>
      img.index === imageIndex ? { ...img, activeWorkflowId: workflowId } : img,
    );
    set({ images: newImages });
  },

  removeImage: (index: number) => {
    const state = get();
    const newImages = state.images.filter((item) => item.index !== index);

    // Calculate next index to display after removal
    let nextIndex = 0;
    if (newImages.length > 0) {
      if (index === state.currentIndex) {
        // If removing current image, find next available index
        const currentImageStillExists = newImages.some(
          (img) => img.index === state.currentIndex,
        );
        if (!currentImageStillExists) {
          // Find the closest index
          const indices = newImages
            .map((img) => img.index)
            .sort((a, b) => a - b);
          nextIndex = indices[0] || 0;
        } else {
          nextIndex = state.currentIndex;
        }
      } else {
        nextIndex = state.currentIndex;
      }
    }

    set({ images: newImages, currentIndex: nextIndex });
    return nextIndex;
  },

  clearImages: () => {
    set({ images: [], currentIndex: 0 });
  },

  setImages: (images: Images[]) => {
    set({ images });
  },

  setCurrentIndex: (index: number) => {
    set({ currentIndex: index });
  },

  getCurrentImage: () => {
    const state = get();
    return state.images.find((img) => img.index === state.currentIndex);
  },

  getImageIndexByImageId: (imageId: string | number) => {
    const state = get();
    const image = state.images.find(
      (img) => img.imageId?.toString() === imageId.toString(),
    );
    return image?.index;
  },

  setImageId: (imageIndex: number, imageId: string) => {
    const state = get();
    const newImages = state.images.map((img) =>
      img.index === imageIndex ? { ...img, imageId } : img,
    );
    set({ images: newImages });
  },

  updateImageMetadata: (
    imageIndex: number,
    metadata: Partial<
      Pick<
        Images,
        | "imageName"
        | "imageDescription"
        | "deviceBrandId"
        | "deviceModelId"
        | "deviceLensId"
        | "trayCode"
        | "magnification"
      >
    >,
  ) => {
    const state = get();
    const newImages = state.images.map((img) =>
      img.index === imageIndex ? { ...img, ...metadata } : img,
    );
    set({ images: newImages });
  },
}));
