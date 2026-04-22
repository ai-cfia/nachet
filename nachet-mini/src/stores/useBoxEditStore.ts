import { create } from "zustand";
import type { InferenceBox } from "@common/types";

interface BoxEditState {
  isEditing: boolean;
  sourceResultKey: string | null;
  editedBoxes: InferenceBox[];
  selectedBoxIndex: number | null;
  isDrawing: boolean;

  enterEditMode: (resultKey: string, boxes: InferenceBox[]) => void;
  exitEditMode: () => void;
  updateBox: (index: number, box: InferenceBox) => void;
  addBox: (box: InferenceBox) => void;
  deleteBox: (index: number) => void;
  setSelectedBoxIndex: (index: number | null) => void;
  setIsDrawing: (drawing: boolean) => void;
}

let userBoxCounter = 0;

export const generateUserBoxId = (): string =>
  `user-${Date.now()}-${userBoxCounter++}`;

export const useBoxEditStore = create<BoxEditState>()((set) => ({
  isEditing: false,
  sourceResultKey: null,
  editedBoxes: [],
  selectedBoxIndex: null,
  isDrawing: false,

  enterEditMode: (resultKey: string, boxes: InferenceBox[]) => {
    set({
      isEditing: true,
      sourceResultKey: resultKey,
      editedBoxes: boxes.map((b) => ({ ...b })),
      selectedBoxIndex: null,
      isDrawing: false,
    });
  },

  exitEditMode: () => {
    set({
      isEditing: false,
      sourceResultKey: null,
      editedBoxes: [],
      selectedBoxIndex: null,
      isDrawing: false,
    });
  },

  updateBox: (index: number, box: InferenceBox) => {
    set((state) => {
      const newBoxes = [...state.editedBoxes];
      newBoxes[index] = box;
      return { editedBoxes: newBoxes };
    });
  },

  addBox: (box: InferenceBox) => {
    set((state) => ({
      editedBoxes: [...state.editedBoxes, box],
      isDrawing: false,
    }));
  },

  deleteBox: (index: number) => {
    set((state) => {
      const newBoxes = state.editedBoxes.filter((_, i) => i !== index);
      const newSelected =
        state.selectedBoxIndex === index
          ? null
          : state.selectedBoxIndex !== null && state.selectedBoxIndex > index
            ? state.selectedBoxIndex - 1
            : state.selectedBoxIndex;
      return { editedBoxes: newBoxes, selectedBoxIndex: newSelected };
    });
  },

  setSelectedBoxIndex: (index: number | null) => {
    set({ selectedBoxIndex: index });
  },

  setIsDrawing: (drawing: boolean) => {
    set({ isDrawing: drawing, selectedBoxIndex: null });
  },
}));
