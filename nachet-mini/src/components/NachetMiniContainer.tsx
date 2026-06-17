import { useEffect, useRef, useState, useCallback } from "react";
import type Webcam from "react-webcam";
import { useTranslation } from "react-i18next";
import { useWebcamDevices } from "@hooks/useWebcamDevices";
import { useVersionCheck } from "@hooks/useVersionCheck";
import { useWebcamStore } from "@stores/useWebcamStore";
import { useMetadataDefaultsStore } from "@stores/useMetadataDefaultsStore";
import { useModelLoadConsentStore } from "@stores/useModelLoadConsentStore";
import { useImageStore } from "@stores/useImageStore";
import { useInferenceStore, resultKey } from "@stores/useInferenceStore";
import { useInference } from "@inference/useInference";
import { useBoxEditStore } from "@stores/useBoxEditStore";
import { useInferenceQueueStore } from "@stores/useInferenceQueueStore";
import {
  DETECTOR_MODELS,
  CLASSIFIER_MODELS,
  DEFAULT_DETECTOR,
  DEFAULT_CLASSIFIER,
  buildModelConfig,
} from "@inference/models";
import { normalizeFileName } from "@common/validation";
import { computeSha256 } from "@common/hash";
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
} from "@mui/material";
import NachetMiniView from "@components/NachetMiniView";

