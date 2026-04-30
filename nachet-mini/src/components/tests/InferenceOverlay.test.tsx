import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, cleanup, fireEvent } from "@testing-library/react";
import { page } from "vitest/browser";
import type { InferenceBox } from "@common/types";
import { useIsPortrait } from "@hooks/useIsPortrait";
import { getScaledBounds, getUnscaledCoordinates } from "@common/imageutils";
import InferenceOverlay from "../InferenceOverlay";

vi.mock("@hooks/useIsPortrait", () => ({ useIsPortrait: vi.fn() }));
vi.mock("@common/imageutils", () => ({
  getScaledBounds: vi.fn(),
  getUnscaledCoordinates: vi.fn(),
}));

const makeBox = (overrides: Partial<InferenceBox> = {}): InferenceBox => ({
  inferenceId: "inf-1",
  boxId: "box-1",
  classId: "class-1",
  label: "wheat",
  isVerified: false,
  bboxSource: "model",
  topX: 100,
  topY: 100,
  bottomX: 300,
  bottomY: 300,
  ...overrides,
});

const defaultProps = {
  index: 0,
  imageWidth: 800,
  imageHeight: 600,
  box: makeBox(),
  canvasWidth: 500,
  canvasHeight: 400,
  label: "wheat",
  visible: true,
  totalBoxes: 1,
  isClassifying: false,
  minBoxSize: 10,
  editMode: false as boolean | undefined,
  isEditSelected: false as boolean | undefined,
};

type Callbacks = {
  onBoxUpdate?: ReturnType<typeof vi.fn>;
  onBoxDelete?: ReturnType<typeof vi.fn>;
  onBoxSelect?: ReturnType<typeof vi.fn>;
};

const renderOverlay = (
  props: Partial<typeof defaultProps> = {},
  callbacks: Callbacks = {},
) => {
  const merged = { ...defaultProps, ...props };
  return render(
    <div
      data-testid="image-viewer-component"
      style={{ width: "500px", height: "400px", position: "relative" }}
    >
      <InferenceOverlay {...merged} {...callbacks} />
    </div>,
  );
};

const getHandleEls = (container: HTMLElement) =>
  Array.from(
    container.querySelectorAll<HTMLElement>('[data-testid^="resize-handle-"]'),
  );

const raf = () =>
  new Promise<void>((resolve) => requestAnimationFrame(resolve));

