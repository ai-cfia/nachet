import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, cleanup } from "@testing-library/react";
import { page } from "vitest/browser";
import { I18nextProvider } from "react-i18next";
import i18n from "../../i18n";
import enMain from "../../locales/en/main";
import { DEFAULT_CLASSIFIER, DEFAULT_DETECTOR } from "@inference/models";
import type { Images, InferenceResult } from "@common/types";
import NachetMiniView, { type NachetMiniViewProps } from "../NachetMiniView";

vi.mock("@components/Navbar", () => ({
  default: () => <div data-testid="navbar" />,
}));

vi.mock("@components/AppBar", () => ({
  default: () => <div data-testid="app-bar" />,
}));

vi.mock("@components/WebcamCapture", () => ({
  default: ({
    onUserMediaError,
  }: {
    onUserMediaError: (err: string) => void;
  }) => (
    <button
      data-testid="webcam-capture"
      onClick={() => onUserMediaError("denied")}
    >
      webcam
    </button>
  ),
}));

vi.mock("@components/ImageViewer", () => ({
  default: ({ src }: { src?: string }) => (
    <div data-testid="image-viewer">{src ?? "no-image"}</div>
  ),
}));

vi.mock("@components/ImageGallery", () => ({
  default: ({
    images,
    onSelectImage,
    onSelectResult,
    onRemoveImage,
    onRemoveResult,
    onEditMetadata,
    onClear,
  }: {
    images: Images[];
    onSelectImage: (index: number) => void;
    onSelectResult: (key: string) => void;
    onRemoveImage: (index: number) => void;
    onRemoveResult: (key: string) => void;
    onEditMetadata: (index: number) => void;
    onClear: () => void;
  }) => (
    <div data-testid="image-gallery">
      <span data-testid="gallery-count">{images.length}</span>
      <button onClick={() => onSelectImage(1)}>select image</button>
      <button onClick={() => onSelectResult("1:model")}>select result</button>
      <button onClick={() => onRemoveImage(1)}>remove image</button>
      <button onClick={() => onRemoveResult("1:model")}>remove result</button>
      <button onClick={() => onEditMetadata(1)}>edit metadata</button>
      <button onClick={onClear}>clear images</button>
    </div>
  ),
}));

vi.mock("@components/ResultsTable", () => ({
  default: ({
    switchTable,
    onSwitchTableChange,
  }: {
    switchTable: boolean;
    onSwitchTableChange: (value: boolean) => void;
  }) => (
    <button
      data-testid="results-table"
      onClick={() => onSwitchTableChange(!switchTable)}
    >
      {switchTable ? "labels" : "classifications"}
    </button>
  ),
}));

vi.mock("@components/ModelLoader", () => ({
  default: ({
    onSelectDetector,
    onSelectClassifier,
    isLoading,
  }: {
    onSelectDetector: (id: string) => void;
    onSelectClassifier: (id: string) => void;
    isLoading: boolean;
  }) => (
    <div data-testid="model-loader">
      <span>{isLoading ? "loading" : "ready"}</span>
      <button onClick={() => onSelectDetector("detector-next")}>
        detector
      </button>
      <button onClick={() => onSelectClassifier("classifier-next")}>
        classifier
      </button>
    </div>
  ),
}));

vi.mock("@components/Footer", () => ({
  default: ({
    statusText,
    isError,
    isLoading,
    loadProgress,
  }: {
    statusText?: string;
    isError?: boolean;
    isLoading?: boolean;
    loadProgress?: { name: string; progress: number } | null;
  }) => (
    <div data-testid="footer" data-error={String(!!isError)}>
      {statusText}
      {isLoading && loadProgress
        ? ` ${loadProgress.name} ${loadProgress.progress}`
        : ""}
    </div>
  ),
}));

vi.mock("@components/ImageUpload", () => ({
  default: ({
    open,
    onClose,
    onImageLoaded,
  }: {
    open: boolean;
    onClose: () => void;
    onImageLoaded: (src: string, dims: number[], fileName?: string) => void;
  }) =>
    open ? (
      <div data-testid="image-upload">
        <button onClick={onClose}>close upload</button>
        <button
          onClick={() =>
            onImageLoaded("data:image/png;base64,x", [2, 3], "x.png")
          }
        >
          load image
        </button>
      </div>
    ) : null,
}));

vi.mock("@components/SaveDialog", () => ({
  default: ({ open, onClose }: { open: boolean; onClose: () => void }) =>
    open ? <button onClick={onClose}>close save</button> : null,
}));

vi.mock("@components/ExportDialog", () => ({
  default: ({
    open,
    onClose,
    onExportComplete,
  }: {
    open: boolean;
    onClose: () => void;
    onExportComplete: () => void;
  }) =>
    open ? (
      <div data-testid="export-dialog">
        <button onClick={onClose}>close export</button>
        <button onClick={onExportComplete}>export complete</button>
      </div>
    ) : null,
}));

