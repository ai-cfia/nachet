import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, cleanup } from "@testing-library/react";
import { page } from "vitest/browser";
import { I18nextProvider } from "react-i18next";
import i18n from "../../i18n";
import enMain from "../../locales/en/main";
import frMain from "../../locales/fr/main";
import type { Images, InferenceResult } from "@common/types";
import ImageGallery from "../ImageGallery";

const makeImage = (
  index: number,
  imageName = `image-${index}.png`,
): Images => ({
  index,
  src: "data:image/png;base64,abc",
  imageDims: [800, 600],
  metadata: {
    imageName,
    deviceBrandId: "",
    deviceModelId: "",
    deviceLensId: "",
    trayCode: "",
    description: "",
  },
  sha256: `sha-${index}`,
});

const makeResult = (
  totalBoxes = 2,
  completedAt = "2024-06-15T10:30:45Z",
): InferenceResult => ({
  scores: [],
  classifications: [],
  boxes: [],
  topN: [],
  overlapping: [],
  overlappingIndices: [],
  labelOccurrence: {},
  totalBoxes,
  models: [],
  completedAt,
  isActive: true,
  minBoxSize: 10,
});

const makeProps = () => ({
  images: [] as Images[],
  currentIndex: 0,
  activeResultKey: null as string | null,
  checkedImages: new Set<number>(),
  checkedResults: new Set<string>(),
  onCheckedImagesChange: vi.fn(),
  onCheckedResultsChange: vi.fn(),
  onSelectImage: vi.fn(),
  onSelectResult: vi.fn(),
  onRemoveImage: vi.fn(),
  onRemoveResult: vi.fn(),
  onEditMetadata: vi.fn(),
  onClear: vi.fn(),
  getResultsForImage: vi.fn().mockReturnValue([]),
});

type GalleryProps = ReturnType<typeof makeProps>;

const renderTemplate = (template: string, values: Record<string, string>) =>
  Object.entries(values).reduce(
    (text, [key, value]) => text.replace(`{{${key}}}`, value),
    template,
  );

const formatResultTime = (completedAt: string) => {
  const date = new Date(completedAt);
  const yy = String(date.getFullYear()).slice(2);
  const mo = String(date.getMonth() + 1).padStart(2, "0");
  const dd = String(date.getDate()).padStart(2, "0");
  const hh = String(date.getHours()).padStart(2, "0");
  const mm = String(date.getMinutes()).padStart(2, "0");
  const ss = String(date.getSeconds()).padStart(2, "0");
  return `${yy}${mo}${dd}${hh}${mm}${ss}`;
};

const formatResultEntryLabel = (
  modelConfigId: string,
  completedAt = "2024-06-15T10:30:45Z",
) =>
  renderTemplate(enMain.imageGallery.resultEntry, {
    modelId: modelConfigId.replace(/:(edited-)?\d+$/, ""),
    time: completedAt ? formatResultTime(completedAt) : "",
  });

const renderGallery = (props: Partial<GalleryProps> = {}) =>
  render(
    <I18nextProvider i18n={i18n}>
      <ImageGallery {...makeProps()} {...props} />
    </I18nextProvider>,
  );

