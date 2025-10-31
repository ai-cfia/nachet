import { create } from "zustand";
import { Images, ApiInferenceData } from "@common/types";
import {
  loadCaptureToCache,
  loadResultsToCache,
  nextCacheIndex,
} from "@common/cacheutils";

interface ImageState {
  images: Images[];
  currentIndex: number;
  addCapturedImage: (src: string) => Promise<void>;
  loadInferenceResults: (
    inferenceData: ApiInferenceData,
    imageIndex: number,
  ) => void;
  removeImage: (index: number) => number;
  clearImages: () => void;
  setImages: (images: Images[]) => void;
  setCurrentIndex: (index: number) => void;
  getCurrentImage: () => Images | undefined;
  getImageIndexByImageId: (imageId: string) => number | undefined;
  setImageId: (imageIndex: number, imageId: string) => void;
}

export const useImageStore = create<ImageState>()((set, get) => ({
  images: [],
  currentIndex: 0,

  addCapturedImage: async (src: string) => {
    const state = get();
    const nextIndex = nextCacheIndex(state.currentIndex, state.images);

    // loadCaptureToCache returns a promise that resolves to the new cache
    const newImages = await loadCaptureToCache(src, state.images, nextIndex);

    set({ images: newImages, currentIndex: nextIndex });
  },

  loadInferenceResults: (
    inferenceData: ApiInferenceData,
    imageIndex: number,
  ) => {
    const state = get();
    const newImages = loadResultsToCache(
      inferenceData,
      state.images,
      imageIndex,
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
}));