const NachetMiniContainer = () => {
  const { t } = useTranslation("main");

  const {
    dialogOpen: versionDialogOpen,
    remoteVersion,
    closeDialog: closeVersionDialog,
  } = useVersionCheck();

  // Webcam
  const { devices, activeDeviceId, requestDevices } = useWebcamDevices();
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

  const { loadModels, runInference, runClassifyOnly } =
    useInference(currentIndex);

  // Model load consent store
  const hasAcknowledgedModelLoadWarning = useModelLoadConsentStore(
    (s) => s.hasAcknowledgedModelLoadWarning,
  );
  const acknowledgeModelLoadWarning = useModelLoadConsentStore(
    (s) => s.acknowledgeModelLoadWarning,
  );

  // Inference queue store
  const enqueue = useInferenceQueueStore((s) => s.enqueue);
  const markProcessing = useInferenceQueueStore((s) => s.markProcessing);
  const markDone = useInferenceQueueStore((s) => s.markDone);
  const cancel = useInferenceQueueStore((s) => s.cancel);
  const nextPendingId = useInferenceQueueStore(
    (s) => s.queue.find((i) => i.status === "pending")?.id ?? null,
  );
  const [drainTick, setDrainTick] = useState(0);
  const clearCompleted = useInferenceQueueStore((s) => s.clearCompleted);
  const markDetectionDone = useInferenceQueueStore((s) => s.markDetectionDone);
  // ADD local dialog state
  const [modelLoadDialogOpen, setModelLoadDialogOpen] = useState(false);

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
  // Text prompt for text-promptable detectors (e.g. SAM3).
  // Ignored by closed-vocabulary detectors (RT-DETR, DETR) — those classify by
  // their trained labels regardless of what's typed here.
  const [detectorPrompt, setDetectorPrompt] = useState("seed");
  const selectedDetector = DETECTOR_MODELS.find(
    (d) => d.id === selectedDetectorId,
  );
  const detectorRequiresPrompt =
    selectedDetector?.kind === "text-promptable-segmentation";
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

  // When the user changes detector/classifier after models were already loaded,
  // mark them as unloaded so the next Identify click reloads the correct config.
  const prevDetectorId = useRef(selectedDetectorId);
  const prevClassifierId = useRef(selectedClassifierId);
  useEffect(() => {
    const detectorChanged = prevDetectorId.current !== selectedDetectorId;
    const classifierChanged = prevClassifierId.current !== selectedClassifierId;
    prevDetectorId.current = selectedDetectorId;
    prevClassifierId.current = selectedClassifierId;

    if ((detectorChanged || classifierChanged) && modelLoaded) {
      useInferenceStore.getState().setModelLoaded(false);
    }
  }, [selectedDetectorId, selectedClassifierId, modelLoaded]);

  const isInferring = status === "detecting" || status === "classifying";
  const handleRunInference = () => {
    if (!currentImage) return;

    const alreadyQueued = useInferenceQueueStore
      .getState()
      .queue.some(
        (i) =>
          i.imageIndex === currentImage.index &&
          (i.status === "pending" || i.status === "processing"),
      );

    if (alreadyQueued) return;

    enqueue({ imageSrc: currentImage.src, imageIndex: currentImage.index });

    if (!hasAcknowledgedModelLoadWarning) {
      setModelLoadDialogOpen(true);
      return;
    }

    if (!modelLoaded && !isLoading) {
      handleLoadModel();
    }
  };

  const startTimeRef = useRef<number | null>(null);
  const detectionStartRef = useRef<number | null>(null);
  const isFiringRef = useRef(false);

  // Fire the next pending item when conditions are met
  useEffect(() => {
    if (!modelLoaded || isInferring || !nextPendingId) return;
    if (isFiringRef.current) return;

    const state = useInferenceQueueStore.getState();
    const item = state.queue.find((i) => i.id === nextPendingId);
    if (!item || item.status !== "pending") return;

    const stillExists = images.some((img) => img.index === item.imageIndex);
    if (!stillExists) {
      cancel(item.id);
      return;
    }

    isFiringRef.current = true;
    markProcessing(item.id);
    startTimeRef.current = Date.now();
    detectionStartRef.current = Date.now();
    // Only forward the prompt when the detector actually consumes it. Closed-
    // vocabulary detectors (RT-DETR, DETR) ignore it; we pass null so the
    // worker logs stay clear.
    runInference(
      item.imageSrc,
      item.imageIndex,
      detectorRequiresPrompt ? detectorPrompt : null,
    );
  }, [modelLoaded, isInferring, nextPendingId, drainTick]); // eslint-disable-line react-hooks/exhaustive-deps

  const prevStatusRef = useRef<string>(status);

  useEffect(() => {
    const prev = prevStatusRef.current;
    prevStatusRef.current = status;

    if (prev === "detecting" && status === "classifying") {
      const processingItem = useInferenceQueueStore
        .getState()
        .queue.find((i) => i.status === "processing");
      if (!processingItem) return;

      const detectionDuration = detectionStartRef.current
        ? Date.now() - detectionStartRef.current
        : 0;

      // Read box count from the partial result stored in useInferenceStore
      const { results } = useInferenceStore.getState();
      let boxCount = 0;
      for (const [key, result] of results) {
        if (key.startsWith(`${processingItem.imageIndex}:`)) {
          boxCount = result.totalBoxes;
          break;
        }
      }

      markDetectionDone(processingItem.id, detectionDuration, boxCount);
    }
  }, [status]); // eslint-disable-line react-hooks/exhaustive-deps

  // When inference completes, mark the processing item as done
  useEffect(() => {
    if (isInferring) {
      if (status === "detecting") {
        detectionStartRef.current ??= Date.now();
      }
      startTimeRef.current ??= Date.now();
      return;
    }

    if (status === "complete") {
      const totalDuration = startTimeRef.current
        ? Date.now() - startTimeRef.current
        : 0;

      const processingItem = useInferenceQueueStore
        .getState()
        .queue.find((i) => i.status === "processing");

      if (processingItem) {
        // Classification duration = total - detection duration
        const detectionDuration =
          processingItem.detectionDoneAt && startTimeRef.current
            ? processingItem.detectionDoneAt - startTimeRef.current
            : 0;
        const classificationDuration = Math.max(
          0,
          totalDuration - detectionDuration,
        );
        markDone(processingItem.id, classificationDuration);
      } else if (totalDuration > 0) {
        useInferenceQueueStore
          .getState()
          .setLastInferenceDuration(totalDuration);
      }
      isFiringRef.current = false;
      clearCompleted();
      setTimeout(() => setDrainTick((n) => n + 1), 0);
      startTimeRef.current = null;
    }
  }, [status]); // eslint-disable-line react-hooks/exhaustive-deps

  const handleModelLoadDialogCancel = () => {
    setModelLoadDialogOpen(false);
    if (nextPendingId) cancel(nextPendingId);
  };

  const handleModelLoadDialogContinue = () => {
    acknowledgeModelLoadWarning();
    setModelLoadDialogOpen(false);
    handleLoadModel();
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
    // eslint-disable-next-line react-hooks/purity
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

  const isLoading = status === "loading-model";
  const canRunInference = !isWebcamActive && !!currentImage && !isEditing;
  const canEditBoxes =
    !isWebcamActive && !!currentResult && !isInferring && !isEditing;
  const canClassifyEdited =
    isEditing && editedBoxes.length > 0 && modelLoaded && !isInferring;

  const statusText = (() => {
    if (webcamError && isWebcamActive) return webcamError;
    if (error) return t("status.error", { error });
    if (status === "loading-model") return t("status.loadingModel");

    // Context-aware status based on selected image
    if (currentImage) {
      const queueEntry = useInferenceQueueStore
        .getState()
        .queue.find((i) => i.imageIndex === currentImage.index);

      if (queueEntry?.status === "processing") {
        if (status === "detecting") return t("status.detecting");
        if (status === "classifying") return t("status.classifying");
      }

      if (queueEntry?.status === "pending") {
        return t("status.queued");
      }

      const imageResults = getResultsForImage(currentImage.index);
      if (
        imageResults.length > 0 &&
        status !== "detecting" &&
        status !== "classifying"
      ) {
        return t("status.inferenceComplete");
      }
    }

    if (modelLoaded) return t("status.modelReady");
    return t("status.noModelLoaded");
  })();

  return (
    <>
      <Dialog open={modelLoadDialogOpen} onClose={handleModelLoadDialogCancel}>
        <DialogTitle>{t("modelLoadDialog.title")}</DialogTitle>
        <DialogContent>{t("modelLoadDialog.message")}</DialogContent>
        <DialogActions>
          <Button onClick={handleModelLoadDialogCancel}>
            {t("modelLoadDialog.cancel")}
          </Button>
          <Button onClick={handleModelLoadDialogContinue} variant="contained">
            {t("modelLoadDialog.continue")}
          </Button>
        </DialogActions>
      </Dialog>
      <NachetMiniView
        devices={devices}
        activeDeviceId={activeDeviceId}
        setActiveDeviceId={setActiveDeviceId}
        requestDevices={requestDevices}
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
        detectorPrompt={detectorPrompt}
        setDetectorPrompt={setDetectorPrompt}
        detectorRequiresPrompt={detectorRequiresPrompt}
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
    </>
  );
};

export { NachetMiniContainer as NachetMini };
