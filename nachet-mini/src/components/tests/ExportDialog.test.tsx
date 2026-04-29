import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, cleanup } from "@testing-library/react";
import { page } from "vitest/browser";
import { I18nextProvider } from "react-i18next";
import i18n from "../../i18n";
import enMain from "../../locales/en/main";
import frMain from "../../locales/fr/main";
import enCommon from "../../locales/en/common";
import frCommon from "../../locales/fr/common";
import { useImageStore } from "@stores/useImageStore";
import { useInferenceStore } from "@stores/useInferenceStore";
import ExportDialog from "../ExportDialog";

const { mockBuildExportManifest, mockGenerateExportZip } = vi.hoisted(() => ({
  mockBuildExportManifest: vi.fn(),
  mockGenerateExportZip: vi.fn(),
}));

vi.mock("@common/exportUtils", () => ({
  buildExportManifest: mockBuildExportManifest,
  generateExportZip: mockGenerateExportZip,
}));

vi.mock("@stores/useImageStore", () => ({ useImageStore: vi.fn() }));
vi.mock("@stores/useInferenceStore", () => ({ useInferenceStore: vi.fn() }));

const makeImage = (index: number, src = "data:image/png;base64,abc") => ({
  index,
  src,
  imageDims: [800, 600],
  metadata: { imageName: `image-${index}.png` },
  sha256: `sha-${index}`,
});

type ExportTestImage = ReturnType<typeof makeImage>;
type InferenceResultEntry = { modelConfigId: string; result: unknown };
type ImageStoreState = {
  images: ExportTestImage[];
};
type InferenceStoreState = {
  results: Map<string, unknown>;
  getResultsForImage: (index: number) => InferenceResultEntry[];
};

const setStores = (
  images: ExportTestImage[] = [],
  resultsMap: Map<string, unknown> = new Map(),
  getResultsForImageFn?: (index: number) => InferenceResultEntry[],
) => {
  vi.mocked(useImageStore).mockImplementation(
    (selector: (state: ImageStoreState) => unknown) => selector({ images }),
  );
  const getResultsForImage =
    getResultsForImageFn ?? vi.fn().mockReturnValue([]);
  vi.mocked(useInferenceStore).mockImplementation(
    (selector: (state: InferenceStoreState) => unknown) =>
      selector({ results: resultsMap, getResultsForImage }),
  );
};

interface RenderProps {
  open?: boolean;
  checkedImages?: Set<number>;
  checkedResults?: Set<string>;
  onClose?: () => void;
  onExportComplete?: () => void;
}

const renderDialog = ({
  open = true,
  checkedImages = new Set<number>(),
  checkedResults = new Set<string>(),
  onClose = vi.fn(),
  onExportComplete = vi.fn(),
}: RenderProps = {}) =>
  render(
    <I18nextProvider i18n={i18n}>
      <ExportDialog
        open={open}
        onClose={onClose}
        checkedImages={checkedImages}
        checkedResults={checkedResults}
        onExportComplete={onExportComplete}
      />
    </I18nextProvider>,
  );

