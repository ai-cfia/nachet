import { describe, it, expect, beforeEach } from "vitest";
import { useBoxEditStore, generateUserBoxId } from "../useBoxEditStore";
import type { InferenceBox } from "@common/types";

const makeBox = (overrides: Partial<InferenceBox> = {}): InferenceBox => ({
  inferenceId: "inf-1",
  boxId: "box-1",
  classId: "class-1",
  label: "wheat",
  isVerified: false,
  bboxSource: "model",
  topX: 0,
  topY: 0,
  bottomX: 100,
  bottomY: 100,
  ...overrides,
});

const initialState = {
  isEditing: false,
  sourceResultKey: null as string | null,
  editedBoxes: [] as InferenceBox[],
  selectedBoxIndex: null as number | null,
  isDrawing: false,
};

describe("generateUserBoxId", () => {
  it("returns a string with user- prefix", () => {
    expect(generateUserBoxId()).toMatch(/^user-\d+-\d+$/);
  });

  it("returns unique IDs on each call", () => {
    const ids = Array.from({ length: 10 }, () => generateUserBoxId());
    expect(new Set(ids).size).toBe(10);
  });
});

describe("useBoxEditStore", () => {
  beforeEach(() => {
    useBoxEditStore.setState(initialState);
  });

  it("has correct initial state", () => {
    const state = useBoxEditStore.getState();
    expect(state.isEditing).toBe(false);
    expect(state.sourceResultKey).toBeNull();
    expect(state.editedBoxes).toEqual([]);
    expect(state.selectedBoxIndex).toBeNull();
    expect(state.isDrawing).toBe(false);
  });

  describe("enterEditMode", () => {
    it("sets isEditing and sourceResultKey", () => {
      useBoxEditStore.getState().enterEditMode("key-1", []);
      const state = useBoxEditStore.getState();
      expect(state.isEditing).toBe(true);
      expect(state.sourceResultKey).toBe("key-1");
    });

    it("deep-clones boxes (no shared references)", () => {
      const boxes = [makeBox({ boxId: "b1" })];
      useBoxEditStore.getState().enterEditMode("key-1", boxes);
      const { editedBoxes } = useBoxEditStore.getState();
      expect(editedBoxes).toEqual(boxes);
      expect(editedBoxes[0]).not.toBe(boxes[0]);
    });

    it("resets selectedBoxIndex and isDrawing", () => {
      useBoxEditStore.setState({ selectedBoxIndex: 2, isDrawing: true });
      useBoxEditStore.getState().enterEditMode("key-1", []);
      expect(useBoxEditStore.getState().selectedBoxIndex).toBeNull();
      expect(useBoxEditStore.getState().isDrawing).toBe(false);
    });
  });

  describe("exitEditMode", () => {
    it("resets all fields to initial values", () => {
      useBoxEditStore.getState().enterEditMode("key-1", [makeBox()]);
      useBoxEditStore.setState({ selectedBoxIndex: 1, isDrawing: true });
      useBoxEditStore.getState().exitEditMode();
      const state = useBoxEditStore.getState();
      expect(state.isEditing).toBe(false);
      expect(state.sourceResultKey).toBeNull();
      expect(state.editedBoxes).toEqual([]);
      expect(state.selectedBoxIndex).toBeNull();
      expect(state.isDrawing).toBe(false);
    });
  });

  describe("updateBox", () => {
    it("replaces the box at the given index", () => {
      const box1 = makeBox({ boxId: "b1" });
      const box2 = makeBox({ boxId: "b2" });
      const updated = makeBox({ boxId: "b1-updated", label: "oat" });
      useBoxEditStore.setState({ editedBoxes: [box1, box2] });
      useBoxEditStore.getState().updateBox(0, updated);
      const { editedBoxes } = useBoxEditStore.getState();
      expect(editedBoxes[0]).toEqual(updated);
      expect(editedBoxes[1]).toEqual(box2);
    });

    it("does not affect other boxes", () => {
      const boxes = [
        makeBox({ boxId: "b1" }),
        makeBox({ boxId: "b2" }),
        makeBox({ boxId: "b3" }),
      ];
      useBoxEditStore.setState({ editedBoxes: boxes });
      useBoxEditStore.getState().updateBox(1, makeBox({ boxId: "new" }));
      expect(useBoxEditStore.getState().editedBoxes[0].boxId).toBe("b1");
      expect(useBoxEditStore.getState().editedBoxes[2].boxId).toBe("b3");
    });
  });

  describe("addBox", () => {
    it("appends the box to editedBoxes", () => {
      useBoxEditStore.setState({ editedBoxes: [makeBox({ boxId: "b1" })] });
      useBoxEditStore.getState().addBox(makeBox({ boxId: "b2" }));
      const { editedBoxes } = useBoxEditStore.getState();
      expect(editedBoxes).toHaveLength(2);
      expect(editedBoxes[1].boxId).toBe("b2");
    });

    it("sets isDrawing to false", () => {
      useBoxEditStore.setState({ isDrawing: true });
      useBoxEditStore.getState().addBox(makeBox());
      expect(useBoxEditStore.getState().isDrawing).toBe(false);
    });
  });

  describe("deleteBox", () => {
    it("removes the box at the given array index", () => {
      const boxes = [
        makeBox({ boxId: "b1" }),
        makeBox({ boxId: "b2" }),
        makeBox({ boxId: "b3" }),
      ];
      useBoxEditStore.setState({ editedBoxes: boxes });
      useBoxEditStore.getState().deleteBox(1);
      const { editedBoxes } = useBoxEditStore.getState();
      expect(editedBoxes).toHaveLength(2);
      expect(editedBoxes.map((b) => b.boxId)).toEqual(["b1", "b3"]);
    });

    it("sets selectedBoxIndex to null when deleting the selected box", () => {
      const boxes = [makeBox({ boxId: "b1" }), makeBox({ boxId: "b2" })];
      useBoxEditStore.setState({ editedBoxes: boxes, selectedBoxIndex: 1 });
      useBoxEditStore.getState().deleteBox(1);
      expect(useBoxEditStore.getState().selectedBoxIndex).toBeNull();
    });

    it("decrements selectedBoxIndex when deleting a box before it", () => {
      const boxes = [
        makeBox({ boxId: "b1" }),
        makeBox({ boxId: "b2" }),
        makeBox({ boxId: "b3" }),
      ];
      useBoxEditStore.setState({ editedBoxes: boxes, selectedBoxIndex: 2 });
      useBoxEditStore.getState().deleteBox(0);
      expect(useBoxEditStore.getState().selectedBoxIndex).toBe(1);
    });

    it("keeps selectedBoxIndex when deleting a box after it", () => {
      const boxes = [
        makeBox({ boxId: "b1" }),
        makeBox({ boxId: "b2" }),
        makeBox({ boxId: "b3" }),
      ];
      useBoxEditStore.setState({ editedBoxes: boxes, selectedBoxIndex: 0 });
      useBoxEditStore.getState().deleteBox(2);
      expect(useBoxEditStore.getState().selectedBoxIndex).toBe(0);
    });

    it("keeps selectedBoxIndex null when no box was selected", () => {
      const boxes = [makeBox({ boxId: "b1" }), makeBox({ boxId: "b2" })];
      useBoxEditStore.setState({ editedBoxes: boxes, selectedBoxIndex: null });
      useBoxEditStore.getState().deleteBox(0);
      expect(useBoxEditStore.getState().selectedBoxIndex).toBeNull();
    });
  });

  describe("setSelectedBoxIndex", () => {
    it("sets selectedBoxIndex to a number", () => {
      useBoxEditStore.getState().setSelectedBoxIndex(3);
      expect(useBoxEditStore.getState().selectedBoxIndex).toBe(3);
    });

    it("accepts null to deselect", () => {
      useBoxEditStore.setState({ selectedBoxIndex: 1 });
      useBoxEditStore.getState().setSelectedBoxIndex(null);
      expect(useBoxEditStore.getState().selectedBoxIndex).toBeNull();
    });
  });

  describe("setIsDrawing", () => {
    it("sets isDrawing to true and clears selectedBoxIndex", () => {
      useBoxEditStore.setState({ isDrawing: false, selectedBoxIndex: 1 });
      useBoxEditStore.getState().setIsDrawing(true);
      expect(useBoxEditStore.getState().isDrawing).toBe(true);
      expect(useBoxEditStore.getState().selectedBoxIndex).toBeNull();
    });

    it("sets isDrawing to false and clears selectedBoxIndex", () => {
      useBoxEditStore.setState({ isDrawing: true, selectedBoxIndex: 2 });
      useBoxEditStore.getState().setIsDrawing(false);
      expect(useBoxEditStore.getState().isDrawing).toBe(false);
      expect(useBoxEditStore.getState().selectedBoxIndex).toBeNull();
    });
  });
});
