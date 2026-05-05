import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, cleanup, act, waitFor } from "@testing-library/react";
import { I18nextProvider } from "react-i18next";
import i18n from "../../i18n";
import enMain from "../../locales/en/main";
import { useImageStore } from "@stores/useImageStore";
import { useInferenceStore, resultKey } from "@stores/useInferenceStore";
import { useBoxEditStore } from "@stores/useBoxEditStore";
import { useWebcamStore } from "@stores/useWebcamStore";
import { useMetadataDefaultsStore } from "@stores/useMetadataDefaultsStore";
import {
  DEFAULT_DETECTOR,
  DEFAULT_CLASSIFIER,
  DETECTOR_MODELS,
  CLASSIFIER_MODELS,
  buildModelConfig,
} from "@inference/models";
import type { Images, InferenceBox, InferenceResult } from "@common/types";
import type { NachetMiniViewProps } from "../NachetMiniView";
import { NachetMini } from "../NachetMiniContainer";

const {
  mockLoadModels,
  mockRunInference,
  mockRunClassifyOnly,
  mockUseVersionCheck,
  mockUseWebcamDevices,
  mockComputeSha256,
  viewPropsRef,
} = vi.hoisted(() => ({
  mockLoadModels: vi.fn(),
  mockRunInference: vi.fn(),
  mockRunClassifyOnly: vi.fn(),
  mockUseVersionCheck: vi.fn(),
  mockUseWebcamDevices: vi.fn(),
  mockComputeSha256: vi.fn(),
  viewPropsRef: { current: null as { props: NachetMiniViewProps } | null },
}));

vi.mock("@inference/useInference", () => ({
  useInference: () => ({
    loadModels: mockLoadModels,
    runInference: mockRunInference,
    runClassifyOnly: mockRunClassifyOnly,
  }),
}));

vi.mock("@hooks/useVersionCheck", () => ({
  useVersionCheck: () => mockUseVersionCheck(),
}));

vi.mock("@hooks/useWebcamDevices", () => ({
  useWebcamDevices: () => mockUseWebcamDevices(),
}));

vi.mock("@common/hash", () => ({
  computeSha256: mockComputeSha256,
}));

vi.mock("@components/NachetMiniView", () => ({
  default: (props: NachetMiniViewProps) => {
    viewPropsRef.current = { props };
    return <div data-testid="view" />;
  },
}));

const getProps = (): NachetMiniViewProps => {
  if (!viewPropsRef.current) throw new Error("View not rendered");
  return viewPropsRef.current.props;
};

const renderContainer = () =>
  render(
    <I18nextProvider i18n={i18n}>
      <NachetMini />
    </I18nextProvider>,
  );

const waitForModelLoadAttempt = async () => {
  await waitFor(() => expect(mockLoadModels).toHaveBeenCalled());
};

const makeResult = (
  overrides: Partial<InferenceResult> = {},
): InferenceResult => ({
  scores: [],
  classifications: [],
  boxes: [],
  topN: [],
  overlapping: [],
  overlappingIndices: [],
  labelOccurrence: {},
  totalBoxes: 0,
  models: [],
  completedAt: "2024-06-15T10:30:45Z",
  isActive: true,
  minBoxSize: 10,
  ...overrides,
});

const makeBox = (overrides: Partial<InferenceBox> = {}): InferenceBox => ({
  inferenceId: "inf-1",
  boxId: "box-1",
  classId: "class-1",
  label: "wheat",
  isVerified: false,
  bboxSource: "model",
  topX: 10,
  topY: 20,
  bottomX: 110,
  bottomY: 220,
  ...overrides,
});

const makeImage = (overrides: Partial<Images> = {}): Images => ({
  index: 0,
  src: "x",
  imageDims: [1, 1],
  metadata: {
    imageName: "x.png",
    deviceBrandId: "",
    deviceModelId: "",
    deviceLensId: "",
    trayCode: "",
    description: "",
  },
  sha256: "h",
  ...overrides,
});