describe("ImageGallery", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en");
    vi.clearAllMocks();
  });

  afterEach(cleanup);

  describe("header", () => {
    it("renders the gallery title", async () => {
      renderGallery();
      await expect
        .element(page.getByText(enMain.imageGallery.title))
        .toBeVisible();
    });

    it("renders the delete/clear action button", async () => {
      renderGallery({ images: [makeImage(0)] });
      await expect
        .element(
          page.getByRole("button", {
            name: enMain.imageGallery.clearAllImages,
          }),
        )
        .toBeVisible();
    });

    it("disables the action button when there are no images", async () => {
      renderGallery();
      await expect
        .element(
          page.getByRole("button", {
            name: enMain.imageGallery.clearAllImages,
          }),
        )
        .toBeDisabled();
    });

    it("enables the action button when images are present", async () => {
      renderGallery({ images: [makeImage(0)] });
      await expect
        .element(
          page.getByRole("button", {
            name: enMain.imageGallery.clearAllImages,
          }),
        )
        .not.toBeDisabled();
    });

    it("disables the select-all checkbox when there are no images", async () => {
      renderGallery();
      await expect
        .element(
          page.getByRole("checkbox", {
            name: enMain.imageGallery.selectAllImages,
          }),
        )
        .toBeDisabled();
    });
  });

  describe("image list", () => {
    it("renders nothing in the table when images is empty", async () => {
      renderGallery();
      expect(await page.getByRole("row").all()).toHaveLength(0);
    });

    it("renders one row per image", async () => {
      renderGallery({ images: [makeImage(0), makeImage(1), makeImage(2)] });
      expect(await page.getByRole("row").all()).toHaveLength(3);
    });

    it("displays the image name from metadata", async () => {
      renderGallery({ images: [makeImage(0, "my-photo.png")] });
      await expect.element(page.getByText("my-photo.png")).toBeVisible();
    });

    it("falls back to the numbered image label when imageName is empty", async () => {
      const img = makeImage(0, "");
      renderGallery({ images: [img] });
      await expect
        .element(
          page.getByText(enMain.imageGallery.image.replace("{{number}}", "1")),
        )
        .toBeVisible();
    });

    it("renders an edit metadata button for each image", async () => {
      renderGallery({ images: [makeImage(0), makeImage(1)] });
      expect(
        await page
          .getByRole("button", {
            name: new RegExp(
              enMain.imageGallery.editMetadataImage.replace(
                "{{number}}",
                "\\d+",
              ),
            ),
          })
          .all(),
      ).toHaveLength(2);
    });
  });

  describe("image selection", () => {
    it("calls onSelectImage with the image index when clicking an image row", async () => {
      const onSelectImage = vi.fn();
      renderGallery({ images: [makeImage(0)], onSelectImage });
      await page.getByText("image-0.png").click();
      expect(onSelectImage).toHaveBeenCalledWith(0);
    });

    it("calls onSelectImage for the correct image when multiple are present", async () => {
      const onSelectImage = vi.fn();
      renderGallery({
        images: [makeImage(0), makeImage(1)],
        onSelectImage,
      });
      await page.getByText("image-1.png").click();
      expect(onSelectImage).toHaveBeenCalledWith(1);
    });

    it("calls onEditMetadata when the edit button is clicked", async () => {
      const onEditMetadata = vi.fn();
      renderGallery({ images: [makeImage(0)], onEditMetadata });
      await page
        .getByRole("button", {
          name: renderTemplate(enMain.imageGallery.editMetadataImage, {
            number: "1",
          }),
        })
        .click();
      expect(onEditMetadata).toHaveBeenCalledWith(0);
    });

    it("does not call onSelectImage when the edit button is clicked", async () => {
      const onSelectImage = vi.fn();
      renderGallery({ images: [makeImage(0)], onSelectImage });
      await page
        .getByRole("button", {
          name: renderTemplate(enMain.imageGallery.editMetadataImage, {
            number: "1",
          }),
        })
        .click();
      expect(onSelectImage).not.toHaveBeenCalled();
    });
  });

  describe("expand / collapse", () => {
    const resultEntry = { modelConfigId: "model-a:123", result: makeResult() };

    it("shows result entries by default (expanded)", async () => {
      const getResultsForImage = vi.fn().mockReturnValue([resultEntry]);
      renderGallery({ images: [makeImage(0)], getResultsForImage });
      await expect
        .element(
          page.getByText(enMain.imageGallery.boxes.replace("{{count}}", "2")),
        )
        .toBeVisible();
    });

    it("shows the boxes count for a result", async () => {
      const getResultsForImage = vi
        .fn()
        .mockReturnValue([
          { modelConfigId: "model-a:123", result: makeResult(5) },
        ]);
      renderGallery({ images: [makeImage(0)], getResultsForImage });
      await expect
        .element(
          page.getByText(enMain.imageGallery.boxes.replace("{{count}}", "5")),
        )
        .toBeVisible();
    });

    it("renders the formatted result entry label", async () => {
      const getResultsForImage = vi
        .fn()
        .mockReturnValue([
          { modelConfigId: "model-a:123", result: makeResult() },
        ]);
      renderGallery({ images: [makeImage(0)], getResultsForImage });
      await expect
        .element(page.getByText(formatResultEntryLabel("model-a:123")))
        .toBeVisible();
    });

    it("strips edited suffixes from result model IDs", async () => {
      const getResultsForImage = vi.fn().mockReturnValue([
        {
          modelConfigId: "model-a:edited-123",
          result: makeResult(),
        },
      ]);
      renderGallery({ images: [makeImage(0)], getResultsForImage });
      await expect
        .element(page.getByText(formatResultEntryLabel("model-a:edited-123")))
        .toBeVisible();
    });

    it("renders result entries without a timestamp when completedAt is empty", async () => {
      const getResultsForImage = vi.fn().mockReturnValue([
        {
          modelConfigId: "model-a:123",
          result: makeResult(2, ""),
        },
      ]);
      renderGallery({ images: [makeImage(0)], getResultsForImage });
      await expect
        .element(page.getByText(formatResultEntryLabel("model-a:123", "")))
        .toBeVisible();
    });

    it("collapses results when the image row is clicked", async () => {
      const getResultsForImage = vi.fn().mockReturnValue([resultEntry]);
      renderGallery({ images: [makeImage(0)], getResultsForImage });
      await expect
        .element(
          page.getByText(enMain.imageGallery.boxes.replace("{{count}}", "2")),
        )
        .toBeVisible();
      await page.getByText("image-0.png").click();
      await expect
        .element(
          page.getByText(enMain.imageGallery.boxes.replace("{{count}}", "2")),
        )
        .not.toBeVisible();
    });

    it("re-expands results when the same image row is clicked again", async () => {
      const getResultsForImage = vi.fn().mockReturnValue([resultEntry]);
      renderGallery({ images: [makeImage(0)], getResultsForImage });
      await page.getByText("image-0.png").click();
      await page.getByText("image-0.png").click();
      await expect
        .element(
          page.getByText(enMain.imageGallery.boxes.replace("{{count}}", "2")),
        )
        .toBeVisible();
    });
  });

  describe("results indicator", () => {
    it("shows the results-available icon when an image has results", async () => {
      const getResultsForImage = vi
        .fn()
        .mockReturnValue([{ modelConfigId: "m:1", result: makeResult() }]);
      renderGallery({ images: [makeImage(0)], getResultsForImage });
      await expect
        .element(
          page.getByRole("img", { name: enMain.imageGallery.resultsAvailable }),
        )
        .toBeVisible();
    });

    it("does not show the results-available icon when an image has no results", async () => {
      renderGallery({ images: [makeImage(0)] });
      expect(
        await page
          .getByRole("img", { name: enMain.imageGallery.resultsAvailable })
          .all(),
      ).toHaveLength(0);
    });
  });

  describe("result selection", () => {
    it("calls onSelectResult when a result entry is clicked", async () => {
      const onSelectResult = vi.fn();
      const getResultsForImage = vi
        .fn()
        .mockReturnValue([
          { modelConfigId: "model-a:123", result: makeResult() },
        ]);
      renderGallery({
        images: [makeImage(0)],
        getResultsForImage,
        onSelectResult,
      });
      await page.getByText(formatResultEntryLabel("model-a:123")).click();
      expect(onSelectResult).toHaveBeenCalledWith("0:model-a:123");
    });
  });

  describe("image checkboxes", () => {
    it("renders a checkbox for each image", async () => {
      renderGallery({ images: [makeImage(0), makeImage(1)] });
      expect(
        await page.getByRole("checkbox", { name: /^Select image \d+$/ }).all(),
      ).toHaveLength(2);
    });

    it("image checkbox is unchecked when not in checkedImages", async () => {
      renderGallery({
        images: [makeImage(0)],
        checkedImages: new Set<number>(),
      });
      await expect
        .element(
          page.getByRole("checkbox", {
            name: renderTemplate(enMain.imageGallery.selectImage, {
              number: "1",
            }),
          }),
        )
        .not.toBeChecked();
    });

    it("image checkbox is checked when index is in checkedImages", async () => {
      renderGallery({
        images: [makeImage(0)],
        checkedImages: new Set([0]),
      });
      await expect
        .element(
          page.getByRole("checkbox", {
            name: renderTemplate(enMain.imageGallery.selectImage, {
              number: "1",
            }),
          }),
        )
        .toBeChecked();
    });

    it("calls onCheckedImagesChange with updated set when checking an image", async () => {
      const onCheckedImagesChange = vi.fn();
      renderGallery({
        images: [makeImage(0)],
        checkedImages: new Set<number>(),
        onCheckedImagesChange,
      });
      await page
        .getByRole("checkbox", {
          name: renderTemplate(enMain.imageGallery.selectImage, {
            number: "1",
          }),
        })
        .click();
      expect(onCheckedImagesChange).toHaveBeenCalledWith(new Set([0]));
    });

    it("calls onCheckedImagesChange with updated set when unchecking an image", async () => {
      const onCheckedImagesChange = vi.fn();
      renderGallery({
        images: [makeImage(0)],
        checkedImages: new Set([0]),
        onCheckedImagesChange,
      });
      await page
        .getByRole("checkbox", {
          name: renderTemplate(enMain.imageGallery.selectImage, {
            number: "1",
          }),
        })
        .click();
      expect(onCheckedImagesChange).toHaveBeenCalledWith(new Set());
    });

    it("does not call onSelectImage when clicking an image checkbox", async () => {
      const onSelectImage = vi.fn();
      renderGallery({ images: [makeImage(0)], onSelectImage });
      await page
        .getByRole("checkbox", {
          name: renderTemplate(enMain.imageGallery.selectImage, {
            number: "1",
          }),
        })
        .click();
      expect(onSelectImage).not.toHaveBeenCalled();
    });

    it("selects all image checkboxes from the header checkbox", async () => {
      const onCheckedImagesChange = vi.fn();
      renderGallery({
        images: [makeImage(0), makeImage(1)],
        checkedImages: new Set<number>(),
        onCheckedImagesChange,
      });
      await page
        .getByRole("checkbox", { name: enMain.imageGallery.selectAllImages })
        .click();
      expect(onCheckedImagesChange).toHaveBeenCalledWith(new Set([0, 1]));
    });

    it("clears image checkbox selection from the header checkbox when all images are selected", async () => {
      const onCheckedImagesChange = vi.fn();
      renderGallery({
        images: [makeImage(0), makeImage(1)],
        checkedImages: new Set([0, 1]),
        onCheckedImagesChange,
      });
      await page
        .getByRole("checkbox", { name: enMain.imageGallery.deselectAllImages })
        .click();
      expect(onCheckedImagesChange).toHaveBeenCalledWith(new Set());
    });

    it("shows the header checkbox as indeterminate when some images are selected", async () => {
      renderGallery({
        images: [makeImage(0), makeImage(1)],
        checkedImages: new Set([0]),
      });
      await expect
        .element(
          page.getByRole("checkbox", {
            name: enMain.imageGallery.selectAllImages,
          }),
        )
        .toHaveAttribute("data-indeterminate", "true");
    });
  });

  describe("result checkboxes", () => {
    const resultEntry = { modelConfigId: "model-a:123", result: makeResult() };

    it("renders a checkbox for each result entry", async () => {
      const getResultsForImage = vi.fn().mockReturnValue([resultEntry]);
      renderGallery({ images: [makeImage(0)], getResultsForImage });
      expect(
        await page
          .getByRole("checkbox", { name: /Select result model-a/ })
          .all(),
      ).toHaveLength(1);
    });

    it("result checkbox is unchecked when not in checkedResults", async () => {
      const getResultsForImage = vi.fn().mockReturnValue([resultEntry]);
      renderGallery({
        images: [makeImage(0)],
        getResultsForImage,
        checkedResults: new Set<string>(),
      });
      await expect
        .element(
          page.getByRole("checkbox", {
            name: renderTemplate(enMain.imageGallery.selectResult, {
              modelId: "model-a",
            }),
          }),
        )
        .not.toBeChecked();
    });

    it("result checkbox is checked when key is in checkedResults", async () => {
      const getResultsForImage = vi.fn().mockReturnValue([resultEntry]);
      renderGallery({
        images: [makeImage(0)],
        getResultsForImage,
        checkedResults: new Set(["0:model-a:123"]),
      });
      await expect
        .element(
          page.getByRole("checkbox", {
            name: renderTemplate(enMain.imageGallery.selectResult, {
              modelId: "model-a",
            }),
          }),
        )
        .toBeChecked();
    });

    it("calls onCheckedResultsChange when checking a result", async () => {
      const onCheckedResultsChange = vi.fn();
      const getResultsForImage = vi.fn().mockReturnValue([resultEntry]);
      renderGallery({
        images: [makeImage(0)],
        getResultsForImage,
        checkedResults: new Set<string>(),
        onCheckedResultsChange,
      });
      await page
        .getByRole("checkbox", {
          name: renderTemplate(enMain.imageGallery.selectResult, {
            modelId: "model-a",
          }),
        })
        .click();
      expect(onCheckedResultsChange).toHaveBeenCalledWith(
        new Set(["0:model-a:123"]),
      );
    });

    it("calls onCheckedResultsChange when unchecking a result", async () => {
      const onCheckedResultsChange = vi.fn();
      const getResultsForImage = vi.fn().mockReturnValue([resultEntry]);
      renderGallery({
        images: [makeImage(0)],
        getResultsForImage,
        checkedResults: new Set(["0:model-a:123"]),
        onCheckedResultsChange,
      });
      await page
        .getByRole("checkbox", {
          name: renderTemplate(enMain.imageGallery.selectResult, {
            modelId: "model-a",
          }),
        })
        .click();
      expect(onCheckedResultsChange).toHaveBeenCalledWith(new Set());
    });

    it("does not call onSelectResult when clicking a result checkbox", async () => {
      const onSelectResult = vi.fn();
      const getResultsForImage = vi.fn().mockReturnValue([resultEntry]);
      renderGallery({
        images: [makeImage(0)],
        getResultsForImage,
        onSelectResult,
      });
      await page
        .getByRole("checkbox", {
          name: renderTemplate(enMain.imageGallery.selectResult, {
            modelId: "model-a",
          }),
        })
        .click();
      expect(onSelectResult).not.toHaveBeenCalled();
    });
  });

  describe("delete / clear button behavior", () => {
    it("shows 'clear all images' label when nothing is checked", async () => {
      renderGallery({
        images: [makeImage(0)],
        checkedImages: new Set<number>(),
        checkedResults: new Set<string>(),
      });
      await expect
        .element(
          page.getByRole("button", {
            name: enMain.imageGallery.clearAllImages,
          }),
        )
        .toBeVisible();
    });

    it("shows removeResult label when images are checked", async () => {
      renderGallery({
        images: [makeImage(0)],
        checkedImages: new Set([0]),
      });
      await expect
        .element(
          page.getByRole("button", { name: enMain.imageGallery.removeResult }),
        )
        .toBeVisible();
    });

    it("shows removeResult label when results are checked", async () => {
      renderGallery({
        images: [makeImage(0)],
        checkedResults: new Set(["0:model-a"]),
      });
      await expect
        .element(
          page.getByRole("button", { name: enMain.imageGallery.removeResult }),
        )
        .toBeVisible();
    });

    it("calls onClear when nothing is checked and the button is clicked", async () => {
      const onClear = vi.fn();
      renderGallery({ images: [makeImage(0)], onClear });
      await page
        .getByRole("button", {
          name: enMain.imageGallery.clearAllImages,
        })
        .click();
      expect(onClear).toHaveBeenCalledOnce();
    });

    it("calls onRemoveImage for each checked image and resets state when button clicked", async () => {
      const onRemoveImage = vi.fn();
      const onCheckedImagesChange = vi.fn();
      renderGallery({
        images: [makeImage(0), makeImage(1)],
        checkedImages: new Set([0, 1]),
        onRemoveImage,
        onCheckedImagesChange,
      });
      await page
        .getByRole("button", { name: enMain.imageGallery.removeResult })
        .click();
      expect(onRemoveImage).toHaveBeenCalledWith(0);
      expect(onRemoveImage).toHaveBeenCalledWith(1);
      expect(onCheckedImagesChange).toHaveBeenCalledWith(new Set());
    });

    it("calls onRemoveResult for each checked result and resets state when button clicked", async () => {
      const onRemoveResult = vi.fn();
      const onCheckedResultsChange = vi.fn();
      renderGallery({
        images: [makeImage(0)],
        checkedResults: new Set(["0:model-a", "0:model-b"]),
        onRemoveResult,
        onCheckedResultsChange,
      });
      await page
        .getByRole("button", { name: enMain.imageGallery.removeResult })
        .click();
      expect(onRemoveResult).toHaveBeenCalledWith("0:model-a");
      expect(onRemoveResult).toHaveBeenCalledWith("0:model-b");
      expect(onCheckedResultsChange).toHaveBeenCalledWith(new Set());
    });

    it("removes both checked images and checked results in one action", async () => {
      const onRemoveImage = vi.fn();
      const onRemoveResult = vi.fn();
      const onCheckedImagesChange = vi.fn();
      const onCheckedResultsChange = vi.fn();
      renderGallery({
        images: [makeImage(0), makeImage(1)],
        checkedImages: new Set([1]),
        checkedResults: new Set(["0:model-a:123"]),
        onRemoveImage,
        onRemoveResult,
        onCheckedImagesChange,
        onCheckedResultsChange,
      });
      await page
        .getByRole("button", { name: enMain.imageGallery.removeResult })
        .click();
      expect(onRemoveImage).toHaveBeenCalledWith(1);
      expect(onRemoveResult).toHaveBeenCalledWith("0:model-a:123");
      expect(onCheckedImagesChange).toHaveBeenCalledWith(new Set());
      expect(onCheckedResultsChange).toHaveBeenCalledWith(new Set());
    });

    it("does not call onClear when checked items exist and the button is clicked", async () => {
      const onClear = vi.fn();
      renderGallery({
        images: [makeImage(0)],
        checkedImages: new Set([0]),
        onClear,
      });
      await page
        .getByRole("button", { name: enMain.imageGallery.removeResult })
        .click();
      expect(onClear).not.toHaveBeenCalled();
    });
  });

  describe("active result highlighting", () => {
    it("marks the active result entry as pressed", async () => {
      const getResultsForImage = vi
        .fn()
        .mockReturnValue([
          { modelConfigId: "model-a:1", result: makeResult(3) },
        ]);
      renderGallery({
        images: [makeImage(0)],
        activeResultKey: "0:model-a:1",
        getResultsForImage,
      });
      await expect
        .element(page.getByTestId("result-row-0:model-a:1"))
        .toHaveAttribute("aria-pressed", "true");
    });

    it("marks inactive result entries as not pressed", async () => {
      const getResultsForImage = vi
        .fn()
        .mockReturnValue([
          { modelConfigId: "model-a:1", result: makeResult(3) },
        ]);
      renderGallery({
        images: [makeImage(0)],
        activeResultKey: null,
        getResultsForImage,
      });
      await expect
        .element(page.getByTestId("result-row-0:model-a:1"))
        .toHaveAttribute("aria-pressed", "false");
    });
  });

  describe("current image state", () => {
    it("marks the current image row", async () => {
      renderGallery({
        images: [makeImage(0), makeImage(1)],
        currentIndex: 1,
      });
      await expect
        .element(page.getByTestId("image-row-1"))
        .toHaveAttribute("data-current", "true");
      await expect
        .element(page.getByTestId("image-row-0"))
        .toHaveAttribute("data-current", "false");
    });
  });

  describe("i18n", () => {
    it("shows the French gallery title in French mode", async () => {
      await i18n.changeLanguage("fr");
      renderGallery();
      await expect
        .element(page.getByText(frMain.imageGallery.title))
        .toBeVisible();
    });

    it("shows the French clear-all label when nothing is checked", async () => {
      await i18n.changeLanguage("fr");
      renderGallery({ images: [makeImage(0)] });
      await expect
        .element(
          page.getByRole("button", {
            name: frMain.imageGallery.clearAllImages,
          }),
        )
        .toBeVisible();
    });

    it("shows the French removeResult label when items are checked (French mode)", async () => {
      await i18n.changeLanguage("fr");
      renderGallery({
        images: [makeImage(0)],
        checkedImages: new Set([0]),
      });
      await expect
        .element(
          page.getByRole("button", { name: frMain.imageGallery.removeResult }),
        )
        .toBeVisible();
    });

    it("shows the French edit-metadata label in French mode", async () => {
      await i18n.changeLanguage("fr");
      renderGallery({ images: [makeImage(0)] });
      await expect
        .element(
          page.getByRole("button", {
            name: renderTemplate(frMain.imageGallery.editMetadataImage, {
              number: "1",
            }),
          }),
        )
        .toBeVisible();
    });

    it("shows the French results-available icon in French mode", async () => {
      await i18n.changeLanguage("fr");
      const getResultsForImage = vi
        .fn()
        .mockReturnValue([{ modelConfigId: "m:1", result: makeResult() }]);
      renderGallery({ images: [makeImage(0)], getResultsForImage });
      await expect
        .element(
          page.getByRole("img", { name: frMain.imageGallery.resultsAvailable }),
        )
        .toBeVisible();
    });
  });
});
