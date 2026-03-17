import { useEffect, useRef, useState } from "react";
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
  Typography,
  createTheme,
} from "@mui/material";
import AddAPhotoIcon from "@mui/icons-material/AddAPhoto";
import AddPhotoAlternateIcon from "@mui/icons-material/AddPhotoAlternate";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import SaveIcon from "@mui/icons-material/Save";
import type Webcam from "react-webcam";
import { useWebcamDevices } from "@hooks/useWebcamDevices";
import { useWebcamStore } from "@stores/useWebcamStore";
import { useImageStore } from "@stores/useImageStore";
import { useInferenceStore } from "@stores/useInferenceStore";
import { useInference } from "@inference/useInference";
import {
  DETECTOR_MODELS,
  CLASSIFIER_MODELS,
  DEFAULT_DETECTOR,
  DEFAULT_CLASSIFIER,
  buildModelConfig,
} from "@inference/models";
import ImageUpload from "@components/ImageUpload";
import WebcamCapture from "@components/WebcamCapture";
import SaveDialog from "@components/SaveDialog";
import ImageGallery from "@components/ImageGallery";
import ResultsTable from "@components/ResultsTable";
import ImageViewer from "@components/ImageViewer";
import ModelLoader from "@components/ModelLoader";
import Navbar from "@components/Navbar";
import AppBar from "@components/AppBar";
import Footer from "@components/Footer";
import { useTranslation } from "react-i18next";

const theme = createTheme();

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
    paddingTop: "0.3vh",
    paddingBottom: "0.3vh",
    paddingLeft: "0.7vh",
    paddingRight: "0.7vh",
    fontSize: "1.17vh",
    width: "fit-content",
    border: "0.01vh solid LightGrey",
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
  fontSize: "1.7vh",
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
  const clearResults = useInferenceStore((s) => s.clearResults);
  const setError = useInferenceStore((s) => s.setError);

  const { loadModels, runInference } = useInference();

  // Local state
  const [uploadOpen, setUploadOpen] = useState(false);
  const [saveOpen, setSaveOpen] = useState(false);
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

  const currentImage = getCurrentImage();
  const currentResult = currentImage
    ? (results.get(currentImage.index) ?? null)
    : null;

  const handleImageLoaded = (src: string, dims: number[]) => {
    addImage(src, dims);
    setUploadOpen(false);
  };

  const handleCaptureFeed = () => {
    const screenshot = webcamRef.current?.getScreenshot();
    if (!screenshot) return;

    const video = webcamRef.current?.video;
    const width = video?.videoWidth ?? 1920;
    const height = video?.videoHeight ?? 1080;

    addImage(screenshot, [width, height]);
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

  const handleClearImages = () => {
    clearImages();
    clearResults();
  };

  const hasResult = (index: number): boolean => results.has(index);

  const isInferring = status === "detecting" || status === "classifying";
  const isLoading = status === "loading-model";
  const canRunInference =
    !isWebcamActive && !!currentImage && modelLoaded && !isInferring;

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
            flex: 1,
            overflow: "hidden",
            gap: "1vw",
            px: "1.5vw",
            py: "1vh",
          }}
        >
          {/* Left: Controls toolbar + Image Viewer / Webcam */}
          <Box
            sx={{
              minWidth: "65vw",
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
                sx={{ minWidth: "8vw", maxWidth: "8vw" }}
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
                label={t("controls.capture")}
                icon={<AddAPhotoIcon color="inherit" style={iconStyle} />}
                disabled={!isWebcamActive}
                onClick={handleCaptureFeed}
              />
              <Switch
                checked={!isWebcamActive}
                onChange={() => {
                  setWebcamError("");
                  setIsWebcamActive(!isWebcamActive);
                }}
                size="small"
              />

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
              <ControlBarButton
                label={t("controls.save")}
                icon={<SaveIcon color="inherit" style={iconStyle} />}
                disabled={isWebcamActive || images.length === 0}
                onClick={() => setSaveOpen(true)}
              />
              <ModelLoader
                detectors={DETECTOR_MODELS}
                classifiers={CLASSIFIER_MODELS}
                selectedDetectorId={selectedDetectorId}
                selectedClassifierId={selectedClassifierId}
                onSelectDetector={setSelectedDetectorId}
                onSelectClassifier={setSelectedClassifierId}
                isLoading={isLoading}
                progress={modelLoadProgress}
              />
              <ControlBarButton
                label={t("controls.runInference")}
                icon={<PlayArrowIcon color="inherit" style={iconStyle} />}
                disabled={!canRunInference}
                onClick={handleRunInference}
              />
              <Typography
                variant="body2"
                sx={{
                  fontSize: "1.1vh",
                  color: error || webcamError ? "error.main" : "text.secondary",
                  ml: "0.4vh",
                }}
              >
                {statusText}
              </Typography>
            </Box>

            {/* Workspace: Webcam feed or Image Viewer */}
            <Box sx={{ flex: 1, overflow: "hidden" }}>
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

          {/* Right: Gallery + Results */}
          <Box
            sx={{
              width: "30vw",
              flexShrink: 0,
              display: "flex",
              flexDirection: "column",
              gap: "1vh",
              overflow: "hidden",
              marginTop: "5vh",
            }}
          >
            <ImageGallery
              images={images}
              currentIndex={currentIndex}
              onSelect={setCurrentIndex}
              onRemove={removeImage}
              onClear={handleClearImages}
              hasResult={hasResult}
            />
            <ResultsTable
              result={currentResult}
              switchTable={switchTable}
              onSwitchTableChange={setSwitchTable}
            />
          </Box>
        </Box>

        {/* Footer */}
        <Footer />
      </Box>

      <ImageUpload
        open={uploadOpen}
        onClose={() => {
          setUploadOpen(false);
        }}
        onImageLoaded={handleImageLoaded}
      />
      <SaveDialog open={saveOpen} onClose={() => setSaveOpen(false)} />
    </ThemeProvider>
  );
}

export default App;
