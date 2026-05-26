import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, cleanup } from "@testing-library/react";
import { page } from "vitest/browser";
import { I18nextProvider } from "react-i18next";
import i18n from "../../i18n";
import enMain from "../../locales/en/main";
import frMain from "../../locales/fr/main";
import type {
  DetectorModelEntry,
  ClassifierModelEntry,
} from "@inference/models";
import { huggingFaceUrl } from "@inference/models";
import ModelLoader from "../ModelLoader";

const TEST_DETECTORS: DetectorModelEntry[] = [
  { id: "detector-a", model: "org/detector-a", threshold: 0.3 },
  { id: "detector-b", model: "org/detector-b", threshold: 0.5 },
];

const TEST_CLASSIFIERS: ClassifierModelEntry[] = [
  { id: "classifier-a", model: "org/classifier-a", topK: 5, minBoxSize: 224 },
  { id: "classifier-b", model: "org/classifier-b", topK: 3, minBoxSize: 384 },
];

interface RenderOptions {
  detectors?: DetectorModelEntry[];
  classifiers?: ClassifierModelEntry[];
  selectedDetectorId?: string;
  selectedClassifierId?: string;
  onSelectDetector?: (id: string) => void;
  onSelectClassifier?: (id: string) => void;
  isLoading?: boolean;
  detectorPrompt?: string;
  onDetectorPromptChange?: (v: string) => void;
  detectorRequiresPrompt?: boolean;
}

const renderModelLoaderElement = ({
  detectors = TEST_DETECTORS,
  classifiers = TEST_CLASSIFIERS,
  selectedDetectorId = TEST_DETECTORS[0].id,
  selectedClassifierId = TEST_CLASSIFIERS[0].id,
  onSelectDetector = vi.fn(),
  onSelectClassifier = vi.fn(),
  isLoading = false,
  detectorPrompt = "",
  onDetectorPromptChange = vi.fn(),
  detectorRequiresPrompt = false,
}: RenderOptions = {}) => (
  <I18nextProvider i18n={i18n}>
    <ModelLoader
      detectors={detectors}
      classifiers={classifiers}
      selectedDetectorId={selectedDetectorId}
      selectedClassifierId={selectedClassifierId}
      onSelectDetector={onSelectDetector}
      onSelectClassifier={onSelectClassifier}
      isLoading={isLoading}
      detectorPrompt={detectorPrompt}
      onDetectorPromptChange={onDetectorPromptChange}
      detectorRequiresPrompt={detectorRequiresPrompt}
    />
  </I18nextProvider>
);

const renderModelLoader = (options: RenderOptions = {}) =>
  render(renderModelLoaderElement(options));

const getDetectorCombobox = (name = enMain.modelLoader.detector) =>
  page.getByRole("combobox", { name });

const getClassifierCombobox = (name = enMain.modelLoader.classifier) =>
  page.getByRole("combobox", { name });

const getDetectorInfoLink = (name = enMain.modelLoader.detectorInfo) =>
  page.getByRole("link", { name });

const getClassifierInfoLink = (name = enMain.modelLoader.classifierInfo) =>
  page.getByRole("link", { name });

