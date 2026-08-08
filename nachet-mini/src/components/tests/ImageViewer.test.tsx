import {
  describe,
  it,
  expect,
  beforeAll,
  beforeEach,
  afterEach,
  vi,
} from "vitest";
import { render, cleanup, fireEvent } from "@testing-library/react";
import { page } from "vitest/browser";
import type { InferenceResult, InferenceBox } from "@common/types";
import { useBoxEditStore } from "@stores/useBoxEditStore";
import { useIsPortrait } from "@hooks/useIsPortrait";
import { getUnscaledCoordinates, getScaledBounds } from "@common/imageutils";
import ImageViewer from "../ImageViewer";

vi.mock("@hooks/useIsPortrait", () => ({ useIsPortrait: vi.fn() }));
vi.mock("@stores/useBoxEditStore", () => ({
  useBoxEditStore: vi.fn(),
  generateUserBoxId: vi.fn(() => "user-test-id"),
}));
vi.mock("@common/imageutils", () => ({
  getUnscaledCoordinates: vi.fn(() => ({ imageX: 50, imageY: 50 })),
  getScaledBounds: vi.fn(() => ({
    scaledWidth: 200,
    scaledHeight: 150,
    scaledTopX: 10,
    scaledTopY: 10,
  })),
}));
// Mock InferenceOverlay with a visible element that exposes props as data-attributes
vi.mock("@components/InferenceOverlay", async () => {
  const React = await import("react");
  return {
    default: (props: Record<string, unknown>) =>
      React.createElement(
        "div",
        {
          "data-testid": `inference-overlay-${props.index}`,
          "aria-label": String(props.label ?? ""),
          "data-edit-mode": String(props.editMode ?? false),
          "data-is-classifying": String(props.isClassifying ?? false),
          "data-is-edit-selected": String(props.isEditSelected ?? false),
          "data-is-view-selected": String(props.isViewSelected ?? false),
          "data-canvas-width": String(props.canvasWidth ?? ""),
          "data-canvas-height": String(props.canvasHeight ?? ""),
          "data-min-box-size": String(props.minBoxSize ?? ""),
          "data-has-on-box-update": String(
            typeof props.onBoxUpdate === "function",
          ),
          "data-has-on-box-delete": String(
            typeof props.onBoxDelete === "function",
          ),
          "data-has-on-box-select": String(
            typeof props.onBoxSelect === "function",
          ),
          // Absolute position + explicit size so Playwright considers it visible
          style: {
            position: "absolute",
            left: `${(props.index as number) * 5}px`,
            top: `${(props.index as number) * 5}px`,
            width: "10px",
            height: "10px",
          },
        },
        [
          React.createElement("button", {
            key: "select",
            "data-testid": `overlay-select-${props.index}`,
            onClick: () =>
              typeof props.onBoxSelect === "function" && props.onBoxSelect(3),
          }),
          React.createElement("button", {
            key: "update",
            "data-testid": `overlay-update-${props.index}`,
            onClick: () =>
              typeof props.onBoxUpdate === "function" &&
              props.onBoxUpdate({ boxId: "updated-from-mock" }),
          }),
          React.createElement("button", {
            key: "delete",
            "data-testid": `overlay-delete-${props.index}`,
            onClick: () =>
              typeof props.onBoxDelete === "function" && props.onBoxDelete(7),
          }),
        ],
      ),
  };
});

// Stub ResizeObserver to immediately report 500×400 so containerSize.width > 0
beforeAll(() => {
  vi.stubGlobal(
    "ResizeObserver",
    class MockResizeObserver {
      private cb: ResizeObserverCallback;
      constructor(cb: ResizeObserverCallback) {
        this.cb = cb;
      }
      observe(el: Element) {
        this.cb(
          [
            {
              target: el,
              contentRect: {
                width: 500,
                height: 400,
                top: 0,
                left: 0,
                bottom: 400,
                right: 500,
                x: 0,
                y: 0,
                toJSON: () => ({}),
              } as DOMRectReadOnly,
              borderBoxSize: [],
              contentBoxSize: [],
              devicePixelContentBoxSize: [],
            },
          ],
          this as unknown as ResizeObserver,
        );
      }
      disconnect() {}
      unobserve() {}
    },
  );
});

// ── Store helpers ──────────────────────────────────────────────────────────────

const mockAddBox = vi.fn();
const mockSetIsDrawing = vi.fn();
const mockUpdateBox = vi.fn();
const mockDeleteBox = vi.fn();
const mockSetSelectedBoxIndex = vi.fn();

