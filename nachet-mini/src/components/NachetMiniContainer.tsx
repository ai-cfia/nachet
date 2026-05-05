import { useEffect, useRef, useState, useCallback } from "react";
import type Webcam from "react-webcam";
import { useTranslation } from "react-i18next";
import { useWebcamDevices } from "@hooks/useWebcamDevices";
import { useVersionCheck } from "@hooks/useVersionCheck";
import { useWebcamStore } from "@stores/useWebcamStore";
import { useMetadataDefaultsStore } from "@stores/useMetadataDefaultsStore";
import { useImageStore } from "@stores/useImageStore";
import { useInferenceStore, resultKey } from "@stores/useInferenceStore";
import { useInference } from "@inference/useInference";
import { useBoxEditStore } from "@stores/useBoxEditStore";
import {
  DETECTOR_MODELS,
  CLASSIFIER_MODELS,
  DEFAULT_DETECTOR,
  DEFAULT_CLASSIFIER,
  buildModelConfig,
} from "@inference/models";
import { normalizeFileName } from "@common/validation";
import { computeSha256 } from "@common/hash";
import NachetMiniView from "@components/NachetMiniView";

const NachetMiniContainer = () => {
  const { t } = useTranslation("main");

  const {
    dialogOpen: versionDialogOpen,
    remoteVersion,
    closeDialog: closeVersionDialog,
  } = useVersionCheck();

  // Webcam
  const { devices, activeDeviceId } = useWebcamDevices();
  const setActiveDeviceId = useWebcamStore((s) => s.setActiveDeviceId);

  // Metadata defaults
  const metaDefaults = useMetadataDefaultsStore((s) => s.defaults);
  const metadataNotSet =
    !metaDefaults.deviceBrandId || !metaDefaults.deviceModelId;

  // Image store
  const images = useImageStore((s) => s.images);
  const currentIndex = useImageStore((s) => s.currentIndex);
  const addImage = useImageStore((s) => s.addImage);
  const removeImage = useImageStore((s) => s.removeImage);
  const setCurrentIndex = useImageStore((s) => s.setCurrentIndex);
  const clearImages = useImageStore((s) => s.clearImages);
  const getCurrentImage = useImageStore((s) => s.getCurrentImage);

  // Inference store
  const status = useInferenceStore((s) => s.status);
  const modelLoaded = useInferenceStore((s) => s.modelLoaded);
  const modelLoadProgress = useInferenceStore((s) => s.modelLoadProgress);
  const error = useInferenceStore((s) => s.error);
  const results = useInferenceStore((s) => s.results);
  const activeResultKey = useInferenceStore((s) => s.activeResultKey);
  const setActiveResultKey = useInferenceStore((s) => s.setActiveResultKey);
  const getResultsForImage = useInferenceStore((s) => s.getResultsForImage);
  const removeResultsForImage = useInferenceStore(
    (s) => s.removeResultsForImage,
  );
  const removeResult = useInferenceStore((s) => s.removeResult);
  const clearResults = useInferenceStore((s) => s.clearResults);
  const setError = useInferenceStore((s) => s.setError);

  const { loadModels, runInference, runClassifyOnly } = useInference();

  // Box edit store
  const isEditing = useBoxEditStore((s) => s.isEditing);
  const editedBoxes = useBoxEditStore((s) => s.editedBoxes);
  const isDrawingBox = useBoxEditStore((s) => s.isDrawing);
  const enterEditMode = useBoxEditStore((s) => s.enterEditMode);
  const exitEditMode = useBoxEditStore((s) => s.exitEditMode);
  const setIsDrawing = useBoxEditStore((s) => s.setIsDrawing);

  // Checked state (lifted from ImageGallery for export)
  const [checkedImages, setCheckedImages] = useState<Set<number>>(new Set());
  const [checkedResults, setCheckedResults] = useState<Set<string>>(new Set());

  // Local state
  const [uploadOpen, setUploadOpen] = useState(false);
  const [saveOpen, setSaveOpen] = useState(false);
  const [exportOpen, setExportOpen] = useState(false);
  const [isWebcamActive, setIsWebcamActive] = useState(true);
  const [webcamError, setWebcamError] = useState("");
  const webcamRef = useRef<Webcam | null>(null);
  const [selectedDetectorId, setSelectedDetectorId] = useState(
    DEFAULT_DETECTOR.id,
  );
  const [selectedClassifierId, setSelectedClassifierId] = useState(
    DEFAULT_CLASSIFIER.id,
  );
  const [switchTable, setSwitchTable] = useState(false);
  const [metadataOpen, setMetadataOpen] = useState(false);
  const [metadataMode, setMetadataMode] = useState<"defaults" | "image">(
    "defaults",
  );
  const [metadataImageIndex, setMetadataImageIndex] = useState<
    number | undefined
  >(undefined);

  const currentImage = getCurrentImage();
  const currentResult = activeResultKey
    ? (results.get(activeResultKey) ?? null)
    : null;

  const handleImageLoaded = async (
    src: string,
    dims: number[],
    fileName?: string,
  ) => {
    const name = fileName ? normalizeFileName(fileName) : undefined;
    const hash = await computeSha256(src);
    const added = addImage(src, dims, name, hash);
    if (!added) return;
    setActiveResultKey(null);
  };

  const handleCaptureFeed = async () => {
    const screenshot = webcamRef.current?.getScreenshot();
    if (!screenshot) return;

    const video = webcamRef.current?.video;
    const width = video?.videoWidth ?? 1920;
    const height = video?.videoHeight ?? 1080;

    const hash = await computeSha256(screenshot);
    const added = addImage(screenshot, [width, height], undefined, hash);
    if (!added) return;
    setActiveResultKey(null);
  };

  const handleWebcamError = (err: string | DOMException) => {
    const message = err instanceof DOMException ? err.message : String(err);
    setWebcamError(t("status.cameraError", { message }));
  };

  const handleLoadModel = () => {
    const detector = DETECTOR_MODELS.find((d) => d.id === selectedDetectorId);
    const classifier = CLASSIFIER_MODELS.find(
      (c) => c.id === selectedClassifierId,
    );
    if (!detector || !classifier) return;
    setError(null);
    loadModels(buildModelConfig(detector, classifier));
  };

  // Auto-load models on startup and whenever selection changes
  useEffect(() => {
    handleLoadModel();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDetectorId, selectedClassifierId]);

  const handleRunInference = () => {
    if (!currentImage) return;
    runInference(currentImage.src, currentImage.index);
  };

  const handleEnterEditMode = () => {
    if (!activeResultKey || !currentResult) return;
    enterEditMode(activeResultKey, currentResult.boxes);
  };

  const handleDiscardEdits = () => {
    exitEditMode();
  };

  const handleClassifyEdited = () => {
    if (!currentImage || editedBoxes.length === 0) return;
    const detector = DETECTOR_MODELS.find((d) => d.id === selectedDetectorId);
    const classifier = CLASSIFIER_MODELS.find(
      (c) => c.id === selectedClassifierId,
    );
    if (!detector || !classifier) return;
    const configId = `${detector.id}+${classifier.id}`;
    const editedConfigId = `${configId}:edited-${Date.now()}`;
    const boxes = editedBoxes.map((b) => ({
      topX: b.topX,
      topY: b.topY,
      bottomX: b.bottomX,
      bottomY: b.bottomY,
    }));
    exitEditMode();
    runClassifyOnly(
      currentImage.src,
      currentImage.index,
      boxes,
      editedConfigId,
    );
  };

  const handleEditMetadata = useCallback((index: number) => {
    setMetadataMode("image");
    setMetadataImageIndex(index);
    setMetadataOpen(true);
  }, []);

  const handleOpenMetadataDefaults = useCallback(() => {
    setMetadataMode("defaults");
    setMetadataImageIndex(undefined);
    setMetadataOpen(true);
  }, []);

  const handleCloseMetadata = useCallback(() => {
    setMetadataOpen(false);
  }, []);

  const handleClearImages = () => {
    clearImages();
    clearResults();
    setCheckedImages(new Set());
    setCheckedResults(new Set());
  };

  const handleSelectImage = useCallback(
    (index: number) => {
      setCurrentIndex(index);
      const imageResults = getResultsForImage(index);
      if (imageResults.length > 0) {
        const latest = imageResults[imageResults.length - 1];
        setActiveResultKey(resultKey(index, latest.modelConfigId));
      } else {
        setActiveResultKey(null);
      }
    },
    [setCurrentIndex, getResultsForImage, setActiveResultKey],
  );

  const handleSelectResult = useCallback(
    (key: string) => {
      setActiveResultKey(key);
      const imageIndex = parseInt(key.split(":")[0], 10);
      if (!isNaN(imageIndex)) {
        setCurrentIndex(imageIndex);
      }
    },
    [setActiveResultKey, setCurrentIndex],
  );

  const handleRemoveImage = useCallback(
    (index: number) => {
      removeResultsForImage(index);
      removeImage(index);
      setCheckedImages((prev) => {
        const next = new Set(prev);
        next.delete(index);
        return next;
      });
      // Remove any checked results for this image
      setCheckedResults((prev) => {
        const prefix = `${index}:`;
        const next = new Set(prev);
        for (const key of prev) {
          if (key.startsWith(prefix)) next.delete(key);
        }
        return next;
      });
    },
    [removeImage, removeResultsForImage],
  );

  const handleRemoveResult = useCallback(
    (key: string) => {
      removeResult(key);
    },
    [removeResult],
  );

  const handleExportComplete = useCallback(() => {
    setCheckedImages(new Set());
    setCheckedResults(new Set());
  }, []);

  const isInferring = status === "detecting" || status === "classifying";
  const isLoading = status === "loading-model";
  const canRunInference =
    !isWebcamActive &&
    !!currentImage &&
    modelLoaded &&
    !isInferring &&
    !isEditing;
  const canEditBoxes =
    !isWebcamActive && !!currentResult && !isInferring && !isEditing;
  const canClassifyEdited =
    isEditing && editedBoxes.length > 0 && modelLoaded && !isInferring;

  const statusText = (() => {
    if (webcamError && isWebcamActive) return webcamError;
    if (error) return t("status.error", { error });
    if (status === "loading-model") return t("status.loadingModel");
    if (status === "detecting") return t("status.detecting");
    if (status === "classifying") return t("status.classifying");
    if (status === "complete") return t("status.inferenceComplete");
    if (modelLoaded) return t("status.modelReady");
    return t("status.noModelLoaded");
  })();

  return (
    <NachetMiniView
      devices={devices}
      activeDeviceId={activeDeviceId}
      setActiveDeviceId={setActiveDeviceId}
      isWebcamActive={isWebcamActive}
      setIsWebcamActive={setIsWebcamActive}
      webcamRef={webcamRef}
      webcamError={webcamError}
      setWebcamError={setWebcamError}
      onWebcamError={handleWebcamError}
      onCaptureFeed={handleCaptureFeed}
      images={images}
      currentIndex={currentIndex}
      currentImage={currentImage}
      currentResult={currentResult}
      activeResultKey={activeResultKey}
      getResultsForImage={getResultsForImage}
      checkedImages={checkedImages}
      checkedResults={checkedResults}
      setCheckedImages={setCheckedImages}
      setCheckedResults={setCheckedResults}
      metadataNotSet={metadataNotSet}
      metadataOpen={metadataOpen}
      metadataMode={metadataMode}
      metadataImageIndex={metadataImageIndex}
      onOpenMetadataDefaults={handleOpenMetadataDefaults}
      onCloseMetadata={handleCloseMetadata}
      onEditMetadata={handleEditMetadata}
      selectedDetectorId={selectedDetectorId}
      selectedClassifierId={selectedClassifierId}
      setSelectedDetectorId={setSelectedDetectorId}
      setSelectedClassifierId={setSelectedClassifierId}
      isEditing={isEditing}
      isDrawingBox={isDrawingBox}
      setIsDrawing={setIsDrawing}
      onEnterEditMode={handleEnterEditMode}
      onDiscardEdits={handleDiscardEdits}
      onClassifyEdited={handleClassifyEdited}
      onRunInference={handleRunInference}
      canRunInference={canRunInference}
      canEditBoxes={canEditBoxes}
      canClassifyEdited={canClassifyEdited}
      isLoading={isLoading}
      modelLoadProgress={modelLoadProgress}
      onSelectImage={handleSelectImage}
      onSelectResult={handleSelectResult}
      onRemoveImage={handleRemoveImage}
      onRemoveResult={handleRemoveResult}
      onClearImages={handleClearImages}
      uploadOpen={uploadOpen}
      setUploadOpen={setUploadOpen}
      onImageLoaded={handleImageLoaded}
      saveOpen={saveOpen}
      setSaveOpen={setSaveOpen}
      exportOpen={exportOpen}
      setExportOpen={setExportOpen}
      onExportComplete={handleExportComplete}
      versionDialogOpen={versionDialogOpen}
      remoteVersion={remoteVersion}
      onCloseVersionDialog={closeVersionDialog}
      statusText={statusText}
      isError={!!(error || webcamError)}
      switchTable={switchTable}
      setSwitchTable={setSwitchTable}
    />
  );
};

export { NachetMiniContainer as NachetMini };