vi.mock("@components/MetadataDialog", () => ({
  default: ({
    open,
    onClose,
    mode,
    imageIndex,
  }: {
    open: boolean;
    onClose: () => void;
    mode: string;
    imageIndex?: number;
  }) =>
    open ? (
      <button data-testid="metadata-dialog" onClick={onClose}>
        {mode}:{imageIndex ?? "none"}
      </button>
    ) : null,
}));

vi.mock("@components/VersionCheckDialog", () => ({
  default: ({
    open,
    remoteVersion,
    onClose,
  }: {
    open: boolean;
    remoteVersion: string | null;
    onClose: () => void;
  }) =>
    open ? (
      <button data-testid="version-dialog" onClick={onClose}>
        {remoteVersion}
      </button>
    ) : null,
}));

const makeImage = (overrides: Partial<Images> = {}): Images => ({
  index: 0,
  src: "data:image/png;base64,IMG",
  imageDims: [10, 10],
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

const makeProps = (
  overrides: Partial<NachetMiniViewProps> = {},
): NachetMiniViewProps => ({
  devices: [],
  activeDeviceId: undefined,
  setActiveDeviceId: vi.fn(),
  isWebcamActive: true,
  setIsWebcamActive: vi.fn(),
  webcamRef: { current: null },
  webcamError: "",
  setWebcamError: vi.fn(),
  onWebcamError: vi.fn(),
  onCaptureFeed: vi.fn(),
  images: [],
  currentIndex: 0,
  currentImage: undefined,
  currentResult: null,
  activeResultKey: null,
  getResultsForImage: vi.fn(() => []),
  checkedImages: new Set(),
  checkedResults: new Set(),
  setCheckedImages: vi.fn(),
  setCheckedResults: vi.fn(),
  metadataNotSet: false,
  metadataOpen: false,
  metadataMode: "defaults",
  metadataImageIndex: undefined,
  onOpenMetadataDefaults: vi.fn(),
  onCloseMetadata: vi.fn(),
  onEditMetadata: vi.fn(),
  selectedDetectorId: DEFAULT_DETECTOR.id,
  selectedClassifierId: DEFAULT_CLASSIFIER.id,
  setSelectedDetectorId: vi.fn(),
  setSelectedClassifierId: vi.fn(),
  isEditing: false,
  isDrawingBox: false,
  setIsDrawing: vi.fn(),
  onEnterEditMode: vi.fn(),
  onDiscardEdits: vi.fn(),
  onClassifyEdited: vi.fn(),
  onRunInference: vi.fn(),
  canRunInference: false,
  canEditBoxes: false,
  canClassifyEdited: false,
  isLoading: false,
  modelLoadProgress: null,
  onSelectImage: vi.fn(),
  onSelectResult: vi.fn(),
  onRemoveImage: vi.fn(),
  onRemoveResult: vi.fn(),
  onClearImages: vi.fn(),
  uploadOpen: false,
  setUploadOpen: vi.fn(),
  onImageLoaded: vi.fn(),
  saveOpen: false,
  setSaveOpen: vi.fn(),
  exportOpen: false,
  setExportOpen: vi.fn(),
  onExportComplete: vi.fn(),
  versionDialogOpen: false,
  remoteVersion: null,
  onCloseVersionDialog: vi.fn(),
  statusText: enMain.status.noModelLoaded,
  isError: false,
  switchTable: false,
  setSwitchTable: vi.fn(),
  ...overrides,
});

const renderView = (props: NachetMiniViewProps) =>
  render(
    <I18nextProvider i18n={i18n}>
      <NachetMiniView {...props} />
    </I18nextProvider>,
  );

describe("NachetMiniView", () => {
  beforeEach(async () => {
    localStorage.clear();
    await i18n.changeLanguage("en");
  });

  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("renders the webcam workspace and forwards toolbar actions", async () => {
    const props = makeProps({
      devices: [{ deviceId: "cam-1", label: "Camera 1" } as MediaDeviceInfo],
    });

    renderView(props);

    await expect.element(page.getByTestId("webcam-capture")).toBeVisible();
    await expect
      .element(page.getByTestId("footer"))
      .toHaveTextContent(enMain.status.noModelLoaded);

    await page
      .getByRole("button", { name: enMain.controls.meta, exact: true })
      .click();
    expect(props.onOpenMetadataDefaults).toHaveBeenCalledTimes(1);

    await page.getByRole("button", { name: enMain.controls.capture }).click();
    expect(props.onCaptureFeed).toHaveBeenCalledTimes(1);

    await page.getByRole("switch").click();
    expect(props.setWebcamError).toHaveBeenCalledWith("");
    expect(props.setIsWebcamActive).toHaveBeenCalledWith(false);

    await page.getByTestId("webcam-capture").click();
    expect(props.onWebcamError).toHaveBeenCalledWith("denied");
  });

  it("disables image-mode controls until metadata defaults are set", async () => {
    const props = makeProps({ metadataNotSet: true });

    renderView(props);

    await expect.element(page.getByRole("switch")).toBeDisabled();
    await expect
      .element(page.getByRole("button", { name: enMain.controls.upload }))
      .toBeDisabled();
    await expect
      .element(page.getByRole("button", { name: enMain.controls.export }))
      .toBeDisabled();
  });

  it("renders image mode and forwards primary image workflow actions", async () => {
    const props = makeProps({
      isWebcamActive: false,
      currentImage: makeImage(),
      currentResult: makeResult(),
      checkedImages: new Set([0]),
      canRunInference: true,
      canEditBoxes: true,
    });

    renderView(props);

    await expect
      .element(page.getByTestId("image-viewer"))
      .toHaveTextContent("data:image/png;base64,IMG");

    await page.getByRole("button", { name: enMain.controls.upload }).click();
    expect(props.setUploadOpen).toHaveBeenCalledWith(true);

    await page.getByRole("button", { name: enMain.controls.export }).click();
    expect(props.setExportOpen).toHaveBeenCalledWith(true);

    await page.getByRole("button", { name: enMain.controls.editBoxes }).click();
    expect(props.onEnterEditMode).toHaveBeenCalledTimes(1);

    await page
      .getByRole("button", { name: enMain.controls.runInference })
      .click();
    expect(props.onRunInference).toHaveBeenCalledTimes(1);
  });

  it("renders edit controls and uses identify to classify edited boxes", async () => {
    const props = makeProps({
      isWebcamActive: false,
      isEditing: true,
      isDrawingBox: false,
      canClassifyEdited: true,
    });

    renderView(props);

    await page.getByRole("button", { name: enMain.controls.addBox }).click();
    expect(props.setIsDrawing).toHaveBeenCalledWith(true);

    await page
      .getByRole("button", { name: enMain.controls.discardEdits })
      .click();
    expect(props.onDiscardEdits).toHaveBeenCalledTimes(1);

    await page
      .getByRole("button", { name: enMain.controls.runInference })
      .click();
    expect(props.onClassifyEdited).toHaveBeenCalledTimes(1);
    expect(props.onRunInference).not.toHaveBeenCalled();
  });

  it("forwards model, gallery, and results table callbacks", async () => {
    const props = makeProps({ images: [makeImage()], switchTable: false });

    renderView(props);

    await page.getByRole("button", { name: "detector" }).click();
    expect(props.setSelectedDetectorId).toHaveBeenCalledWith("detector-next");

    await page.getByRole("button", { name: "classifier" }).click();
    expect(props.setSelectedClassifierId).toHaveBeenCalledWith(
      "classifier-next",
    );

    await page.getByRole("button", { name: "select image" }).click();
    expect(props.onSelectImage).toHaveBeenCalledWith(1);

    await page.getByRole("button", { name: "select result" }).click();
    expect(props.onSelectResult).toHaveBeenCalledWith("1:model");

    await page.getByRole("button", { name: "remove image" }).click();
    expect(props.onRemoveImage).toHaveBeenCalledWith(1);

    await page.getByRole("button", { name: "remove result" }).click();
    expect(props.onRemoveResult).toHaveBeenCalledWith("1:model");

    await page.getByRole("button", { name: "edit metadata" }).click();
    expect(props.onEditMetadata).toHaveBeenCalledWith(1);

    await page.getByRole("button", { name: "clear images" }).click();
    expect(props.onClearImages).toHaveBeenCalledTimes(1);

    await page.getByTestId("results-table").click();
    expect(props.setSwitchTable).toHaveBeenCalledWith(true);
  });

  it("renders open dialogs and forwards their close/complete callbacks", async () => {
    const props = makeProps({
      uploadOpen: true,
      saveOpen: true,
      exportOpen: true,
      metadataOpen: true,
      metadataMode: "image",
      metadataImageIndex: 2,
      versionDialogOpen: true,
      remoteVersion: "9.9.9",
    });

    renderView(props);

    await expect.element(page.getByTestId("image-upload")).toBeVisible();
    await page.getByRole("button", { name: "load image" }).click();
    expect(props.onImageLoaded).toHaveBeenCalledWith(
      "data:image/png;base64,x",
      [2, 3],
      "x.png",
    );

    await page.getByRole("button", { name: "close upload" }).click();
    expect(props.setUploadOpen).toHaveBeenCalledWith(false);

    await page.getByRole("button", { name: "close save" }).click();
    expect(props.setSaveOpen).toHaveBeenCalledWith(false);

    await page.getByRole("button", { name: "close export" }).click();
    expect(props.setExportOpen).toHaveBeenCalledWith(false);

    await page.getByRole("button", { name: "export complete" }).click();
    expect(props.onExportComplete).toHaveBeenCalledTimes(1);

    await page.getByTestId("metadata-dialog").click();
    expect(props.onCloseMetadata).toHaveBeenCalledTimes(1);

    await page.getByTestId("version-dialog").click();
    expect(props.onCloseVersionDialog).toHaveBeenCalledTimes(1);
  });
});
