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
import { MODEL_PRESETS, DEFAULT_MODEL } from "@inference/models";
import ImageUpload from "@components/ImageUpload";
import ImageGallery from "@components/ImageGallery";
import ResultsTable from "@components/ResultsTable";
import ImageViewer from "@components/ImageViewer";
import ModelLoader from "@components/ModelLoader";

const theme = createTheme();

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
  const getResult = useInferenceStore((s) => s.getResult);
  const clearResults = useInferenceStore((s) => s.clearResults);
  const setModelLoaded = useInferenceStore((s) => s.setModelLoaded);
  const setError = useInferenceStore((s) => s.setError);

  const { loadModels, runInference } = useInference();

  // Local state
  const [uploadOpen, setUploadOpen] = useState(false);
  const [selectedModelId, setSelectedModelId] = useState(DEFAULT_MODEL.id);
  const [switchTable, setSwitchTable] = useState(true);

  const currentImage = getCurrentImage();
  const currentResult = currentImage
    ? (getResult(currentImage.index) ?? null)
    : null;

  const handleImageLoaded = (src: string, dims: number[]) => {
    addImage(src, dims);
    setUploadOpen(false);
  };

  const handleLoadModel = () => {
    const config = MODEL_PRESETS.find((p) => p.id === selectedModelId);
    if (!config) return;
    setModelLoaded(false);
    setError(null);
    loadModels(config);
  };

  const handleRunInference = () => {
    if (!currentImage) return;
    runInference(currentImage.src, currentImage.index);
  };

  const handleClearImages = () => {
    clearImages();
    clearResults();
  };

  const hasResult = (index: number): boolean => getResult(index) !== undefined;

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
            justifyContent: "space-between",
            px: "1.5vw",
            height: "6vh",
            flexShrink: 0,
            borderBottom: "0.01vh solid LightGrey",
          }}
        >
          <Typography sx={{ fontWeight: 700, fontSize: "2vh" }}>
            Nachet Mini
          </Typography>
          <ModelLoader
            presets={MODEL_PRESETS}
            selectedId={selectedModelId}
            onSelectId={setSelectedModelId}
            onLoad={handleLoadModel}
            isLoading={isLoading}
            progress={modelLoadProgress}
          />
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
          {/* Left: Image Viewer */}
          <Box sx={{ flex: 1, overflow: "hidden", minWidth: 0 }}>
            <ImageViewer
              src={currentImage?.src}
              imageDims={currentImage?.imageDims ?? []}
              result={currentResult}
            />
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

        {/* Footer */}
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            px: "1.5vw",
            height: "7vh",
            flexShrink: 0,
            borderTop: "0.01vh solid LightGrey",
          }}
        >
          <Box sx={{ display: "flex", gap: "1vw" }}>
            <Button
              variant="outlined"
              size="small"
              startIcon={<AddPhotoAlternateIcon />}
              onClick={() => {
                setUploadOpen(true);
              }}
              sx={{ fontSize: "1.1vh", textTransform: "none" }}
            >
              Upload Image
            </Button>
            <Button
              variant="contained"
              size="small"
              startIcon={<PlayArrowIcon />}
              onClick={handleRunInference}
              disabled={!canRunInference}
              sx={{ fontSize: "1.1vh", textTransform: "none" }}
            >
              Run Inference
            </Button>
          </Box>
          <Typography
            variant="body2"
            sx={{
              fontSize: "1.1vh",
              color: error ? "error.main" : "text.secondary",
            }}
          >
            {statusText}
          </Typography>
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
