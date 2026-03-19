import { create } from "zustand";
import type { Images, ImageMetadata } from "@common/types";
import { useMetadataDefaultsStore } from "@stores/useMetadataDefaultsStore";

interface ImageState {
  images: Images[];
  currentIndex: number;
  addImage: (src: string, dims: number[], imageName?: string) => void;
  removeImage: (index: number) => void;
  setCurrentIndex: (index: number) => void;
  clearImages: () => void;
  getCurrentImage: () => Images | undefined;
  updateImageMetadata: (index: number, metadata: ImageMetadata) => void;
}

export const useImageStore = create<ImageState>()((set, get) => ({
  images: [],
  currentIndex: 0,

  addImage: (src: string, dims: number[], imageName?: string) => {
    const state = get();
    const nextIndex =
      state.images.length > 0
        ? Math.max(...state.images.map((img) => img.index)) + 1
        : 0;
    const defaults = useMetadataDefaultsStore.getState().defaults;
    const prefix = defaults.namePrefix || "image";
    const seq = String(nextIndex + 1).padStart(4, "0");
    const metadata: ImageMetadata = {
      imageName: imageName ?? `${prefix}-${seq}`,
      deviceBrandId: defaults.deviceBrandId,
      deviceModelId: defaults.deviceModelId,
      deviceLensId: defaults.deviceLensId,
      trayCode: defaults.trayCode,
      magnification: defaults.magnification,
      description: defaults.description,
    };
    const newImage: Images = {
      index: nextIndex,
      src,
      imageDims: dims,
      metadata,
    };
    set({ images: [...state.images, newImage], currentIndex: nextIndex });
  },

  removeImage: (index: number) => {
    const state = get();
    const newImages = state.images.filter((img) => img.index !== index);

    let nextIndex = 0;
    if (newImages.length > 0) {
      if (index === state.currentIndex) {
        const indices = newImages.map((img) => img.index).sort((a, b) => a - b);
        nextIndex = indices[0];
      } else {
        nextIndex = state.currentIndex;
      }
    }

    set({ images: newImages, currentIndex: nextIndex });
  },

  setCurrentIndex: (index: number) => {
    set({ currentIndex: index });
  },

  clearImages: () => {
    set({ images: [], currentIndex: 0 });
  },

  getCurrentImage: () => {
    const state = get();
    return state.images.find((img) => img.index === state.currentIndex);
  },

  updateImageMetadata: (index: number, metadata: ImageMetadata) => {
    const state = get();
    const newImages = state.images.map((img) =>
      img.index === index ? { ...img, metadata } : img,
    );
    set({ images: newImages });
  },
}));