type StoreOverride = {
  isEditing?: boolean;
  editedBoxes?: InferenceBox[];
  selectedBoxIndex?: number | null;
  isDrawing?: boolean;
};

const setMockStore = (overrides: StoreOverride = {}) => {
  const state = {
    isEditing: false,
    editedBoxes: [] as InferenceBox[],
    selectedBoxIndex: null as number | null,
    isDrawing: false,
    updateBox: mockUpdateBox,
    addBox: mockAddBox,
    deleteBox: mockDeleteBox,
    setSelectedBoxIndex: mockSetSelectedBoxIndex,
    setIsDrawing: mockSetIsDrawing,
    ...overrides,
  };
  vi.mocked(useBoxEditStore).mockImplementation(
    (selector: (s: typeof state) => unknown) => selector(state),
  );
};

// ── Data factories ─────────────────────────────────────────────────────────────

const makeBox = (overrides: Partial<InferenceBox> = {}): InferenceBox => ({
  inferenceId: "inf-1",
  boxId: "box-1",
  classId: "class-1",
  label: "wheat",
  isVerified: false,
  bboxSource: "model",
  topX: 10,
  topY: 10,
  bottomX: 90,
  bottomY: 90,
  ...overrides,
});

const makeResult = (
  boxCount = 2,
  classOverrides?: string[],
): InferenceResult => {
  const classifications =
    classOverrides ??
    Array.from({ length: boxCount }, (_, i) => `Species ${i + 1}`);
  return {
    scores: [],
    classifications,
    boxes: Array.from({ length: boxCount }, (_, i) =>
      makeBox({ boxId: `box-${i}`, inferenceId: `inf-${i}` }),
    ),
    topN: [],
    overlapping: [],
    overlappingIndices: [],
    labelOccurrence: {},
    totalBoxes: boxCount,
    models: [],
    completedAt: "2024-01-01T00:00:00Z",
    isActive: true,
    minBoxSize: 10,
  };
};

// ── Render helper ──────────────────────────────────────────────────────────────

const defaultProps = {
  src: undefined as string | undefined,
  imageDims: [800, 600] as number[],
  result: null as InferenceResult | null,
  selectedBoxId: null as string | null,
  onSelectedBoxIdChange: undefined as
    | ((boxId: string | null) => void)
    | undefined,
};

// Wrap in an explicitly sized div so CSS percentages resolve to real pixels,
// making absolutely-positioned children visible to Playwright.
const renderViewer = (props: Partial<typeof defaultProps> = {}) =>
  render(
    <div style={{ width: "800px", height: "600px" }}>
      <ImageViewer {...defaultProps} {...props} />
    </div>,
  );

// ── Tests ──────────────────────────────────────────────────────────────────────