describe("InferenceOverlay", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.mocked(useIsPortrait).mockReturnValue(false);
    vi.mocked(getScaledBounds).mockReturnValue({
      scaledWidth: 200,
      scaledHeight: 150,
      scaledTopX: 10,
      scaledTopY: 10,
    });
    vi.mocked(getUnscaledCoordinates).mockReturnValue({
      imageX: 50,
      imageY: 50,
    });
  });

  afterEach(cleanup);

  describe("rendering", () => {
    it("renders the overlay with the label as its aria-label", () => {
      const { getByLabelText } = renderOverlay({ label: "canary grass" });
      expect(getByLabelText("canary grass")).toBeInTheDocument();
    });

    it("renders a stable test id for the overlay root", () => {
      const { getByTestId } = renderOverlay({ index: 4 });
      expect(getByTestId("inference-overlay-4")).toBeInTheDocument();
    });

    it("renders box number as index + 1", () => {
      const { getByTestId } = renderOverlay({ index: 4 });
      expect(getByTestId("inference-overlay-label-4")).toHaveTextContent("5");
    });

    it("uses scaled bounds from getScaledBounds", () => {
      const box = makeBox({ topX: 10, topY: 20, bottomX: 210, bottomY: 170 });
      const { getByTestId } = renderOverlay({
        box,
        canvasWidth: 640,
        canvasHeight: 480,
        imageWidth: 1200,
        imageHeight: 900,
      });

      expect(getScaledBounds).toHaveBeenCalledWith(640, 480, 1200, 900, box);

      const overlay = getByTestId("inference-overlay-0");
      const computed = window.getComputedStyle(overlay);
      expect(computed.left).toBe("10px");
      expect(computed.top).toBe("10px");
      expect(computed.minWidth).toBe("200px");
      expect(computed.maxWidth).toBe("200px");
      expect(computed.minHeight).toBe("150px");
      expect(computed.maxHeight).toBe("150px");
    });

    it("shows a progress spinner when classifying", async () => {
      renderOverlay({ isClassifying: true });
      await expect.element(page.getByRole("progressbar")).toBeVisible();
    });

    it("does not show a progress spinner when not classifying", async () => {
      renderOverlay({ isClassifying: false });
      expect(await page.getByRole("progressbar").all()).toHaveLength(0);
    });

    it("hides the overlay when visible=false", () => {
      const { getByTestId } = renderOverlay({ visible: false });
      const overlay = getByTestId("inference-overlay-0");
      expect(window.getComputedStyle(overlay).display).toBe("none");
    });

    it("keeps the overlay visible when visible=true", () => {
      const { getByTestId } = renderOverlay({ visible: true });
      const overlay = getByTestId("inference-overlay-0");
      expect(window.getComputedStyle(overlay).display).toBe("block");
    });
  });

  describe("view mode", () => {
    it("renders the layers button and omits edit controls", async () => {
      const { container } = renderOverlay({ editMode: false });

      await expect
        .element(page.getByRole("button", { name: "layers" }))
        .toBeInTheDocument();
      expect(
        await page.getByRole("button", { name: "delete box" }).all(),
      ).toHaveLength(0);
      expect(getHandleEls(container)).toHaveLength(0);
    });

    it("does not call onBoxSelect on mouseDown", () => {
      const onBoxSelect = vi.fn();
      const { getByTestId } = renderOverlay(
        { editMode: false },
        { onBoxSelect },
      );

      fireEvent.mouseDown(getByTestId("inference-overlay-0"));
      expect(onBoxSelect).not.toHaveBeenCalled();
    });

    it("opens the layers menu with both actions", async () => {
      renderOverlay({ editMode: false });

      await page.getByRole("button", { name: "layers" }).click();
      await expect.element(page.getByRole("menu")).toBeVisible();
      await expect
        .element(page.getByTestId("layers-menu-forward"))
        .toBeVisible();
      await expect
        .element(page.getByTestId("layers-menu-backward"))
        .toBeVisible();
    });

    it("shows the z-index badge only while the layers menu is open", async () => {
      const { getByTestId } = renderOverlay({ editMode: false, index: 2 });
      const badge = getByTestId("z-index-badge-2");

      expect(window.getComputedStyle(badge).display).toBe("none");

      await page.getByRole("button", { name: "layers" }).click();
      await expect.element(page.getByTestId("z-index-badge-2")).toBeVisible();
      expect(badge).toHaveTextContent("2");
    });

    it("moves the box forward and closes the layers menu", async () => {
      const { getByTestId } = renderOverlay({ editMode: false, index: 0 });

      await page.getByRole("button", { name: "layers" }).click();
      await page.getByTestId("layers-menu-forward").click();
      expect(await page.getByRole("menu").all()).toHaveLength(0);

      await page.getByRole("button", { name: "layers" }).click();
      await expect.element(page.getByTestId("z-index-badge-0")).toBeVisible();
      expect(getByTestId("z-index-badge-0")).toHaveTextContent("1");
    });

    it("moves the box backward but never below zero", async () => {
      const { getByTestId } = renderOverlay({ editMode: false, index: 0 });

      await page.getByRole("button", { name: "layers" }).click();
      await page.getByTestId("layers-menu-backward").click();
      expect(await page.getByRole("menu").all()).toHaveLength(0);

      await page.getByRole("button", { name: "layers" }).click();
      await expect.element(page.getByTestId("z-index-badge-0")).toBeVisible();
      expect(getByTestId("z-index-badge-0")).toHaveTextContent("0");
    });
  });

  describe("edit mode", () => {
    it("renders delete and resize controls and omits layers", async () => {
      const { container } = renderOverlay({ editMode: true });

      await expect
        .element(page.getByRole("button", { name: "delete box" }))
        .toBeVisible();
      expect(
        await page.getByRole("button", { name: "layers" }).all(),
      ).toHaveLength(0);
      expect(getHandleEls(container)).toHaveLength(8);
    });

    it("calls onBoxDelete with the correct index", async () => {
      const onBoxDelete = vi.fn();
      renderOverlay({ editMode: true, index: 3 }, { onBoxDelete });

      await page.getByRole("button", { name: "delete box" }).click();
      expect(onBoxDelete).toHaveBeenCalledWith(3);
    });

    it("calls onBoxSelect when the overlay is grabbed", () => {
      const onBoxSelect = vi.fn();
      const { getByTestId } = renderOverlay(
        { editMode: true, index: 2 },
        { onBoxSelect },
      );

      fireEvent.mouseDown(getByTestId("inference-overlay-2"));
      expect(onBoxSelect).toHaveBeenCalledWith(2);
    });

    it("calls onBoxSelect when a resize handle is grabbed", () => {
      const onBoxSelect = vi.fn();
      const { getByTestId } = renderOverlay(
        { editMode: true, index: 5 },
        { onBoxSelect },
      );

      fireEvent.mouseDown(getByTestId("resize-handle-nw"));
      expect(onBoxSelect).toHaveBeenCalledWith(5);
    });

    it("elevates z-index and uses selected styling when isEditSelected=true", () => {
      const { getByTestId } = renderOverlay({
        editMode: true,
        index: 2,
        isEditSelected: true,
      });

      const overlay = getByTestId("inference-overlay-2");
      const computed = window.getComputedStyle(overlay);
      expect(computed.zIndex).toBe("102");
      expect(computed.borderTopColor).toBe("rgb(21, 101, 192)");
    });
  });

  describe("coordinate conversion", () => {
    it("passes display coordinates through getUnscaledCoordinates", () => {
      const { getByTestId, getByLabelText } = renderOverlay({ editMode: true });
      const container = getByTestId("image-viewer-component");

      vi.spyOn(container, "getBoundingClientRect").mockReturnValue({
        x: 25,
        y: 40,
        top: 40,
        left: 25,
        bottom: 440,
        right: 525,
        width: 500,
        height: 400,
        toJSON: () => ({}),
      } as DOMRect);

      fireEvent.mouseDown(getByLabelText("wheat"), {
        clientX: 125,
        clientY: 150,
      });

      expect(getUnscaledCoordinates).toHaveBeenCalledWith(
        500,
        400,
        800,
        600,
        100,
        110,
      );
    });
  });

  describe("drag interaction", () => {
    it("calls onBoxUpdate with translated coordinates during mousemove", async () => {
      const onBoxUpdate = vi.fn();
      vi.mocked(getUnscaledCoordinates)
        .mockReturnValueOnce({ imageX: 100, imageY: 100 })
        .mockReturnValue({ imageX: 150, imageY: 160 });

      const box = makeBox({ topX: 100, topY: 100, bottomX: 300, bottomY: 300 });
      const { getByTestId } = renderOverlay(
        { editMode: true, box },
        { onBoxUpdate },
      );

      fireEvent.mouseDown(getByTestId("inference-overlay-0"));
      await raf();
      window.dispatchEvent(
        new MouseEvent("mousemove", {
          clientX: 200,
          clientY: 200,
          bubbles: true,
        }),
      );
      await raf();

      expect(onBoxUpdate).toHaveBeenCalledWith(
        0,
        expect.objectContaining({
          topX: 150,
          topY: 160,
          bottomX: 350,
          bottomY: 360,
        }),
      );
    });

    it("preserves the box dimensions while dragging", async () => {
      const onBoxUpdate = vi.fn();
      vi.mocked(getUnscaledCoordinates)
        .mockReturnValueOnce({ imageX: 100, imageY: 100 })
        .mockReturnValue({ imageX: 130, imageY: 120 });

      const box = makeBox({ topX: 100, topY: 100, bottomX: 300, bottomY: 250 });
      const { getByTestId } = renderOverlay(
        { editMode: true, box },
        { onBoxUpdate },
      );

      fireEvent.mouseDown(getByTestId("inference-overlay-0"));
      await raf();
      window.dispatchEvent(
        new MouseEvent("mousemove", {
          clientX: 200,
          clientY: 200,
          bubbles: true,
        }),
      );
      await raf();

      const updated = onBoxUpdate.mock.calls[0][1] as InferenceBox;
      expect(updated.bottomX - updated.topX).toBe(200);
      expect(updated.bottomY - updated.topY).toBe(150);
    });

    it("clamps the dragged box within image boundaries", async () => {
      const onBoxUpdate = vi.fn();
      vi.mocked(getUnscaledCoordinates)
        .mockReturnValueOnce({ imageX: 100, imageY: 100 })
        .mockReturnValue({ imageX: 900, imageY: 800 });

      const box = makeBox({ topX: 100, topY: 100, bottomX: 300, bottomY: 300 });
      const { getByTestId } = renderOverlay(
        { editMode: true, box, imageWidth: 800, imageHeight: 600 },
        { onBoxUpdate },
      );

      fireEvent.mouseDown(getByTestId("inference-overlay-0"));
      await raf();
      window.dispatchEvent(
        new MouseEvent("mousemove", {
          clientX: 900,
          clientY: 800,
          bubbles: true,
        }),
      );
      await raf();

      const updated = onBoxUpdate.mock.calls[0][1] as InferenceBox;
      expect(updated.topX).toBe(600);
      expect(updated.topY).toBe(400);
      expect(updated.bottomX).toBe(800);
      expect(updated.bottomY).toBe(600);
    });

    it("stops updating after mouseUp", async () => {
      const onBoxUpdate = vi.fn();
      vi.mocked(getUnscaledCoordinates).mockReturnValue({
        imageX: 150,
        imageY: 160,
      });

      const { getByTestId } = renderOverlay(
        { editMode: true },
        { onBoxUpdate },
      );

      fireEvent.mouseDown(getByTestId("inference-overlay-0"));
      await raf();
      window.dispatchEvent(new MouseEvent("mouseup", { bubbles: true }));
      await raf();

      onBoxUpdate.mockClear();
      window.dispatchEvent(
        new MouseEvent("mousemove", {
          clientX: 300,
          clientY: 300,
          bubbles: true,
        }),
      );
      await raf();

      expect(onBoxUpdate).not.toHaveBeenCalled();
    });
  });

  describe("resize interaction", () => {
    it("calls onBoxUpdate when the south-east handle is dragged", async () => {
      const onBoxUpdate = vi.fn();
      vi.mocked(getUnscaledCoordinates)
        .mockReturnValueOnce({ imageX: 300, imageY: 300 })
        .mockReturnValue({ imageX: 350, imageY: 350 });

      const { getByTestId } = renderOverlay(
        { editMode: true },
        { onBoxUpdate },
      );

      fireEvent.mouseDown(getByTestId("resize-handle-se"));
      await raf();
      window.dispatchEvent(
        new MouseEvent("mousemove", {
          clientX: 400,
          clientY: 400,
          bubbles: true,
        }),
      );
      await raf();

      expect(onBoxUpdate).toHaveBeenCalledWith(
        0,
        expect.objectContaining({
          topX: 100,
          topY: 100,
          bottomX: 350,
          bottomY: 350,
        }),
      );
    });

    it("enforces the minimum width when resizing the east edge", async () => {
      const onBoxUpdate = vi.fn();
      vi.mocked(getUnscaledCoordinates)
        .mockReturnValueOnce({ imageX: 300, imageY: 200 })
        .mockReturnValue({ imageX: 101, imageY: 200 });

      const box = makeBox({ topX: 100, topY: 100, bottomX: 300, bottomY: 300 });
      const { getByTestId } = renderOverlay(
        { editMode: true, box },
        { onBoxUpdate },
      );

      fireEvent.mouseDown(getByTestId("resize-handle-e"));
      await raf();
      window.dispatchEvent(
        new MouseEvent("mousemove", {
          clientX: 102,
          clientY: 200,
          bubbles: true,
        }),
      );
      await raf();

      const updated = onBoxUpdate.mock.calls[0][1] as InferenceBox;
      expect(updated.topX).toBe(100);
      expect(updated.bottomX).toBe(120);
    });

    it("enforces the minimum height when resizing the north edge", async () => {
      const onBoxUpdate = vi.fn();
      vi.mocked(getUnscaledCoordinates)
        .mockReturnValueOnce({ imageX: 200, imageY: 100 })
        .mockReturnValue({ imageX: 200, imageY: 299 });

      const box = makeBox({ topX: 100, topY: 100, bottomX: 300, bottomY: 300 });
      const { getByTestId } = renderOverlay(
        { editMode: true, box },
        { onBoxUpdate },
      );

      fireEvent.mouseDown(getByTestId("resize-handle-n"));
      await raf();
      window.dispatchEvent(
        new MouseEvent("mousemove", {
          clientX: 200,
          clientY: 300,
          bubbles: true,
        }),
      );
      await raf();

      const updated = onBoxUpdate.mock.calls[0][1] as InferenceBox;
      expect(updated.topY).toBe(280);
      expect(updated.bottomY).toBe(300);
    });

    it("clamps resized boxes within image bounds", async () => {
      const onBoxUpdate = vi.fn();
      vi.mocked(getUnscaledCoordinates)
        .mockReturnValueOnce({ imageX: 300, imageY: 300 })
        .mockReturnValue({ imageX: 1000, imageY: 1000 });

      const { getByTestId } = renderOverlay(
        { editMode: true, imageWidth: 800, imageHeight: 600 },
        { onBoxUpdate },
      );

      fireEvent.mouseDown(getByTestId("resize-handle-se"));
      await raf();
      window.dispatchEvent(
        new MouseEvent("mousemove", {
          clientX: 1000,
          clientY: 1000,
          bubbles: true,
        }),
      );
      await raf();

      const updated = onBoxUpdate.mock.calls[0][1] as InferenceBox;
      expect(updated.bottomX).toBe(800);
      expect(updated.bottomY).toBe(600);
    });

    it("stops resizing after mouseUp", async () => {
      const onBoxUpdate = vi.fn();
      vi.mocked(getUnscaledCoordinates).mockReturnValue({
        imageX: 350,
        imageY: 350,
      });

      const { getByTestId } = renderOverlay(
        { editMode: true },
        { onBoxUpdate },
      );

      fireEvent.mouseDown(getByTestId("resize-handle-se"));
      await raf();
      window.dispatchEvent(new MouseEvent("mouseup", { bubbles: true }));
      await raf();

      onBoxUpdate.mockClear();
      window.dispatchEvent(
        new MouseEvent("mousemove", {
          clientX: 500,
          clientY: 500,
          bubbles: true,
        }),
      );
      await raf();

      expect(onBoxUpdate).not.toHaveBeenCalled();
    });
  });

  describe("small box styling", () => {
    it("uses the small-box border color when the box is below minBoxSize", () => {
      const smallBox = makeBox({
        topX: 100,
        topY: 100,
        bottomX: 105,
        bottomY: 105,
      });
      const { getByTestId } = renderOverlay({
        box: smallBox,
        minBoxSize: 20,
      });

      const overlay = getByTestId("inference-overlay-0");
      expect(window.getComputedStyle(overlay).borderTopColor).toBe(
        "rgba(255, 0, 0, 0.7)",
      );
    });

    it("uses the normal border color at the minBoxSize threshold", () => {
      const thresholdBox = makeBox({
        topX: 100,
        topY: 100,
        bottomX: 120,
        bottomY: 110,
      });
      const { getByTestId } = renderOverlay({
        box: thresholdBox,
        minBoxSize: 20,
      });

      const overlay = getByTestId("inference-overlay-0");
      expect(window.getComputedStyle(overlay).borderTopColor).toBe(
        "rgba(128, 0, 128, 0.7)",
      );
    });
  });

  describe("portrait mode", () => {
    it("rotates the label in portrait orientation", () => {
      vi.mocked(useIsPortrait).mockReturnValue(true);
      const { getByTestId } = renderOverlay({ index: 0 });

      const labelEl = getByTestId("inference-overlay-label-0");
      expect(window.getComputedStyle(labelEl).transform).not.toBe("none");
    });

    it("does not rotate the label in landscape orientation", () => {
      vi.mocked(useIsPortrait).mockReturnValue(false);
      const { getByTestId } = renderOverlay({ index: 0 });

      const labelEl = getByTestId("inference-overlay-label-0");
      expect(window.getComputedStyle(labelEl).transform).toBe("none");
    });
  });

  describe("label position", () => {
    it("places the label above the box when topY >= 40", () => {
      const box = makeBox({ topY: 100 });
      const { getByTestId } = renderOverlay({ box, index: 0 });

      const labelEl = getByTestId("inference-overlay-label-0");
      const computed = window.getComputedStyle(labelEl);
      expect(parseFloat(computed.top)).toBeLessThan(0);
    });

    it("keeps the label above the box at the topY=40 boundary", () => {
      const box = makeBox({ topY: 40 });
      const { getByTestId } = renderOverlay({ box, index: 0 });

      const labelEl = getByTestId("inference-overlay-label-0");
      const computed = window.getComputedStyle(labelEl);
      expect(parseFloat(computed.top)).toBeLessThan(0);
    });

    it("places the label below the box when topY < 40", () => {
      const box = makeBox({ topY: 10 });
      const { getByTestId } = renderOverlay({ box, index: 0 });

      const labelEl = getByTestId("inference-overlay-label-0");
      const computed = window.getComputedStyle(labelEl);
      expect(parseFloat(computed.bottom)).toBeLessThan(0);
    });
  });
});
