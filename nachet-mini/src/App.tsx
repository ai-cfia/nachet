import { useEffect, useRef, useState, useCallback } from "react";
import {
  Box,
  Button,
  CssBaseline,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Switch,
  ThemeProvider,
  Tooltip,
  Badge,
  createTheme,
} from "@mui/material";
import AddAPhotoIcon from "@mui/icons-material/AddAPhoto";
import AddPhotoAlternateIcon from "@mui/icons-material/AddPhotoAlternate";
import VisibilityIcon from "@mui/icons-material/Visibility";
import TuneIcon from "@mui/icons-material/Tune";
// import SaveIcon from "@mui/icons-material/Save";
import FileDownloadIcon from "@mui/icons-material/FileDownload";
import EditIcon from "@mui/icons-material/Edit";
import AddBoxIcon from "@mui/icons-material/AddBox";
import CloseIcon from "@mui/icons-material/Close";
import type Webcam from "react-webcam";
import { useWebcamDevices } from "@hooks/useWebcamDevices";
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
import ImageUpload from "@components/ImageUpload";
import WebcamCapture from "@components/WebcamCapture";
import SaveDialog from "@components/SaveDialog";
import ExportDialog from "@components/ExportDialog";
import MetadataDialog from "@components/MetadataDialog";
import ImageGallery from "@components/ImageGallery";
import ResultsTable from "@components/ResultsTable";
import ImageViewer from "@components/ImageViewer";
import ModelLoader from "@components/ModelLoader";
import Navbar from "@components/Navbar";
import AppBar from "@components/AppBar";
import Footer from "@components/Footer";
import { useTranslation } from "react-i18next";
import { computeSha256 } from "@common/hash";

const theme = createTheme({
  components: {
    MuiButton: {
      styleOverrides: {
        outlined: {
          borderColor: "#1565c0",
          "&:hover": { borderColor: "#1565c0" },
          "&.Mui-disabled": { borderColor: "LightGrey" },
        },
      },
    },
    MuiOutlinedInput: {
      styleOverrides: {
        notchedOutline: {
          borderColor: "#1565c0",
        },
        root: {
          "&:hover .MuiOutlinedInput-notchedOutline": {
            borderColor: "#1565c0",
          },
          "&.Mui-focused .MuiOutlinedInput-notchedOutline": {
            borderColor: "#1565c0",
          },
          "&.Mui-disabled .MuiOutlinedInput-notchedOutline": {
            borderColor: "LightGrey",
          },
        },
      },
    },
  },
});

const ControlBarButton = (props: {
  label: string;
  icon: React.ReactNode;
  disabled: boolean;
  onClick: () => void;
  sx?: object;
}) => {
  const { label, icon, onClick, disabled, sx } = props;
  const buttonStyle = {
    borderRadius: "0.4vh",
    paddingTop: { xs: "1vh", md: "0.3vh" },
    paddingBottom: { xs: "1vh", md: "0.3vh" },
    paddingLeft: { xs: "1.5vh", md: "0.7vh" },
    paddingRight: { xs: "1.5vh", md: "0.7vh" },
    fontSize: { xs: "1.8vh", md: "1.17vh" },
    width: "fit-content",
    textTransform: "none",
    "&:hover": {
      backgroundColor: "#F5F5F5",
      transition: "0.1s ease-in-out all",
    },
    ...sx,
  };
  return (
    <Button
      color="inherit"
      variant="outlined"
      disabled={disabled}
      onClick={onClick}
      sx={buttonStyle}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          flexWrap: "wrap",
        }}
      >
        {icon}
        <span>{label}</span>
      </div>
    </Button>
  );
};

const iconStyle = {
  fontSize: "2.4vh",
  paddingRight: "0.4vh",
  marginTop: 0,
  marginBottom: 0,
  marginRight: 0,
  marginLeft: 0,
  paddingTop: 0,
  paddingBottom: 0,
  paddingLeft: 0,
};

