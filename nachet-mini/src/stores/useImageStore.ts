import { create } from "zustand";
import type { Images } from "@common/types";

interface ImageState {
  images: Images[];
  currentIndex: number;
  addImage: (src: string, dims: number[]) => void;
  removeImage: (index: number) => void;
  setCurrentIndex: (index: number) => void;
  clearImages: () => void;
  getCurrentImage: () => Images | undefined;
}

export const useImageStore = create<ImageState>()((set, get) => ({
  images: [],
  currentIndex: 0,

  addImage: (src: string, dims: number[]) => {
    const state = get();
    const nextIndex =
      state.images.length > 0
        ? Math.max(...state.images.map((img) => img.index)) + 1
        : 0;
    const newImage: Images = { index: nextIndex, src, imageDims: dims };
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
}));
