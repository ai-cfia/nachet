import { cleanup, render, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { I18nextProvider } from "react-i18next";
import { page } from "vitest/browser";
import type { InferenceBox } from "@common/types";
import { useInferenceStore } from "@stores/useInferenceStore";
import i18n from "../../i18n";
import enMain from "../../locales/en/main";
import SeedInspector from "../SeedInspector";

const box: InferenceBox = {
  inferenceId: "test",
  boxId: "seed-1",
  classId: "Avena fatua",
  label: "Avena fatua",
  isVerified: false,
  bboxSource: "model",
  topX: 2,
  topY: 0,
  bottomX: 4,
  bottomY: 4,
};

const taxonomy = {
  families: [
    { label: "Poaceae", score: 0.8 },
    { label: "Fabaceae", score: 0.15 },
  ],
  genera: [
    { label: "Avena", score: 0.8 },
    { label: "Vicia", score: 0.15 },
  ],
  candidates: [
    {
      label: "Avena fatua",
      family: { label: "Poaceae", score: 0.8 },
      genus: { label: "Avena", score: 0.8 },
    },
    {
      label: "Vicia cracca",
      family: { label: "Fabaceae", score: 0.15 },
      genus: { label: "Vicia", score: 0.15 },
    },
  ],
};

const topResults = [
  { label: "Avena fatua", score: 0.8 },
  { label: "Vicia cracca", score: 0.15 },
];

const makeSourceImage = (): string => {
  const source = document.createElement("canvas");
  source.width = 4;
  source.height = 4;
  const context = source.getContext("2d");
  if (!context) throw new Error("Canvas context unavailable");
  context.fillStyle = "rgb(255, 0, 0)";
  context.fillRect(0, 0, 2, 4);
  context.fillStyle = "rgb(0, 255, 0)";
  context.fillRect(2, 0, 2, 4);
  return source.toDataURL("image/png");
};

const InspectorHarness = ({ withCam = true }: { withCam?: boolean }) => {
  return (
    <SeedInspector
      imageSrc={makeSourceImage()}
      imageDims={[4, 4]}
      box={box}
      taxonomy={taxonomy}
      topResults={topResults}
      cam={
        withCam
          ? {
              grid: 2,
              classes: [
                {
                  classIndex: 0,
                  label: "Avena fatua",
                  score: 0.8,
                  heatmap: [1, 1, 1, 1],
                },
                {
                  classIndex: 1,
                  label: "Vicia cracca",
                  score: 0.15,
                  heatmap: [0, 0, 0, 0],
                },
              ],
            }
          : undefined
      }
    />
  );
};

const renderInspector = (withCam = true) =>
  render(
    <I18nextProvider i18n={i18n}>
      <InspectorHarness withCam={withCam} />
    </I18nextProvider>,
  );

describe("SeedInspector", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en");
    useInferenceStore.setState({ camRank: new Map() });
  });

  afterEach(cleanup);

  it("draws the exact selected crop from the source image", async () => {
    const { getByTestId } = renderInspector();
    const canvas = getByTestId("seed-crop-canvas") as HTMLCanvasElement;

    expect(canvas.width).toBe(120);
    expect(canvas.height).toBe(240);
    await waitFor(() => {
      const pixel = canvas.getContext("2d")?.getImageData(60, 120, 1, 1).data;
      expect(pixel?.[1]).toBeGreaterThan(200);
      expect(pixel?.[0]).toBeLessThan(20);
    });
  });

  it("keeps taxonomy secondary until its details are requested", async () => {
    renderInspector();

    await expect.element(page.getByText(/Poaceae · 80.00%/)).toBeVisible();
    await expect.element(page.getByText("Vicia cracca")).toBeVisible();
    expect(
      await page.getByText("Fabaceae", { exact: true }).all(),
    ).toHaveLength(0);

    await page
      .getByRole("button", { name: enMain.resultsTable.showTaxonomyDetails })
      .click();
    await expect
      .element(page.getByText("Fabaceae", { exact: true }))
      .toBeVisible();
    await expect
      .element(page.getByText("Vicia", { exact: true }))
      .toBeVisible();
  });

  it("uses the eye control to show and hide model focus in place", async () => {
    const { getByTestId } = renderInspector();
    const cropCanvas = getByTestId("seed-crop-canvas") as HTMLCanvasElement;

    await waitFor(() => {
      const pixel = cropCanvas
        .getContext("2d")
        ?.getImageData(60, 120, 1, 1).data;
      expect(pixel?.[1]).toBeGreaterThan(200);
    });
    const cropPixel = cropCanvas
      .getContext("2d")
      ?.getImageData(60, 120, 1, 1).data;

    const initialWidth = cropCanvas.style.width;
    const initialHeight = cropCanvas.style.height;
    const showLabel = enMain.resultsTable.showModelFocus.replace(
      "{{species}}",
      "Avena fatua",
    );
    const hideLabel = enMain.resultsTable.hideModelFocus.replace(
      "{{species}}",
      "Avena fatua",
    );
    const focusButton = page.getByRole("button", { name: showLabel });
    await expect.element(focusButton).toHaveAttribute("aria-pressed", "false");
    await focusButton.click();
    const hideButton = page.getByRole("button", { name: hideLabel });
    await expect.element(hideButton).toHaveAttribute("aria-pressed", "true");
    await waitFor(() => {
      const pixel = cropCanvas
        .getContext("2d")
        ?.getImageData(60, 120, 1, 1).data;
      expect(pixel?.[0]).toBeGreaterThan(cropPixel?.[0] ?? 0);
      expect(pixel?.[1]).toBeLessThan(cropPixel?.[1] ?? 255);
    });
    expect(cropCanvas.style.width).toBe(initialWidth);
    expect(cropCanvas.style.height).toBe(initialHeight);

    await hideButton.click();
    await waitFor(() => {
      const pixel = cropCanvas
        .getContext("2d")
        ?.getImageData(60, 120, 1, 1).data;
      expect(pixel).toEqual(cropPixel);
    });
  });

  it("switches the CAM and taxonomy to the selected species", async () => {
    renderInspector();
    const showLabel = enMain.resultsTable.showModelFocus.replace(
      "{{species}}",
      "Vicia cracca",
    );

    const secondSpecies = page.getByRole("button", { name: showLabel });
    await secondSpecies.click();
    await expect
      .element(
        page.getByRole("img", {
          name: enMain.resultsTable.modelFocusFor.replace(
            "{{species}}",
            "Vicia cracca",
          ),
        }),
      )
      .toBeVisible();
    await expect
      .element(
        page.getByText(
          enMain.resultsTable.taxonomyFor.replace(
            "{{species}}",
            "Vicia cracca",
          ),
        ),
      )
      .toBeVisible();
    await expect.element(page.getByText(/Fabaceae · 15.00%/)).toBeVisible();
    await expect.element(page.getByText(/Vicia · 15.00%/)).toBeVisible();
  });

  it("omits CAM controls when the classifier did not provide maps", async () => {
    renderInspector(false);

    expect(
      await page
        .getByRole("button", {
          name: /model focus/i,
        })
        .all(),
    ).toHaveLength(0);
    await expect.element(page.getByText(/Poaceae · 80.00%/)).toBeVisible();
  });
});