describe("ExportDialog", () => {
  let consoleErrorSpy: ReturnType<typeof vi.spyOn>;

  beforeEach(async () => {
    localStorage.clear();
    await i18n.changeLanguage("en");
    consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    mockBuildExportManifest.mockReset();
    mockGenerateExportZip.mockReset();
    mockBuildExportManifest.mockReturnValue({ images: [] });
    mockGenerateExportZip.mockResolvedValue(undefined);
    setStores();
  });

  afterEach(cleanup);
  afterEach(() => {
    consoleErrorSpy.mockRestore();
  });

  describe("when closed", () => {
    it("does not render the dialog when open is false", async () => {
      renderDialog({ open: false });
      expect(await page.getByRole("dialog").all()).toHaveLength(0);
    });
  });

  describe("when open", () => {
    it("renders the dialog title", async () => {
      renderDialog();
      await expect
        .element(page.getByRole("heading", { name: enMain.exportDialog.title }))
        .toBeVisible();
    });

    it("renders a close button", async () => {
      renderDialog();
      await expect
        .element(page.getByRole("button", { name: "close" }))
        .toBeVisible();
    });

    it("renders the Cancel button", async () => {
      renderDialog();
      await expect
        .element(page.getByRole("button", { name: enCommon.actions.cancel }))
        .toBeVisible();
    });

    it("renders the Export button", async () => {
      renderDialog();
      await expect
        .element(page.getByRole("button", { name: enMain.exportDialog.title }))
        .toBeVisible();
    });

    it("shows nothingSelected text when no images or results are checked", async () => {
      renderDialog();
      await expect
        .element(page.getByText(enMain.exportDialog.nothingSelected))
        .toBeVisible();
    });

    it("shows summary text when images are checked", async () => {
      const getResultsForImage = vi.fn().mockReturnValue([]);
      setStores([makeImage(0)], new Map(), getResultsForImage);
      renderDialog({ checkedImages: new Set([0]) });
      await expect
        .element(
          page.getByText(
            enMain.exportDialog.summary
              .replace("{{imageCount}}", "1")
              .replace("{{resultCount}}", "0"),
          ),
        )
        .toBeVisible();
    });

    it("disables the Export button when nothing is selected", async () => {
      renderDialog();
      await expect
        .element(page.getByRole("button", { name: enMain.exportDialog.title }))
        .toBeDisabled();
    });

    it("enables the Export button when an image is checked", async () => {
      setStores([makeImage(0)]);
      renderDialog({ checkedImages: new Set([0]) });
      await expect
        .element(page.getByRole("button", { name: enMain.exportDialog.title }))
        .not.toBeDisabled();
    });

    it("enables the Export button when only results are checked", async () => {
      setStores([makeImage(0)]);
      renderDialog({ checkedResults: new Set(["0:model-a"]) });
      await expect
        .element(page.getByRole("button", { name: enMain.exportDialog.title }))
        .not.toBeDisabled();
    });
  });

  describe("checkboxes", () => {
    it("renders all five option checkboxes", async () => {
      renderDialog();
      await expect
        .element(
          page.getByRole("checkbox", {
            name: enMain.exportDialog.includeImages,
          }),
        )
        .toBeVisible();
      await expect
        .element(
          page.getByRole("checkbox", {
            name: enMain.exportDialog.includeResults,
          }),
        )
        .toBeVisible();
      await expect
        .element(
          page.getByRole("checkbox", { name: enMain.exportDialog.includeCsv }),
        )
        .toBeVisible();
      await expect
        .element(
          page.getByRole("checkbox", {
            name: enMain.exportDialog.includeAnnotatedImages,
          }),
        )
        .toBeVisible();
      await expect
        .element(
          page.getByRole("checkbox", {
            name: enMain.exportDialog.humanReadable,
          }),
        )
        .toBeVisible();
    });

    it("starts with includeImages checked", async () => {
      renderDialog();
      await expect
        .element(
          page.getByRole("checkbox", {
            name: enMain.exportDialog.includeImages,
          }),
        )
        .toBeChecked();
    });

    it("starts with includeResults checked", async () => {
      renderDialog();
      await expect
        .element(
          page.getByRole("checkbox", {
            name: enMain.exportDialog.includeResults,
          }),
        )
        .toBeChecked();
    });

    it("starts with includeCsv checked", async () => {
      renderDialog();
      await expect
        .element(
          page.getByRole("checkbox", { name: enMain.exportDialog.includeCsv }),
        )
        .toBeChecked();
    });

    it("starts with includeAnnotatedImages unchecked", async () => {
      renderDialog();
      await expect
        .element(
          page.getByRole("checkbox", {
            name: enMain.exportDialog.includeAnnotatedImages,
          }),
        )
        .not.toBeChecked();
    });

    it("starts with humanReadable unchecked", async () => {
      renderDialog();
      await expect
        .element(
          page.getByRole("checkbox", {
            name: enMain.exportDialog.humanReadable,
          }),
        )
        .not.toBeChecked();
    });

    it("can toggle includeImages off", async () => {
      renderDialog();
      await page
        .getByRole("checkbox", { name: enMain.exportDialog.includeImages })
        .click();
      await expect
        .element(
          page.getByRole("checkbox", {
            name: enMain.exportDialog.includeImages,
          }),
        )
        .not.toBeChecked();
    });

    it("can toggle includeAnnotatedImages on", async () => {
      renderDialog();
      await page
        .getByRole("checkbox", {
          name: enMain.exportDialog.includeAnnotatedImages,
        })
        .click();
      await expect
        .element(
          page.getByRole("checkbox", {
            name: enMain.exportDialog.includeAnnotatedImages,
          }),
        )
        .toBeChecked();
    });

    it("disables the Export button when all checkboxes are unchecked", async () => {
      setStores([makeImage(0)]);
      renderDialog({ checkedImages: new Set([0]) });
      await page
        .getByRole("checkbox", { name: enMain.exportDialog.includeImages })
        .click();
      await page
        .getByRole("checkbox", { name: enMain.exportDialog.includeResults })
        .click();
      await page
        .getByRole("checkbox", { name: enMain.exportDialog.includeCsv })
        .click();
      await expect
        .element(page.getByRole("button", { name: enMain.exportDialog.title }))
        .toBeDisabled();
    });
  });

  describe("export behavior", () => {
    const img = makeImage(0);

    beforeEach(() => {
      setStores([img]);
    });

    it("calls buildExportManifest and generateExportZip on export", async () => {
      const onClose = vi.fn();
      const onExportComplete = vi.fn();
      renderDialog({
        checkedImages: new Set([0]),
        onClose,
        onExportComplete,
      });
      await page
        .getByRole("button", { name: enMain.exportDialog.title })
        .click();
      await vi.waitFor(() => {
        expect(mockBuildExportManifest).toHaveBeenCalledOnce();
        expect(mockGenerateExportZip).toHaveBeenCalledOnce();
      });
    });

    it("passes the selected store data into buildExportManifest", async () => {
      const resultsMap = new Map([["0:model-a", { id: "result-a" }]]);
      const getResultsForImage = vi
        .fn()
        .mockReturnValue([
          { modelConfigId: "model-a", result: { id: "result-a" } },
        ]);
      setStores([img], resultsMap, getResultsForImage);

      const checkedImages = new Set([0]);
      const checkedResults = new Set(["0:model-a"]);
      renderDialog({ checkedImages, checkedResults });
      await page
        .getByRole("button", { name: enMain.exportDialog.title })
        .click();

      await vi.waitFor(() =>
        expect(mockBuildExportManifest).toHaveBeenCalledWith(
          [img],
          checkedImages,
          checkedResults,
          getResultsForImage,
          resultsMap,
        ),
      );
    });

    it("passes correct options to generateExportZip by default", async () => {
      renderDialog({ checkedImages: new Set([0]) });
      await page
        .getByRole("button", { name: enMain.exportDialog.title })
        .click();
      await vi.waitFor(() =>
        expect(mockGenerateExportZip).toHaveBeenCalledWith(
          expect.anything(),
          expect.anything(),
          expect.objectContaining({
            includeImages: true,
            includeResults: true,
            includeCsv: true,
            includeAnnotatedImages: false,
            humanReadable: false,
          }),
        ),
      );
    });

    it("passes updated options when checkboxes are changed", async () => {
      renderDialog({ checkedImages: new Set([0]) });
      await page
        .getByRole("checkbox", { name: enMain.exportDialog.includeImages })
        .click();
      await page
        .getByRole("checkbox", { name: enMain.exportDialog.humanReadable })
        .click();
      await page
        .getByRole("button", { name: enMain.exportDialog.title })
        .click();
      await vi.waitFor(() =>
        expect(mockGenerateExportZip).toHaveBeenCalledWith(
          expect.anything(),
          expect.anything(),
          expect.objectContaining({
            includeImages: false,
            humanReadable: true,
          }),
        ),
      );
    });

    it("calls onExportComplete after a successful export", async () => {
      const onExportComplete = vi.fn();
      renderDialog({ checkedImages: new Set([0]), onExportComplete });
      await page
        .getByRole("button", { name: enMain.exportDialog.title })
        .click();
      await vi.waitFor(() => expect(onExportComplete).toHaveBeenCalledOnce());
    });

    it("calls onClose after a successful export", async () => {
      const onClose = vi.fn();
      renderDialog({ checkedImages: new Set([0]), onClose });
      await page
        .getByRole("button", { name: enMain.exportDialog.title })
        .click();
      await vi.waitFor(() => expect(onClose).toHaveBeenCalledOnce());
    });

    it("disables the Export button while exporting", async () => {
      let resolveExport!: () => void;
      mockGenerateExportZip.mockReturnValue(
        new Promise<void>((r) => {
          resolveExport = r;
        }),
      );
      renderDialog({ checkedImages: new Set([0]) });
      await page
        .getByRole("button", { name: enMain.exportDialog.title })
        .click();
      await expect
        .element(page.getByRole("button", { name: enMain.exportDialog.title }))
        .toBeDisabled();
      resolveExport();
    });

    it("shows a duplicate name error when generateExportZip throws DUPLICATE_NAME", async () => {
      mockGenerateExportZip.mockRejectedValue(
        new Error("DUPLICATE_NAME:image-0.png"),
      );
      renderDialog({ checkedImages: new Set([0]) });
      await page
        .getByRole("button", { name: enMain.exportDialog.title })
        .click();
      await vi.waitFor(() =>
        expect(
          page
            .getByText(
              enMain.exportDialog.duplicateNameError.replace(
                "{{name}}",
                "image-0.png",
              ),
            )
            .element(),
        ).toBeTruthy(),
      );
    });

    it("clears the duplicate name error when humanReadable is toggled", async () => {
      mockGenerateExportZip.mockRejectedValueOnce(
        new Error("DUPLICATE_NAME:image-0.png"),
      );
      renderDialog({ checkedImages: new Set([0]) });
      await page
        .getByRole("button", { name: enMain.exportDialog.title })
        .click();
      await vi.waitFor(() =>
        expect(
          page
            .getByText(
              enMain.exportDialog.duplicateNameError.replace(
                "{{name}}",
                "image-0.png",
              ),
            )
            .element(),
        ).toBeTruthy(),
      );
      await page
        .getByRole("checkbox", { name: enMain.exportDialog.humanReadable })
        .click();
      expect(
        await page
          .getByText(
            enMain.exportDialog.duplicateNameError.replace(
              "{{name}}",
              "image-0.png",
            ),
          )
          .all(),
      ).toHaveLength(0);
    });

    it("does not call onExportComplete or onClose when export throws", async () => {
      mockGenerateExportZip.mockRejectedValue(new Error("DUPLICATE_NAME:foo"));
      const onClose = vi.fn();
      const onExportComplete = vi.fn();
      renderDialog({ checkedImages: new Set([0]), onClose, onExportComplete });
      await page
        .getByRole("button", { name: enMain.exportDialog.title })
        .click();
      await vi.waitFor(() =>
        expect(mockGenerateExportZip).toHaveBeenCalledOnce(),
      );
      expect(onExportComplete).not.toHaveBeenCalled();
      expect(onClose).not.toHaveBeenCalled();
    });

    it("recovers cleanly from a non-duplicate export error", async () => {
      mockGenerateExportZip.mockRejectedValue(new Error("zip failed"));
      renderDialog({ checkedImages: new Set([0]) });

      await page
        .getByRole("button", { name: enMain.exportDialog.title })
        .click();

      await vi.waitFor(() =>
        expect(mockGenerateExportZip).toHaveBeenCalledOnce(),
      );
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        "Export error:",
        "zip failed",
      );
      expect(
        await page
          .getByText(
            enMain.exportDialog.duplicateNameError.replace(
              "{{name}}",
              "image-0.png",
            ),
          )
          .all(),
      ).toHaveLength(0);
      await expect
        .element(page.getByRole("button", { name: enMain.exportDialog.title }))
        .not.toBeDisabled();
    });
  });

  describe("result count logic", () => {
    it("includes parent image index for checked results", async () => {
      const getResultsForImage = vi.fn().mockReturnValue([]);
      setStores([makeImage(0), makeImage(1)], new Map(), getResultsForImage);
      renderDialog({
        checkedImages: new Set<number>(),
        checkedResults: new Set(["1:model-a"]),
      });
      await expect
        .element(
          page.getByText(
            enMain.exportDialog.summary
              .replace("{{imageCount}}", "1")
              .replace("{{resultCount}}", "1"),
          ),
        )
        .toBeVisible();
    });

    it("counts all results for a checked image", async () => {
      const fakeResults = [
        { modelConfigId: "model-a", result: {} },
        { modelConfigId: "model-b", result: {} },
      ];
      const getResultsForImage = vi.fn().mockReturnValue(fakeResults);
      setStores([makeImage(0)], new Map(), getResultsForImage);
      renderDialog({ checkedImages: new Set([0]) });
      await expect
        .element(
          page.getByText(
            enMain.exportDialog.summary
              .replace("{{imageCount}}", "1")
              .replace("{{resultCount}}", "2"),
          ),
        )
        .toBeVisible();
    });

    it("counts only specific results for unchecked image with checked results", async () => {
      const getResultsForImage = vi.fn().mockReturnValue([]);
      setStores([makeImage(0)], new Map(), getResultsForImage);
      renderDialog({
        checkedImages: new Set<number>(),
        checkedResults: new Set(["0:model-a", "0:model-b"]),
      });
      await expect
        .element(
          page.getByText(
            enMain.exportDialog.summary
              .replace("{{imageCount}}", "1")
              .replace("{{resultCount}}", "2"),
          ),
        )
        .toBeVisible();
    });

    it("combines checked images and checked results for imageIndices", async () => {
      const getResultsForImage = vi.fn().mockReturnValue([]);
      setStores([makeImage(0), makeImage(1)], new Map(), getResultsForImage);
      renderDialog({
        checkedImages: new Set([0]),
        checkedResults: new Set(["1:model-a"]),
      });
      await expect
        .element(
          page.getByText(
            enMain.exportDialog.summary
              .replace("{{imageCount}}", "2")
              .replace("{{resultCount}}", "1"),
          ),
        )
        .toBeVisible();
    });

    it("does not double count checked results for an already checked image", async () => {
      const fakeResults = [
        { modelConfigId: "model-a", result: {} },
        { modelConfigId: "model-b", result: {} },
      ];
      const getResultsForImage = vi.fn().mockReturnValue(fakeResults);
      setStores([makeImage(0)], new Map(), getResultsForImage);
      renderDialog({
        checkedImages: new Set([0]),
        checkedResults: new Set(["0:model-a"]),
      });
      await expect
        .element(
          page.getByText(
            enMain.exportDialog.summary
              .replace("{{imageCount}}", "1")
              .replace("{{resultCount}}", "2"),
          ),
        )
        .toBeVisible();
    });
  });

  describe("close and cancel behavior", () => {
    it("calls onClose when the close button is clicked", async () => {
      const onClose = vi.fn();
      renderDialog({ onClose });
      await page.getByRole("button", { name: "close" }).click();
      expect(onClose).toHaveBeenCalledOnce();
    });

    it("calls onClose when the Cancel button is clicked", async () => {
      const onClose = vi.fn();
      renderDialog({ onClose });
      await page.getByRole("button", { name: enCommon.actions.cancel }).click();
      expect(onClose).toHaveBeenCalledOnce();
    });
  });

  describe("i18n", () => {
    it("shows the French dialog title in French mode", async () => {
      await i18n.changeLanguage("fr");
      renderDialog();
      await expect
        .element(page.getByRole("heading", { name: frMain.exportDialog.title }))
        .toBeVisible();
    });

    it("shows the French Cancel button in French mode", async () => {
      await i18n.changeLanguage("fr");
      renderDialog();
      await expect
        .element(page.getByRole("button", { name: frCommon.actions.cancel }))
        .toBeVisible();
    });

    it("shows the French nothingSelected message in French mode", async () => {
      await i18n.changeLanguage("fr");
      renderDialog();
      await expect
        .element(page.getByText(frMain.exportDialog.nothingSelected))
        .toBeVisible();
    });

    it("shows the French includeResults checkbox label in French mode", async () => {
      await i18n.changeLanguage("fr");
      renderDialog();
      await expect
        .element(
          page.getByRole("checkbox", {
            name: frMain.exportDialog.includeResults,
          }),
        )
        .toBeVisible();
    });
  });
});
