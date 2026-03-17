import { useState } from "react";
import {
  Box,
  Button,
  CssBaseline,
  ThemeProvider,
  Typography,
  createTheme,
} from "@mui/material";
import AddPhotoAlternateIcon from "@mui/icons-material/AddPhotoAlternate";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
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
import ImageGallery from "@components/ImageGallery";
import ResultsTable from "@components/ResultsTable";
import ImageViewer from "@components/ImageViewer";
import ModelLoader from "@components/ModelLoader";

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
  const [selectedDetectorId, setSelectedDetectorId] = useState(
    DEFAULT_DETECTOR.id,
  );
  const [selectedClassifierId, setSelectedClassifierId] = useState(
    DEFAULT_CLASSIFIER.id,
  );
  const [switchTable, setSwitchTable] = useState(true);

  const currentImage = getCurrentImage();
  const currentResult = currentImage
    ? (results.get(currentImage.index) ?? null)
    : null;

  const handleImageLoaded = (src: string, dims: number[]) => {
    addImage(src, dims);
    setUploadOpen(false);
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
  const canRunInference = !!currentImage && modelLoaded && !isInferring;

  const statusText = (() => {
    if (error) return `Error: ${error}`;
    if (status === "loading-model") return "Loading model…";
    if (status === "detecting") return "Detecting objects…";
    if (status === "classifying") return "Classifying detections…";
    if (status === "complete") return "Inference complete";
    if (modelLoaded) return "Model ready";
    return "No model loaded";
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
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            px: "1.5vw",
            height: "4vh",
            flexShrink: 0,
            borderBottom: "0.01vh solid LightGrey",
          }}
        >
          <Typography sx={{ fontWeight: 700, fontSize: "2vh" }}>
            Nachet Mini
          </Typography>
        </Box>

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
          {/* Left: Controls toolbar + Image Viewer */}
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
              <ControlBarButton
                label="Upload"
                icon={
                  <AddPhotoAlternateIcon color="inherit" style={iconStyle} />
                }
                disabled={false}
                onClick={() => {
                  setUploadOpen(true);
                }}
              />
              <ModelLoader
                detectors={DETECTOR_MODELS}
                classifiers={CLASSIFIER_MODELS}
                selectedDetectorId={selectedDetectorId}
                selectedClassifierId={selectedClassifierId}
                onSelectDetector={setSelectedDetectorId}
                onSelectClassifier={setSelectedClassifierId}
                onLoad={handleLoadModel}
                isLoading={isLoading}
                progress={modelLoadProgress}
              />
              <Typography
                variant="body2"
                sx={{
                  fontSize: "1.1vh",
                  color: error ? "error.main" : "text.secondary",
                  ml: "0.4vh",
                }}
              >
              <ControlBarButton
                label="Run Inference"
                icon={<PlayArrowIcon color="inherit" style={iconStyle} />}
                disabled={!canRunInference}
                onClick={handleRunInference}
              />
                {statusText}
              </Typography>
            </Box>

            {/* Image Viewer */}
            <Box sx={{ flex: 1, overflow: "hidden" }}>
              <ImageViewer
                src={currentImage?.src}
                imageDims={currentImage?.imageDims ?? []}
                result={currentResult}
              />
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
              overflowY: "auto",
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
      </Box>

      <ImageUpload
        open={uploadOpen}
        onClose={() => {
          setUploadOpen(false);
        }}
        onImageLoaded={handleImageLoaded}
      />
    </ThemeProvider>
  );
}

export default App;