describe("ModelLoader", () => {
  beforeEach(async () => {
    localStorage.clear();
    await i18n.changeLanguage("en");
  });

  afterEach(cleanup);

  describe("loading state", () => {
    it("renders a loading status with two skeletons and no controls", async () => {
      renderModelLoader({ isLoading: true });
      await expect
        .element(page.getByRole("status", { name: enMain.modelLoader.loading }))
        .toBeVisible();
      expect(
        await page.getByTestId("model-loader-skeleton").all(),
      ).toHaveLength(2);
      expect(await page.getByRole("combobox").all()).toHaveLength(0);
      expect(await page.getByRole("link").all()).toHaveLength(0);
    });
  });

  describe("rendering", () => {
    it("renders two dropdowns", async () => {
      renderModelLoader();
      expect(await page.getByRole("combobox").all()).toHaveLength(2);
    });

    it("exposes labeled dropdowns in English", async () => {
      renderModelLoader();
      await expect.element(getDetectorCombobox()).toBeVisible();
      await expect.element(getClassifierCombobox()).toBeVisible();
    });

    it("exposes labeled dropdowns in French", async () => {
      await i18n.changeLanguage("fr");
      renderModelLoader();
      await expect
        .element(getDetectorCombobox(frMain.modelLoader.detector))
        .toBeVisible();
      await expect
        .element(getClassifierCombobox(frMain.modelLoader.classifier))
        .toBeVisible();
    });
  });

  describe("model list population", () => {
    it("shows all detector options when the detector dropdown is opened", async () => {
      renderModelLoader();
      await getDetectorCombobox().click();
      for (const d of TEST_DETECTORS) {
        await expect
          .element(page.getByRole("option", { name: d.id }))
          .toBeVisible();
      }
    });

    it("shows all classifier options when the classifier dropdown is opened", async () => {
      renderModelLoader();
      await getClassifierCombobox().click();
      for (const c of TEST_CLASSIFIERS) {
        await expect
          .element(page.getByRole("option", { name: c.id }))
          .toBeVisible();
      }
    });
  });

  describe("selected value", () => {
    it("displays selectedDetectorId as the current detector value", async () => {
      renderModelLoader({ selectedDetectorId: TEST_DETECTORS[1].id });
      await expect
        .element(getDetectorCombobox())
        .toHaveTextContent(TEST_DETECTORS[1].id);
    });

    it("displays selectedClassifierId as the current classifier value", async () => {
      renderModelLoader({ selectedClassifierId: TEST_CLASSIFIERS[1].id });
      await expect
        .element(getClassifierCombobox())
        .toHaveTextContent(TEST_CLASSIFIERS[1].id);
    });

    it("updates the selected values and info links after rerender", async () => {
      const view = renderModelLoader();
      await expect
        .element(getDetectorCombobox())
        .toHaveTextContent(TEST_DETECTORS[0].id);
      await expect
        .element(getDetectorInfoLink())
        .toHaveAttribute("href", huggingFaceUrl(TEST_DETECTORS[0].model));
      await expect
        .element(getClassifierCombobox())
        .toHaveTextContent(TEST_CLASSIFIERS[0].id);
      await expect
        .element(getClassifierInfoLink())
        .toHaveAttribute("href", huggingFaceUrl(TEST_CLASSIFIERS[0].model));

      view.rerender(
        renderModelLoaderElement({
          selectedDetectorId: TEST_DETECTORS[1].id,
          selectedClassifierId: TEST_CLASSIFIERS[1].id,
        }),
      );

      await expect
        .element(getDetectorCombobox())
        .toHaveTextContent(TEST_DETECTORS[1].id);
      await expect
        .element(getDetectorInfoLink())
        .toHaveAttribute("href", huggingFaceUrl(TEST_DETECTORS[1].model));
      await expect
        .element(getClassifierCombobox())
        .toHaveTextContent(TEST_CLASSIFIERS[1].id);
      await expect
        .element(getClassifierInfoLink())
        .toHaveAttribute("href", huggingFaceUrl(TEST_CLASSIFIERS[1].model));
    });
  });

  describe("info buttons — present when a model is selected", () => {
    it("renders two info links when both models are selected", async () => {
      renderModelLoader();
      expect(await getDetectorInfoLink().all()).toHaveLength(1);
      expect(await getClassifierInfoLink().all()).toHaveLength(1);
    });

    it("renders a detector info link pointing to the correct HuggingFace URL", async () => {
      renderModelLoader({ selectedDetectorId: TEST_DETECTORS[0].id });
      await expect
        .element(getDetectorInfoLink())
        .toHaveAttribute("href", huggingFaceUrl(TEST_DETECTORS[0].model));
    });

    it("renders a classifier info link pointing to the correct HuggingFace URL", async () => {
      renderModelLoader({ selectedClassifierId: TEST_CLASSIFIERS[0].id });
      await expect
        .element(getClassifierInfoLink())
        .toHaveAttribute("href", huggingFaceUrl(TEST_CLASSIFIERS[0].model));
    });

    it("opens info links in a new tab", async () => {
      renderModelLoader();
      await expect
        .element(getDetectorInfoLink())
        .toHaveAttribute("target", "_blank");
      await expect
        .element(getClassifierInfoLink())
        .toHaveAttribute("target", "_blank");
    });

    it("sets rel=noopener noreferrer on info links", async () => {
      renderModelLoader();
      await expect
        .element(getDetectorInfoLink())
        .toHaveAttribute("rel", "noopener noreferrer");
      await expect
        .element(getClassifierInfoLink())
        .toHaveAttribute("rel", "noopener noreferrer");
    });
  });

  describe("info buttons — absent when no model is selected", () => {
    it("renders only the classifier link when selectedDetectorId does not match", async () => {
      renderModelLoader({ selectedDetectorId: "" });
      expect(await getDetectorInfoLink().all()).toHaveLength(0);
      await expect
        .element(getClassifierInfoLink())
        .toHaveAttribute("href", huggingFaceUrl(TEST_CLASSIFIERS[0].model));
    });

    it("renders only the detector link when selectedClassifierId does not match", async () => {
      renderModelLoader({ selectedClassifierId: "" });
      expect(await getClassifierInfoLink().all()).toHaveLength(0);
      await expect
        .element(getDetectorInfoLink())
        .toHaveAttribute("href", huggingFaceUrl(TEST_DETECTORS[0].model));
    });

    it("renders no links at all when neither model id matches", async () => {
      renderModelLoader({ selectedDetectorId: "", selectedClassifierId: "" });
      expect(await getDetectorInfoLink().all()).toHaveLength(0);
      expect(await getClassifierInfoLink().all()).toHaveLength(0);
    });

    it("renders no info links when both model lists are empty", async () => {
      renderModelLoader({
        detectors: [],
        classifiers: [],
        selectedDetectorId: "",
        selectedClassifierId: "",
      });
      expect(await getDetectorCombobox().all()).toHaveLength(1);
      expect(await getClassifierCombobox().all()).toHaveLength(1);
      expect(await getDetectorInfoLink().all()).toHaveLength(0);
      expect(await getClassifierInfoLink().all()).toHaveLength(0);
    });

    it("renders only the available model info link when one list is empty", async () => {
      renderModelLoader({
        detectors: [],
        classifiers: TEST_CLASSIFIERS,
        selectedDetectorId: "",
        selectedClassifierId: TEST_CLASSIFIERS[0].id,
      });
      expect(await getDetectorInfoLink().all()).toHaveLength(0);
      await expect
        .element(getClassifierInfoLink())
        .toHaveAttribute("href", huggingFaceUrl(TEST_CLASSIFIERS[0].model));
    });
  });

  describe("selection callbacks", () => {
    it("calls onSelectDetector with the new id when a detector option is chosen", async () => {
      const onSelectDetector = vi.fn();
      renderModelLoader({
        onSelectDetector,
        selectedDetectorId: TEST_DETECTORS[0].id,
      });
      await getDetectorCombobox().click();
      await page.getByRole("option", { name: TEST_DETECTORS[1].id }).click();
      expect(onSelectDetector).toHaveBeenCalledTimes(1);
      expect(onSelectDetector).toHaveBeenCalledWith(TEST_DETECTORS[1].id);
    });

    it("calls onSelectClassifier with the new id when a classifier option is chosen", async () => {
      const onSelectClassifier = vi.fn();
      renderModelLoader({
        onSelectClassifier,
        selectedClassifierId: TEST_CLASSIFIERS[0].id,
      });
      await getClassifierCombobox().click();
      await page.getByRole("option", { name: TEST_CLASSIFIERS[1].id }).click();
      expect(onSelectClassifier).toHaveBeenCalledTimes(1);
      expect(onSelectClassifier).toHaveBeenCalledWith(TEST_CLASSIFIERS[1].id);
    });
  });
});