function App() {
  const { t } = useTranslation("main");

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
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Box
        sx={{
          display: "flex",
          flexDirection: "column",
          height: "100vh",
          overflow: "hidden",
        }}
      >
        {/* Header */}
        <Navbar />
        <AppBar />

        {/* Main content */}
        <Box
          sx={{
            display: "flex",
            flexDirection: { xs: "column", md: "row" },
            flex: 1,
            overflow: { xs: "auto", md: "hidden" },
            gap: "1vw",
            px: "1.5vw",
            py: "1vh",
          }}
        >
          {/* Left: Controls toolbar + Image Viewer / Webcam */}
          <Box
            sx={{
              minWidth: { xs: "100%", md: "65vw" },
              display: "flex",
              flexDirection: "column",
              overflow: "hidden",
            }}
          >
            {/* Controls toolbar */}
            <Box
              sx={{
                display: "flex",
                flexDirection: "row",
                justifyContent: "flex-start",
                flexWrap: "wrap",
                alignItems: "center",
                padding: "0.8vh",
                rowGap: "0.8vh",
                columnGap: "0.4vh",
                borderBottom: "0.01vh solid LightGrey",
                flexShrink: 0,
              }}
            >
              {/* Webcam toggle */}
              <FormControl
                size="small"
                sx={{
                  minWidth: { xs: "fit-content", md: "8vw" },
                  maxWidth: { xs: "fit-content", md: "8vw" },
                }}
              >
                <InputLabel sx={{ fontSize: "1.2vh" }}>
                  {t("controls.camera")}
                </InputLabel>
                <Select
                  value={activeDeviceId ?? ""}
                  onChange={(e) => setActiveDeviceId(e.target.value)}
                  label={t("controls.camera")}
                  displayEmpty
                  sx={{ fontSize: "1.2vh" }}
                  disabled={!isWebcamActive}
                >
                  {devices.length === 0 ? (
                    <MenuItem value="" disabled sx={{ fontSize: "1.2vh" }}>
                      {t("controls.noCamera")}
                    </MenuItem>
                  ) : (
                    devices.map((device) => (
                      <MenuItem
                        key={device.deviceId}
                        value={device.deviceId}
                        sx={{ fontSize: "1.2vh" }}
                      >
                        {device.label ||
                          t("controls.cameraDevice", {
                            id: device.deviceId.slice(0, 8),
                          })}
                      </MenuItem>
                    ))
                  )}
                </Select>
              </FormControl>
              <ControlBarButton
                label={t("controls.meta")}
                icon={
                  <Badge
                    color="warning"
                    variant="dot"
                    invisible={!metadataNotSet}
                    overlap="circular"
                  >
                    <TuneIcon color="inherit" style={iconStyle} />
                  </Badge>
                }
                disabled={false}
                onClick={() => {
                  setMetadataMode("defaults");
                  setMetadataImageIndex(undefined);
                  setMetadataOpen(true);
                }}
              />
              <ControlBarButton
                label={t("controls.capture")}
                icon={<AddAPhotoIcon color="inherit" style={iconStyle} />}
                disabled={!isWebcamActive}
                onClick={handleCaptureFeed}
              />
              <Tooltip
                title={metadataNotSet ? t("controls.metadataRequired") : ""}
                arrow
              >
                <span>
                  <Switch
                    checked={!isWebcamActive}
                    onChange={() => {
                      setWebcamError("");
                      setIsWebcamActive(!isWebcamActive);
                    }}
                    size="small"
                    disabled={metadataNotSet}
                    sx={
                      metadataNotSet
                        ? {}
                        : {
                            "& .MuiSwitch-switchBase": {
                              color: "#1565c0",
                            },
                            "& .MuiSwitch-switchBase.Mui-checked": {
                              color: "#1565c0",
                            },
                            "& .MuiSwitch-track": {
                              backgroundColor: "#1565c0",
                            },
                            "& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track":
                              {
                                backgroundColor: "#1565c0",
                              },
                          }
                    }
                  />
                </span>
              </Tooltip>

              {/* Capture (webcam active only) */}
              <ControlBarButton
                label={t("controls.upload")}
                icon={
                  <AddPhotoAlternateIcon color="inherit" style={iconStyle} />
                }
                disabled={isWebcamActive}
                onClick={() => {
                  setUploadOpen(true);
                }}
              />
              {/* <ControlBarButton
                label={t("controls.save")}
                icon={<SaveIcon color="inherit" style={iconStyle} />}
                disabled={isWebcamActive || images.length === 0}
                onClick={() => setSaveOpen(true)}
              /> */}
              <ControlBarButton
                label={t("controls.export")}
                icon={<FileDownloadIcon color="inherit" style={iconStyle} />}
                disabled={
                  isWebcamActive ||
                  (checkedImages.size === 0 && checkedResults.size === 0)
                }
                onClick={() => setExportOpen(true)}
              />
              <ModelLoader
                detectors={DETECTOR_MODELS}
                classifiers={CLASSIFIER_MODELS}
                selectedDetectorId={selectedDetectorId}
                selectedClassifierId={selectedClassifierId}
                onSelectDetector={setSelectedDetectorId}
                onSelectClassifier={setSelectedClassifierId}
                isLoading={isLoading}
              />
              {!isEditing && (
                <ControlBarButton
                  label={t("controls.editBoxes")}
                  icon={<EditIcon color="inherit" style={iconStyle} />}
                  disabled={!canEditBoxes}
                  onClick={handleEnterEditMode}
                />
              )}
              {isEditing && (
                <>
                  <ControlBarButton
                    label={t("controls.addBox")}
                    icon={<AddBoxIcon color="inherit" style={iconStyle} />}
                    disabled={false}
                    onClick={() => setIsDrawing(!isDrawingBox)}
                    sx={isDrawingBox ? { backgroundColor: "#e3f2fd" } : {}}
                  />
                  <ControlBarButton
                    label={t("controls.discardEdits")}
                    icon={<CloseIcon color="inherit" style={iconStyle} />}
                    disabled={false}
                    onClick={handleDiscardEdits}
                  />
                </>
              )}
              <ControlBarButton
                label={t("controls.runInference")}
                icon={<VisibilityIcon color="inherit" style={iconStyle} />}
                disabled={isEditing ? !canClassifyEdited : !canRunInference}
                onClick={isEditing ? handleClassifyEdited : handleRunInference}
              />
            </Box>

            {/* Workspace: Webcam feed or Image Viewer */}
            <Box
              sx={{
                flex: 1,
                overflow: "hidden",
                minHeight: { xs: "30vh", md: 0 },
              }}
            >
              {isWebcamActive ? (
                <WebcamCapture
                  webcamRef={webcamRef}
                  onUserMediaError={handleWebcamError}
                />
              ) : (
                <ImageViewer
                  src={currentImage?.src}
                  imageDims={currentImage?.imageDims ?? []}
                  result={currentResult}
                />
              )}
            </Box>
          </Box>

          {/* Right: Gallery + Results (below on mobile) */}
          <Box
            sx={{
              width: { xs: "100%", md: "30vw" },
              flexShrink: 0,
              display: "flex",
              flexDirection: "column",
              gap: "1vh",
              overflow: "hidden",
              marginTop: { xs: "1vh", md: "5vh" },
              minHeight: { xs: "35vh", md: 0 },
            }}
          >
            <ImageGallery
              images={images}
              currentIndex={currentIndex}
              activeResultKey={activeResultKey}
              checkedImages={checkedImages}
              checkedResults={checkedResults}
              onCheckedImagesChange={setCheckedImages}
              onCheckedResultsChange={setCheckedResults}
              onSelectImage={handleSelectImage}
              onSelectResult={handleSelectResult}
              onRemoveImage={handleRemoveImage}
              onRemoveResult={handleRemoveResult}
              onEditMetadata={handleEditMetadata}
              onClear={handleClearImages}
              getResultsForImage={getResultsForImage}
            />
            <ResultsTable
              result={currentResult}
              switchTable={switchTable}
              onSwitchTableChange={setSwitchTable}
            />
          </Box>
        </Box>

        {/* Footer */}
        <Footer
          statusText={statusText}
          isError={!!(error || webcamError)}
          isLoading={isLoading}
          loadProgress={modelLoadProgress}
        />
      </Box>

      <ImageUpload
        open={uploadOpen}
        onClose={() => {
          setUploadOpen(false);
        }}
        onImageLoaded={handleImageLoaded}
      />
      <SaveDialog open={saveOpen} onClose={() => setSaveOpen(false)} />
      <ExportDialog
        open={exportOpen}
        onClose={() => setExportOpen(false)}
        checkedImages={checkedImages}
        checkedResults={checkedResults}
        onExportComplete={() => {
          setCheckedImages(new Set());
          setCheckedResults(new Set());
        }}
      />
      <MetadataDialog
        open={metadataOpen}
        onClose={() => setMetadataOpen(false)}
        mode={metadataMode}
        imageIndex={metadataImageIndex}
      />
    </ThemeProvider>
  );
}

export default App;