const getAlternateDetector = () => {
  const detector = DETECTOR_MODELS.find((d) => d.id !== DEFAULT_DETECTOR.id);
  expect(detector).toBeDefined();
  return detector!;
};

const getAlternateClassifier = () => {
  const classifier = CLASSIFIER_MODELS.find(
    (c) => c.id !== DEFAULT_CLASSIFIER.id,
  );
  expect(classifier).toBeDefined();
  return classifier!;
};

const setMetadataDefaults = (
  overrides: Partial<{
    deviceBrandId: string;
    deviceModelId: string;
    namePrefix: string;
  }> = {},
) => {
  useMetadataDefaultsStore.setState({
    defaults: {
      namePrefix: "image",
      deviceBrandId: "brand-1",
      deviceModelId: "model-1",
      deviceLensId: "",
      trayCode: "",
      description: "",
      ...overrides,
    },
  });
};

describe("NachetMiniContainer", () => {
  beforeEach(async () => {
    localStorage.clear();
    await i18n.changeLanguage("en");

    // Reset stores
    useImageStore.setState({ images: [], currentIndex: 0 });
    useInferenceStore.setState({
      results: new Map(),
      activeResultKey: null,
      status: "idle",
      modelLoaded: false,
      modelLoadProgress: null,
      error: null,
    });
    useBoxEditStore.getState().exitEditMode();
    useWebcamStore.setState({ devices: [], activeDeviceId: undefined });
    useMetadataDefaultsStore.getState().clearDefaults();

    // Reset mocks
    mockLoadModels.mockReset();
    mockRunInference.mockReset();
    mockRunClassifyOnly.mockReset();
    mockUseVersionCheck.mockReset();
    mockUseWebcamDevices.mockReset();
    mockComputeSha256.mockReset();

    mockUseVersionCheck.mockReturnValue({
      dialogOpen: false,
      remoteVersion: null,
      closeDialog: vi.fn(),
    });
    mockUseWebcamDevices.mockReturnValue({
      devices: [],
      activeDeviceId: undefined,
    });
    mockComputeSha256.mockResolvedValue("hash-default");

    viewPropsRef.current = null;
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  describe("mount", () => {
    it("renders NachetMiniView", () => {
      renderContainer();
      expect(viewPropsRef.current).not.toBeNull();
    });

    it("auto-loads default model config on mount", async () => {
      renderContainer();
      await waitForModelLoadAttempt();
      expect(mockLoadModels).toHaveBeenCalledTimes(1);
      expect(mockLoadModels).toHaveBeenCalledWith(
        buildModelConfig(DEFAULT_DETECTOR, DEFAULT_CLASSIFIER),
      );
    });

    it("passes default selected model ids to the view", () => {
      renderContainer();
      expect(getProps().selectedDetectorId).toBe(DEFAULT_DETECTOR.id);
      expect(getProps().selectedClassifierId).toBe(DEFAULT_CLASSIFIER.id);
    });

    it("starts with the webcam active by default", () => {
      renderContainer();
      expect(getProps().isWebcamActive).toBe(true);
    });

    it("forwards version check state to the view", () => {
      const closeDialog = vi.fn();
      mockUseVersionCheck.mockReturnValue({
        dialogOpen: true,
        remoteVersion: "9.9.9",
        closeDialog,
      });
      renderContainer();
      expect(getProps().versionDialogOpen).toBe(true);
      expect(getProps().remoteVersion).toBe("9.9.9");
      getProps().onCloseVersionDialog();
      expect(closeDialog).toHaveBeenCalledTimes(1);
    });

    it("forwards webcam device data to the view", () => {
      const devices = [
        { deviceId: "cam-1", label: "Cam 1" } as MediaDeviceInfo,
      ];
      mockUseWebcamDevices.mockReturnValue({
        devices,
        activeDeviceId: "cam-1",
      });
      renderContainer();
      expect(getProps().devices).toEqual(devices);
      expect(getProps().activeDeviceId).toBe("cam-1");
    });

    it("updates the active webcam device through the forwarded setter", () => {
      renderContainer();
      act(() => {
        getProps().setActiveDeviceId("cam-2");
      });
      expect(useWebcamStore.getState().activeDeviceId).toBe("cam-2");
    });
  });

  describe("metadata defaults flag", () => {
    it("reports metadataNotSet=true when brand or model is missing", () => {
      renderContainer();
      expect(getProps().metadataNotSet).toBe(true);
    });

    it("reports metadataNotSet=false once both brand and model are set", async () => {
      renderContainer();
      await act(async () => {
        setMetadataDefaults();
      });
      expect(getProps().metadataNotSet).toBe(false);
    });
  });

  describe("model selection", () => {
    it("reloads models when the detector selection changes", async () => {
      renderContainer();
      await waitForModelLoadAttempt();
      mockLoadModels.mockClear();
      const otherDetector = getAlternateDetector();
      await act(async () => {
        getProps().setSelectedDetectorId(otherDetector.id);
      });
      expect(mockLoadModels).toHaveBeenCalledTimes(1);
      expect(mockLoadModels).toHaveBeenCalledWith(
        buildModelConfig(otherDetector, DEFAULT_CLASSIFIER),
      );
      expect(getProps().selectedDetectorId).toBe(otherDetector.id);
    });

    it("reloads models when the classifier selection changes", async () => {
      renderContainer();
      await waitForModelLoadAttempt();
      mockLoadModels.mockClear();
      const otherClassifier = getAlternateClassifier();
      await act(async () => {
        getProps().setSelectedClassifierId(otherClassifier.id);
      });
      expect(mockLoadModels).toHaveBeenCalledTimes(1);
      expect(mockLoadModels).toHaveBeenCalledWith(
        buildModelConfig(DEFAULT_DETECTOR, otherClassifier),
      );
      expect(getProps().selectedClassifierId).toBe(otherClassifier.id);
    });

    it("does not call loadModels when a non-existent id is selected", async () => {
      renderContainer();
      await waitForModelLoadAttempt();
      mockLoadModels.mockClear();
      await act(async () => {
        getProps().setSelectedDetectorId("does-not-exist");
      });
      expect(mockLoadModels).not.toHaveBeenCalled();
    });

    it("clears any inference error when reloading models", async () => {
      useInferenceStore.getState().setError("boom");
      renderContainer();
      await waitForModelLoadAttempt();
      expect(useInferenceStore.getState().error).toBeNull();
    });
  });

  describe("image upload", () => {
    it("computes the hash, normalizes the filename, and stores the image", async () => {
      mockComputeSha256.mockResolvedValueOnce("hash-1");
      renderContainer();
      await waitForModelLoadAttempt();
      await act(async () => {
        await getProps().onImageLoaded(
          "data:image/png;base64,abc",
          [800, 600],
          "My Photo!.png",
        );
      });
      expect(mockComputeSha256).toHaveBeenCalledWith(
        "data:image/png;base64,abc",
      );
      const images = useImageStore.getState().images;
      expect(images).toHaveLength(1);
      expect(images[0].metadata.imageName).toBe("My-Photo.png");
      expect(images[0].sha256).toBe("hash-1");
      expect(images[0].imageDims).toEqual([800, 600]);
    });

    it("clears the active result key after a new image is added", async () => {
      useInferenceStore.getState().setActiveResultKey("0:foo");
      renderContainer();
      await waitForModelLoadAttempt();
      await act(async () => {
        await getProps().onImageLoaded(
          "data:image/png;base64,abc",
          [10, 10],
          "x.png",
        );
      });
      expect(useInferenceStore.getState().activeResultKey).toBeNull();
    });

    it("does not clear the active result when the image is a duplicate", async () => {
      mockComputeSha256.mockResolvedValue("dup-hash");
      renderContainer();
      await waitForModelLoadAttempt();
      await act(async () => {
        await getProps().onImageLoaded(
          "data:image/png;base64,abc",
          [10, 10],
          "dup.png",
        );
      });
      useInferenceStore.getState().setActiveResultKey("0:something");
      await act(async () => {
        await getProps().onImageLoaded(
          "data:image/png;base64,abc",
          [10, 10],
          "dup.png",
        );
      });
      expect(useImageStore.getState().images).toHaveLength(1);
      expect(useInferenceStore.getState().activeResultKey).toBe("0:something");
    });
  });

  describe("webcam capture", () => {
    it("captures a screenshot and stores it as a new image", async () => {
      mockComputeSha256.mockResolvedValueOnce("cap-hash");
      renderContainer();
      await waitForModelLoadAttempt();
      const props = getProps();
      props.webcamRef.current = {
        getScreenshot: () => "data:image/png;base64,SHOT",
        video: { videoWidth: 1280, videoHeight: 720 },
      } as unknown as NonNullable<typeof props.webcamRef.current>;
      await act(async () => {
        await getProps().onCaptureFeed();
      });
      const images = useImageStore.getState().images;
      expect(images).toHaveLength(1);
      expect(images[0].src).toBe("data:image/png;base64,SHOT");
      expect(images[0].imageDims).toEqual([1280, 720]);
      expect(images[0].sha256).toBe("cap-hash");
    });

    it("falls back to default dims when the webcam video element is missing", async () => {
      renderContainer();
      await waitForModelLoadAttempt();
      const props = getProps();
      props.webcamRef.current = {
        getScreenshot: () => "data:image/png;base64,SHOT",
        video: null,
      } as unknown as NonNullable<typeof props.webcamRef.current>;
      await act(async () => {
        await getProps().onCaptureFeed();
      });
      const images = useImageStore.getState().images;
      expect(images[0].imageDims).toEqual([1920, 1080]);
    });

    it("does nothing when there is no webcam ref", async () => {
      renderContainer();
      await waitForModelLoadAttempt();
      await act(async () => {
        await getProps().onCaptureFeed();
      });
      expect(useImageStore.getState().images).toHaveLength(0);
      expect(mockComputeSha256).not.toHaveBeenCalled();
    });

    it("does nothing when the webcam returns no screenshot", async () => {
      renderContainer();
      await waitForModelLoadAttempt();
      const props = getProps();
      props.webcamRef.current = {
        getScreenshot: () => null,
      } as unknown as NonNullable<typeof props.webcamRef.current>;
      await act(async () => {
        await getProps().onCaptureFeed();
      });
      expect(useImageStore.getState().images).toHaveLength(0);
      expect(mockComputeSha256).not.toHaveBeenCalled();
    });
  });

  describe("webcam error", () => {
    it("formats DOMException messages into the camera error status", async () => {
      renderContainer();
      const err = new DOMException("permission denied", "NotAllowedError");
      await act(async () => {
        getProps().onWebcamError(err);
      });
      expect(getProps().webcamError).toBe(
        enMain.status.cameraError.replace("{{message}}", "permission denied"),
      );
      expect(getProps().isError).toBe(true);
    });

    it("formats string errors into the camera error status", async () => {
      renderContainer();
      await act(async () => {
        getProps().onWebcamError("nope");
      });
      expect(getProps().webcamError).toBe(
        enMain.status.cameraError.replace("{{message}}", "nope"),
      );
    });
  });

  describe("running inference", () => {
    it("does nothing when there is no current image", async () => {
      renderContainer();
      await waitForModelLoadAttempt();
      await act(async () => {
        getProps().onRunInference();
      });
      expect(mockRunInference).not.toHaveBeenCalled();
    });

    it("calls runInference with the current image's src and index", async () => {
      useImageStore.setState({
        images: [
          makeImage({
            index: 7,
            src: "data:image/png;base64,abc",
            imageDims: [10, 10],
          }),
        ],
        currentIndex: 7,
      });
      renderContainer();
      await waitForModelLoadAttempt();
      await act(async () => {
        getProps().onRunInference();
      });
      expect(mockRunInference).toHaveBeenCalledWith(
        "data:image/png;base64,abc",
        7,
      );
    });
  });

  describe("box edit mode", () => {
    it("does not enter edit mode when there is no active result", async () => {
      renderContainer();
      await waitForModelLoadAttempt();
      await act(async () => {
        getProps().onEnterEditMode();
      });
      expect(useBoxEditStore.getState().isEditing).toBe(false);
    });

    it("enters edit mode with the boxes from the active result", async () => {
      const boxes = [makeBox({ boxId: "b-1" }), makeBox({ boxId: "b-2" })];
      const result = makeResult({ boxes, totalBoxes: 2 });
      useInferenceStore.getState().setResult(0, "model-a", result);
      useInferenceStore.getState().setActiveResultKey(resultKey(0, "model-a"));

      renderContainer();
      await waitForModelLoadAttempt();
      await act(async () => {
        getProps().onEnterEditMode();
      });
      const state = useBoxEditStore.getState();
      expect(state.isEditing).toBe(true);
      expect(state.editedBoxes).toHaveLength(2);
      expect(state.editedBoxes[0]).not.toBe(boxes[0]);
      expect(state.editedBoxes[0].boxId).toBe("b-1");
      expect(state.sourceResultKey).toBe(resultKey(0, "model-a"));
    });

    it("exits edit mode on discard", async () => {
      useBoxEditStore.getState().enterEditMode("k", [makeBox()]);
      renderContainer();
      await waitForModelLoadAttempt();
      await act(async () => {
        getProps().onDiscardEdits();
      });
      expect(useBoxEditStore.getState().isEditing).toBe(false);
    });

    it("classifies edited boxes and exits edit mode", async () => {
      vi.spyOn(Date, "now").mockReturnValue(1234567890);
      useImageStore.setState({
        images: [
          makeImage({
            index: 3,
            src: "data:image/png;base64,IMG",
            imageDims: [10, 10],
          }),
        ],
        currentIndex: 3,
      });
      const editedBoxes = [
        makeBox({ topX: 1, topY: 2, bottomX: 3, bottomY: 4 }),
      ];
      useBoxEditStore.getState().enterEditMode("0:foo", editedBoxes);

      renderContainer();
      await waitForModelLoadAttempt();
      await act(async () => {
        getProps().onClassifyEdited();
      });

      expect(useBoxEditStore.getState().isEditing).toBe(false);
      expect(mockRunClassifyOnly).toHaveBeenCalledTimes(1);
      const call = mockRunClassifyOnly.mock.calls[0];
      expect(call[0]).toBe("data:image/png;base64,IMG");
      expect(call[1]).toBe(3);
      expect(call[2]).toEqual([{ topX: 1, topY: 2, bottomX: 3, bottomY: 4 }]);
      expect(call[3]).toBe(
        `${DEFAULT_DETECTOR.id}+${DEFAULT_CLASSIFIER.id}:edited-1234567890`,
      );
    });

    it("does not classify when there are no edited boxes", async () => {
      useImageStore.setState({
        images: [makeImage()],
        currentIndex: 0,
      });
      useBoxEditStore.getState().enterEditMode("k", []);
      renderContainer();
      await waitForModelLoadAttempt();
      await act(async () => {
        getProps().onClassifyEdited();
      });
      expect(mockRunClassifyOnly).not.toHaveBeenCalled();
    });
  });

  describe("metadata dialog", () => {
    it("opens in 'defaults' mode with no image index", async () => {
      renderContainer();
      await act(async () => {
        getProps().onOpenMetadataDefaults();
      });
      expect(getProps().metadataOpen).toBe(true);
      expect(getProps().metadataMode).toBe("defaults");
      expect(getProps().metadataImageIndex).toBeUndefined();
    });

    it("opens in 'image' mode with the selected image index", async () => {
      renderContainer();
      await act(async () => {
        getProps().onEditMetadata(2);
      });
      expect(getProps().metadataOpen).toBe(true);
      expect(getProps().metadataMode).toBe("image");
      expect(getProps().metadataImageIndex).toBe(2);
    });

    it("closes the metadata dialog", async () => {
      renderContainer();
      await act(async () => {
        getProps().onOpenMetadataDefaults();
      });
      await act(async () => {
        getProps().onCloseMetadata();
      });
      expect(getProps().metadataOpen).toBe(false);
    });
  });

  describe("view state setters", () => {
    it("toggles upload, save, export, and result table view state", async () => {
      renderContainer();
      await waitForModelLoadAttempt();

      await act(async () => {
        getProps().setUploadOpen(true);
        getProps().setSaveOpen(true);
        getProps().setExportOpen(true);
        getProps().setSwitchTable(true);
      });

      expect(getProps().uploadOpen).toBe(true);
      expect(getProps().saveOpen).toBe(true);
      expect(getProps().exportOpen).toBe(true);
      expect(getProps().switchTable).toBe(true);
    });
  });

  describe("clear images", () => {
    it("clears images, results, and checked sets", async () => {
      useImageStore.setState({
        images: [makeImage()],
        currentIndex: 0,
      });
      useInferenceStore.getState().setResult(0, "m", makeResult());
      renderContainer();
      await waitForModelLoadAttempt();
      await act(async () => {
        getProps().setCheckedImages(new Set([0]));
        getProps().setCheckedResults(new Set(["0:m"]));
      });
      await act(async () => {
        getProps().onClearImages();
      });
      expect(useImageStore.getState().images).toHaveLength(0);
      expect(useInferenceStore.getState().results.size).toBe(0);
      expect(getProps().checkedImages.size).toBe(0);
      expect(getProps().checkedResults.size).toBe(0);
    });
  });

  describe("select image", () => {
    it("sets currentIndex and activates the latest result for that image", async () => {
      useInferenceStore
        .getState()
        .setResult(0, "model-a", makeResult({ totalBoxes: 1 }));
      useInferenceStore
        .getState()
        .setResult(0, "model-b", makeResult({ totalBoxes: 2 }));
      renderContainer();
      await waitForModelLoadAttempt();
      await act(async () => {
        getProps().onSelectImage(0);
      });
      expect(useImageStore.getState().currentIndex).toBe(0);
      expect(useInferenceStore.getState().activeResultKey).toBe(
        resultKey(0, "model-b"),
      );
    });

    it("clears the active result key when the image has no results", async () => {
      useInferenceStore.getState().setActiveResultKey("0:something");
      renderContainer();
      await waitForModelLoadAttempt();
      await act(async () => {
        getProps().onSelectImage(5);
      });
      expect(useImageStore.getState().currentIndex).toBe(5);
      expect(useInferenceStore.getState().activeResultKey).toBeNull();
    });
  });

  describe("select result", () => {
    it("sets the active result key and parses the image index from the key", async () => {
      renderContainer();
      await waitForModelLoadAttempt();
      await act(async () => {
        getProps().onSelectResult("4:model-a:1234");
      });
      expect(useInferenceStore.getState().activeResultKey).toBe(
        "4:model-a:1234",
      );
      expect(useImageStore.getState().currentIndex).toBe(4);
    });

    it("does not change currentIndex when the key prefix is not numeric", async () => {
      useImageStore.setState({ images: [], currentIndex: 9 });
      renderContainer();
      await waitForModelLoadAttempt();
      await act(async () => {
        getProps().onSelectResult("abc:model");
      });
      expect(useInferenceStore.getState().activeResultKey).toBe("abc:model");
      expect(useImageStore.getState().currentIndex).toBe(9);
    });
  });

  describe("remove image / result", () => {
    it("removes the image, its results, and any related checked entries", async () => {
      useImageStore.setState({
        images: [makeImage({ index: 1 })],
        currentIndex: 1,
      });
      useInferenceStore.getState().setResult(1, "m-a", makeResult());
      useInferenceStore.getState().setResult(1, "m-b", makeResult());

      renderContainer();
      await waitForModelLoadAttempt();
      await act(async () => {
        getProps().setCheckedImages(new Set([1]));
        getProps().setCheckedResults(new Set(["1:m-a", "1:m-b", "2:other"]));
      });
      await act(async () => {
        getProps().onRemoveImage(1);
      });

      expect(useImageStore.getState().images).toHaveLength(0);
      expect(useInferenceStore.getState().results.size).toBe(0);
      expect(getProps().checkedImages.has(1)).toBe(false);
      const remainingChecked = Array.from(getProps().checkedResults);
      expect(remainingChecked).toEqual(["2:other"]);
    });

    it("removes a single result via onRemoveResult", async () => {
      useInferenceStore.getState().setResult(0, "m-a", makeResult());
      useInferenceStore.getState().setResult(0, "m-b", makeResult());
      renderContainer();
      await waitForModelLoadAttempt();
      await act(async () => {
        getProps().onRemoveResult(resultKey(0, "m-a"));
      });
      expect(
        useInferenceStore.getState().results.has(resultKey(0, "m-a")),
      ).toBe(false);
      expect(
        useInferenceStore.getState().results.has(resultKey(0, "m-b")),
      ).toBe(true);
    });
  });

  describe("export complete", () => {
    it("clears checked images and checked results", async () => {
      renderContainer();
      await waitForModelLoadAttempt();
      await act(async () => {
        getProps().setCheckedImages(new Set([0, 1]));
        getProps().setCheckedResults(new Set(["0:m"]));
      });
      await act(async () => {
        getProps().onExportComplete();
      });
      expect(getProps().checkedImages.size).toBe(0);
      expect(getProps().checkedResults.size).toBe(0);
    });
  });

  describe("derived flags", () => {
    const addOneImage = () => {
      useImageStore.setState({
        images: [makeImage({ imageDims: [10, 10] })],
        currentIndex: 0,
      });
    };

    it("canRunInference is false while the webcam is active", async () => {
      addOneImage();
      useInferenceStore.getState().setModelLoaded(true);
      renderContainer();
      await waitForModelLoadAttempt();
      expect(getProps().isWebcamActive).toBe(true);
      expect(getProps().canRunInference).toBe(false);
    });

    it("canRunInference becomes true with image + model + webcam off + idle + not editing", async () => {
      addOneImage();
      useInferenceStore.getState().setModelLoaded(true);
      renderContainer();
      await waitForModelLoadAttempt();
      await act(async () => {
        getProps().setIsWebcamActive(false);
      });
      expect(getProps().canRunInference).toBe(true);
    });

    it("canRunInference is false while inference is running", async () => {
      addOneImage();
      useInferenceStore.getState().setModelLoaded(true);
      useInferenceStore.getState().setStatus("detecting");
      renderContainer();
      await waitForModelLoadAttempt();
      await act(async () => {
        getProps().setIsWebcamActive(false);
      });
      expect(getProps().canRunInference).toBe(false);
    });

    it("canEditBoxes is true when there is an active result and not inferring", async () => {
      useInferenceStore.getState().setResult(0, "m", makeResult());
      useInferenceStore.getState().setActiveResultKey(resultKey(0, "m"));
      renderContainer();
      await waitForModelLoadAttempt();
      await act(async () => {
        getProps().setIsWebcamActive(false);
      });
      expect(getProps().canEditBoxes).toBe(true);
    });

    it("canEditBoxes is false while editing", async () => {
      useInferenceStore.getState().setResult(0, "m", makeResult());
      useInferenceStore.getState().setActiveResultKey(resultKey(0, "m"));
      useBoxEditStore.getState().enterEditMode("0:m", []);
      renderContainer();
      await waitForModelLoadAttempt();
      await act(async () => {
        getProps().setIsWebcamActive(false);
      });
      expect(getProps().canEditBoxes).toBe(false);
    });

    it("canClassifyEdited requires editing + boxes + model loaded + not inferring", async () => {
      useInferenceStore.getState().setModelLoaded(true);
      useBoxEditStore.getState().enterEditMode("k", [makeBox()]);
      renderContainer();
      await waitForModelLoadAttempt();
      expect(getProps().canClassifyEdited).toBe(true);
    });

    it("canClassifyEdited is false when no boxes are edited", async () => {
      useInferenceStore.getState().setModelLoaded(true);
      useBoxEditStore.getState().enterEditMode("k", []);
      renderContainer();
      await waitForModelLoadAttempt();
      expect(getProps().canClassifyEdited).toBe(false);
    });

    it("isLoading mirrors the loading-model status", async () => {
      useInferenceStore.getState().setStatus("loading-model");
      renderContainer();
      await waitForModelLoadAttempt();
      expect(getProps().isLoading).toBe(true);
    });
  });

  describe("status text", () => {
    it("shows 'no model loaded' by default", async () => {
      renderContainer();
      await waitForModelLoadAttempt();
      expect(getProps().statusText).toBe(enMain.status.noModelLoaded);
    });

    it("shows 'model ready' once the model is loaded", async () => {
      useInferenceStore.getState().setModelLoaded(true);
      renderContainer();
      await waitForModelLoadAttempt();
      expect(getProps().statusText).toBe(enMain.status.modelReady);
    });

    it("shows the loading status while loading the model", async () => {
      useInferenceStore.getState().setStatus("loading-model");
      renderContainer();
      await waitForModelLoadAttempt();
      expect(getProps().statusText).toBe(enMain.status.loadingModel);
    });

    it("shows the detecting status while detecting", async () => {
      useInferenceStore.getState().setStatus("detecting");
      renderContainer();
      await waitForModelLoadAttempt();
      expect(getProps().statusText).toBe(enMain.status.detecting);
    });

    it("shows the classifying status while classifying", async () => {
      useInferenceStore.getState().setStatus("classifying");
      renderContainer();
      await waitForModelLoadAttempt();
      expect(getProps().statusText).toBe(enMain.status.classifying);
    });

    it("shows 'inference complete' when complete", async () => {
      useInferenceStore.getState().setStatus("complete");
      renderContainer();
      await waitForModelLoadAttempt();
      expect(getProps().statusText).toBe(enMain.status.inferenceComplete);
    });

    it("renders the formatted error status when an inference error is set", async () => {
      renderContainer();
      await waitForModelLoadAttempt();
      await act(async () => {
        useInferenceStore.getState().setError("kaboom");
      });
      expect(getProps().statusText).toBe(
        enMain.status.error.replace("{{error}}", "kaboom"),
      );
      expect(getProps().isError).toBe(true);
    });

    it("prefers the webcam error when the webcam is active", async () => {
      renderContainer();
      await act(async () => {
        getProps().onWebcamError("denied");
      });
      expect(getProps().statusText).toBe(
        enMain.status.cameraError.replace("{{message}}", "denied"),
      );
    });

    it("does not show the webcam error once the webcam is turned off", async () => {
      renderContainer();
      await act(async () => {
        getProps().onWebcamError("denied");
      });
      await act(async () => {
        getProps().setIsWebcamActive(false);
      });
      expect(getProps().statusText).not.toContain("denied");
    });
  });
});