describe("ImageViewer", () => {
  beforeEach(() => {
    vi.mocked(useIsPortrait).mockReturnValue(false);
    vi.mocked(getScaledBounds).mockClear();
    vi.mocked(getScaledBounds).mockReturnValue({
      scaledWidth: 200,
      scaledHeight: 150,
      scaledTopX: 10,
      scaledTopY: 10,
    });
    vi.mocked(getUnscaledCoordinates).mockClear();
    vi.mocked(getUnscaledCoordinates).mockReturnValue({
      imageX: 50,
      imageY: 50,
    });
    setMockStore();
    mockAddBox.mockClear();
    mockSetIsDrawing.mockClear();
    mockUpdateBox.mockClear();
    mockDeleteBox.mockClear();
    mockSetSelectedBoxIndex.mockClear();
  });

  afterEach(cleanup);

  describe("container", () => {
    it("renders with data-testid 'image-viewer-component'", async () => {
      renderViewer();
      await expect
        .element(page.getByTestId("image-viewer-component"))
        .toBeVisible();
    });
  });

  describe("no image", () => {
    it("shows 'No image loaded' when src is undefined", async () => {
      renderViewer({ src: undefined });
      await expect.element(page.getByText("No image loaded")).toBeVisible();
    });

    it("does not render an img element when src is undefined", async () => {
      renderViewer({ src: undefined });
      expect(await page.getByRole("img").all()).toHaveLength(0);
    });
  });

  describe("with image", () => {
    const SRC = "data:image/png;base64,abc";

    it("renders an img element when src is provided", async () => {
      renderViewer({ src: SRC });
      await expect.element(page.getByRole("img")).toBeVisible();
    });

    it("img has alt text 'Uploaded image'", async () => {
      renderViewer({ src: SRC });
      await expect.element(page.getByAltText("Uploaded image")).toBeVisible();
    });

    it("does not show 'No image loaded' when src is provided", async () => {
      renderViewer({ src: SRC });
      expect(await page.getByText("No image loaded").all()).toHaveLength(0);
    });

    it("rotates the image wrapper in portrait mode", () => {
      vi.mocked(useIsPortrait).mockReturnValue(true);
      const { getByAltText } = renderViewer({ src: SRC });
      const wrapper = getByAltText("Uploaded image").parentElement;
      expect(wrapper).not.toBeNull();
      expect(getComputedStyle(wrapper as HTMLElement).transform).not.toBe(
        "none",
      );
    });
  });

  describe("inference overlays — view mode", () => {
    const SRC = "data:image/png;base64,abc";

    it("renders no overlays when result is null", async () => {
      renderViewer({ src: SRC, result: null });
      await expect
        .element(page.getByTestId("image-viewer-component"))
        .toBeVisible();
      expect(await page.getByTestId(/inference-overlay-\d/).all()).toHaveLength(
        0,
      );
    });

    it("renders no overlays when result has no boxes", async () => {
      renderViewer({ src: SRC, result: makeResult(0) });
      await expect
        .element(page.getByTestId("image-viewer-component"))
        .toBeVisible();
      expect(await page.getByTestId(/inference-overlay-\d/).all()).toHaveLength(
        0,
      );
    });

    it("renders one overlay per box in result", async () => {
      renderViewer({ src: SRC, result: makeResult(3) });
      expect(await page.getByTestId(/inference-overlay-\d/).all()).toHaveLength(
        3,
      );
    });

    it("passes the classification as label to each overlay", async () => {
      renderViewer({ src: SRC, result: makeResult(2) });
      await expect
        .element(page.getByTestId("inference-overlay-0"))
        .toHaveAttribute("aria-label", "Species 1");
      await expect
        .element(page.getByTestId("inference-overlay-1"))
        .toHaveAttribute("aria-label", "Species 2");
    });

    it("passes isClassifying=true when the classification is an empty string", async () => {
      renderViewer({ src: SRC, result: makeResult(1, [""]) });
      await expect
        .element(page.getByTestId("inference-overlay-0"))
        .toHaveAttribute("data-is-classifying", "true");
    });

    it("passes isClassifying=false when the classification is non-empty", async () => {
      renderViewer({ src: SRC, result: makeResult(1) });
      await expect
        .element(page.getByTestId("inference-overlay-0"))
        .toHaveAttribute("data-is-classifying", "false");
    });

    it("passes editMode=false to overlays in view mode", async () => {
      renderViewer({ src: SRC, result: makeResult(1) });
      await expect
        .element(page.getByTestId("inference-overlay-0"))
        .toHaveAttribute("data-edit-mode", "false");
    });

    it("passes canvas dimensions and min box size to overlays", async () => {
      renderViewer({ src: SRC, result: makeResult(1) });
      await expect
        .element(page.getByTestId("inference-overlay-0"))
        .toHaveAttribute("data-canvas-width", "500");
      await expect
        .element(page.getByTestId("inference-overlay-0"))
        .toHaveAttribute("data-canvas-height", "400");
      await expect
        .element(page.getByTestId("inference-overlay-0"))
        .toHaveAttribute("data-min-box-size", "10");
    });

    it("does not pass edit callbacks to overlays in view mode", async () => {
      renderViewer({ src: SRC, result: makeResult(1) });
      await expect
        .element(page.getByTestId("inference-overlay-0"))
        .toHaveAttribute("data-has-on-box-update", "false");
      await expect
        .element(page.getByTestId("inference-overlay-0"))
        .toHaveAttribute("data-has-on-box-delete", "false");
      await expect
        .element(page.getByTestId("inference-overlay-0"))
        .toHaveAttribute("data-has-on-box-select", "false");
    });

    it("selects a result box through its stable box id", () => {
      const onSelectedBoxIdChange = vi.fn();
      const { getByTestId } = renderViewer({
        src: SRC,
        result: makeResult(1),
        onSelectedBoxIdChange,
      });

      fireEvent.click(getByTestId("overlay-select-0"));
      expect(onSelectedBoxIdChange).toHaveBeenCalledWith("box-0");
    });

    it("marks only the matching result box as selected", async () => {
      renderViewer({
        src: SRC,
        result: makeResult(2),
        selectedBoxId: "box-1",
        onSelectedBoxIdChange: vi.fn(),
      });

      await expect
        .element(page.getByTestId("inference-overlay-0"))
        .toHaveAttribute("data-is-view-selected", "false");
      await expect
        .element(page.getByTestId("inference-overlay-1"))
        .toHaveAttribute("data-is-view-selected", "true");
    });
  });

  describe("edit mode overlays", () => {
    const SRC = "data:image/png;base64,abc";

    it("renders editedBoxes instead of result boxes when isEditing", async () => {
      const editedBoxes = [makeBox({ boxId: "e0" }), makeBox({ boxId: "e1" })];
      setMockStore({ isEditing: true, editedBoxes });
      renderViewer({ src: SRC, result: makeResult(5) });
      expect(await page.getByTestId(/inference-overlay-\d/).all()).toHaveLength(
        2,
      );
    });

    it("uses the box label when it is non-empty in edit mode", async () => {
      setMockStore({
        isEditing: true,
        editedBoxes: [makeBox({ label: "rye" })],
      });
      renderViewer({ src: SRC, result: null });
      await expect
        .element(page.getByTestId("inference-overlay-0"))
        .toHaveAttribute("aria-label", "rye");
    });

    it("falls back to 'Box N' label for edit boxes with empty label", async () => {
      setMockStore({ isEditing: true, editedBoxes: [makeBox({ label: "" })] });
      renderViewer({ src: SRC, result: null });
      await expect
        .element(page.getByTestId("inference-overlay-0"))
        .toHaveAttribute("aria-label", "Box 1");
    });

    it("passes editMode=true to overlays in edit mode", async () => {
      setMockStore({ isEditing: true, editedBoxes: [makeBox()] });
      renderViewer({ src: SRC, result: null });
      await expect
        .element(page.getByTestId("inference-overlay-0"))
        .toHaveAttribute("data-edit-mode", "true");
    });

    it("marks the selected box with isEditSelected=true and others false", async () => {
      setMockStore({
        isEditing: true,
        editedBoxes: [makeBox(), makeBox()],
        selectedBoxIndex: 1,
      });
      renderViewer({ src: SRC, result: null });
      await expect
        .element(page.getByTestId("inference-overlay-0"))
        .toHaveAttribute("data-is-edit-selected", "false");
      await expect
        .element(page.getByTestId("inference-overlay-1"))
        .toHaveAttribute("data-is-edit-selected", "true");
    });

    it("passes isClassifying=false to all overlays in edit mode", async () => {
      setMockStore({ isEditing: true, editedBoxes: [makeBox()] });
      renderViewer({ src: SRC, result: null });
      await expect
        .element(page.getByTestId("inference-overlay-0"))
        .toHaveAttribute("data-is-classifying", "false");
    });

    it("passes edit callbacks to overlays in edit mode", async () => {
      setMockStore({ isEditing: true, editedBoxes: [makeBox()] });
      renderViewer({ src: SRC, result: makeResult(1) });
      await expect
        .element(page.getByTestId("inference-overlay-0"))
        .toHaveAttribute("data-has-on-box-update", "true");
      await expect
        .element(page.getByTestId("inference-overlay-0"))
        .toHaveAttribute("data-has-on-box-delete", "true");
      await expect
        .element(page.getByTestId("inference-overlay-0"))
        .toHaveAttribute("data-has-on-box-select", "true");
    });

    it("wires edit callbacks through to the store", () => {
      setMockStore({ isEditing: true, editedBoxes: [makeBox()] });
      const { getByTestId } = renderViewer({ src: SRC, result: null });

      fireEvent.click(getByTestId("overlay-select-0"));
      fireEvent.click(getByTestId("overlay-update-0"));
      fireEvent.click(getByTestId("overlay-delete-0"));

      expect(mockSetSelectedBoxIndex).toHaveBeenCalledWith(3);
      expect(mockUpdateBox).toHaveBeenCalledWith({
        boxId: "updated-from-mock",
      });
      expect(mockDeleteBox).toHaveBeenCalledWith(7);
    });
  });

  describe("draw overlay", () => {
    const SRC = "data:image/png;base64,abc";

    it("shows draw overlay when isEditing and isDrawing", async () => {
      setMockStore({ isEditing: true, isDrawing: true });
      renderViewer({ src: SRC });
      await expect.element(page.getByTestId("draw-overlay")).toBeVisible();
    });

    it("does not show draw overlay when isEditing but not isDrawing", async () => {
      setMockStore({ isEditing: true, isDrawing: false });
      renderViewer({ src: SRC });
      await expect
        .element(page.getByTestId("image-viewer-component"))
        .toBeVisible();
      expect(await page.getByTestId("draw-overlay").all()).toHaveLength(0);
    });

    it("does not show draw overlay in view mode even when drawing is enabled", async () => {
      setMockStore({ isEditing: false, isDrawing: true });
      renderViewer({ src: SRC });
      await expect
        .element(page.getByTestId("image-viewer-component"))
        .toBeVisible();
      expect(await page.getByTestId("draw-overlay").all()).toHaveLength(0);
    });
  });

  describe("draw interaction", () => {
    const SRC = "data:image/png;base64,abc";

    it("shows draw preview rectangle after mousedown on draw overlay", async () => {
      setMockStore({ isEditing: true, isDrawing: true });
      const { getByTestId } = renderViewer({ src: SRC });
      await expect.element(page.getByTestId("draw-overlay")).toBeVisible();
      fireEvent.mouseDown(getByTestId("draw-overlay"));
      await expect.element(page.getByTestId("draw-preview")).toBeVisible();
    });

    it("translates client coordinates relative to the container before drawing", () => {
      setMockStore({ isEditing: true, isDrawing: true });
      const { getByTestId } = renderViewer({ src: SRC, imageDims: [800, 600] });
      const container = getByTestId("image-viewer-component");
      vi.spyOn(container, "getBoundingClientRect").mockReturnValue({
        width: 500,
        height: 400,
        top: 40,
        left: 100,
        bottom: 440,
        right: 600,
        x: 100,
        y: 40,
        toJSON: () => ({}),
      } as DOMRect);

      fireEvent.mouseDown(getByTestId("draw-overlay"), {
        clientX: 160,
        clientY: 130,
      });

      expect(getUnscaledCoordinates).toHaveBeenCalledWith(
        500,
        400,
        800,
        600,
        60,
        90,
      );
    });

    it("updates the draw preview using normalized bounds during mousemove", async () => {
      vi.mocked(getUnscaledCoordinates)
        .mockReturnValueOnce({ imageX: 80, imageY: 120 })
        .mockReturnValueOnce({ imageX: 20, imageY: 40 });

      setMockStore({ isEditing: true, isDrawing: true });
      const { getByTestId } = renderViewer({ src: SRC, imageDims: [800, 600] });

      fireEvent.mouseDown(getByTestId("draw-overlay"));
      await new Promise<void>((r) => requestAnimationFrame(() => r()));
      window.dispatchEvent(
        new MouseEvent("mousemove", {
          clientX: 250,
          clientY: 250,
          bubbles: true,
        }),
      );
      await new Promise<void>((r) => requestAnimationFrame(() => r()));

      expect(getScaledBounds).toHaveBeenLastCalledWith(500, 400, 800, 600, {
        topX: 20,
        topY: 40,
        bottomX: 80,
        bottomY: 120,
      });
    });

    it("calls addBox with correct coordinates when mouseup produces a sufficiently large box", async () => {
      // mousedown returns {10,10}, mouseup returns {200,200} → 190×190 px ≥ MIN_DRAW_PX(20)
      vi.mocked(getUnscaledCoordinates)
        .mockReturnValueOnce({ imageX: 10, imageY: 10 })
        .mockReturnValue({ imageX: 200, imageY: 200 });

      setMockStore({ isEditing: true, isDrawing: true });
      const { getByTestId } = renderViewer({ src: SRC, imageDims: [800, 600] });

      fireEvent.mouseDown(getByTestId("draw-overlay"));
      await new Promise<void>((r) => requestAnimationFrame(() => r()));
      window.dispatchEvent(
        new MouseEvent("mouseup", {
          clientX: 300,
          clientY: 300,
          bubbles: true,
        }),
      );
      await new Promise<void>((r) => requestAnimationFrame(() => r()));

      expect(mockAddBox).toHaveBeenCalledOnce();
      expect(mockAddBox).toHaveBeenCalledWith(
        expect.objectContaining({
          topX: 10,
          topY: 10,
          bottomX: 200,
          bottomY: 200,
          boxId: "user-test-id",
          classId: "",
          label: "",
          isVerified: false,
          inferenceId: "user-drawn",
          bboxSource: "user",
        }),
      );
    });

    it("normalizes reverse drag coordinates before adding a box", async () => {
      vi.mocked(getUnscaledCoordinates)
        .mockReturnValueOnce({ imageX: 220, imageY: 180 })
        .mockReturnValue({ imageX: 40, imageY: 20 });

      setMockStore({ isEditing: true, isDrawing: true });
      const { getByTestId } = renderViewer({ src: SRC, imageDims: [800, 600] });

      fireEvent.mouseDown(getByTestId("draw-overlay"));
      await new Promise<void>((r) => requestAnimationFrame(() => r()));
      window.dispatchEvent(
        new MouseEvent("mouseup", {
          clientX: 20,
          clientY: 20,
          bubbles: true,
        }),
      );
      await new Promise<void>((r) => requestAnimationFrame(() => r()));

      expect(mockAddBox).toHaveBeenCalledWith(
        expect.objectContaining({
          topX: 40,
          topY: 20,
          bottomX: 220,
          bottomY: 180,
        }),
      );
    });

    it("clamps drawn boxes to the image bounds before adding a box", async () => {
      vi.mocked(getUnscaledCoordinates)
        .mockReturnValueOnce({ imageX: -10, imageY: -5 })
        .mockReturnValue({ imageX: 900, imageY: 700 });

      setMockStore({ isEditing: true, isDrawing: true });
      const { getByTestId } = renderViewer({ src: SRC, imageDims: [800, 600] });

      fireEvent.mouseDown(getByTestId("draw-overlay"));
      await new Promise<void>((r) => requestAnimationFrame(() => r()));
      window.dispatchEvent(
        new MouseEvent("mouseup", {
          clientX: 900,
          clientY: 700,
          bubbles: true,
        }),
      );
      await new Promise<void>((r) => requestAnimationFrame(() => r()));

      expect(mockAddBox).toHaveBeenCalledWith(
        expect.objectContaining({
          topX: 0,
          topY: 0,
          bottomX: 800,
          bottomY: 600,
        }),
      );
    });

    it("does not call addBox when the drawn box is smaller than MIN_DRAW_PX (20px)", async () => {
      vi.mocked(getUnscaledCoordinates)
        .mockReturnValueOnce({ imageX: 10, imageY: 10 })
        .mockReturnValue({ imageX: 14, imageY: 14 }); // 4×4 < 20

      setMockStore({ isEditing: true, isDrawing: true });
      const { getByTestId } = renderViewer({ src: SRC });

      fireEvent.mouseDown(getByTestId("draw-overlay"));
      await new Promise<void>((r) => requestAnimationFrame(() => r()));
      window.dispatchEvent(
        new MouseEvent("mouseup", { clientX: 20, clientY: 20, bubbles: true }),
      );
      await new Promise<void>((r) => requestAnimationFrame(() => r()));

      expect(mockAddBox).not.toHaveBeenCalled();
    });

    it("calls setIsDrawing(false) after mouseup", async () => {
      vi.mocked(getUnscaledCoordinates)
        .mockReturnValueOnce({ imageX: 10, imageY: 10 })
        .mockReturnValue({ imageX: 200, imageY: 200 });

      setMockStore({ isEditing: true, isDrawing: true });
      const { getByTestId } = renderViewer({ src: SRC });

      fireEvent.mouseDown(getByTestId("draw-overlay"));
      await new Promise<void>((r) => requestAnimationFrame(() => r()));
      window.dispatchEvent(
        new MouseEvent("mouseup", {
          clientX: 300,
          clientY: 300,
          bubbles: true,
        }),
      );
      await new Promise<void>((r) => requestAnimationFrame(() => r()));

      expect(mockSetIsDrawing).toHaveBeenCalledWith(false);
    });

    it("hides the draw preview after mouseup resets draw state", async () => {
      vi.mocked(getUnscaledCoordinates)
        .mockReturnValueOnce({ imageX: 10, imageY: 10 })
        .mockReturnValue({ imageX: 200, imageY: 200 });

      setMockStore({ isEditing: true, isDrawing: true });
      const { getByTestId } = renderViewer({ src: SRC });

      fireEvent.mouseDown(getByTestId("draw-overlay"));
      await expect.element(page.getByTestId("draw-preview")).toBeVisible();

      await new Promise<void>((r) => requestAnimationFrame(() => r()));
      window.dispatchEvent(
        new MouseEvent("mouseup", {
          clientX: 300,
          clientY: 300,
          bubbles: true,
        }),
      );
      await new Promise<void>((r) => requestAnimationFrame(() => r()));

      // drawStart/drawCurrent are reset to null, so the preview div is removed
      expect(await page.getByTestId("draw-preview").all()).toHaveLength(0);
    });
  });
});
