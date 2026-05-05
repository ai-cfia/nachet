import type { Dispatch, RefObject, SetStateAction } from "react";
import {
  Box,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Switch,
  Tooltip,
  Badge,
} from "@mui/material";
import AddAPhotoIcon from "@mui/icons-material/AddAPhoto";
import AddPhotoAlternateIcon from "@mui/icons-material/AddPhotoAlternate";
import VisibilityIcon from "@mui/icons-material/Visibility";
import TuneIcon from "@mui/icons-material/Tune";
import FileDownloadIcon from "@mui/icons-material/FileDownload";
import EditIcon from "@mui/icons-material/Edit";
import AddBoxIcon from "@mui/icons-material/AddBox";
import CloseIcon from "@mui/icons-material/Close";
import type Webcam from "react-webcam";
import { useTranslation } from "react-i18next";
import type { Images, InferenceResult } from "@common/types";
import { DETECTOR_MODELS, CLASSIFIER_MODELS } from "@inference/models";
import ImageUpload from "@components/ImageUpload";
import WebcamCapture from "@components/WebcamCapture";
import SaveDialog from "@components/SaveDialog";
import ExportDialog from "@components/ExportDialog";
import MetadataDialog from "@components/MetadataDialog";
import VersionCheckDialog from "@components/VersionCheckDialog";
import ImageGallery from "@components/ImageGallery";
import ResultsTable from "@components/ResultsTable";
import ImageViewer from "@components/ImageViewer";
import ModelLoader from "@components/ModelLoader";
import Navbar from "@components/Navbar";
import AppBar from "@components/AppBar";
import Footer from "@components/Footer";
import ControlBarButton from "@components/ControlBarButton";

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

export interface NachetMiniViewProps {
  // Webcam
  devices: MediaDeviceInfo[];
  activeDeviceId: string | undefined;
  setActiveDeviceId: (id: string | undefined) => void;
  isWebcamActive: boolean;
  setIsWebcamActive: (v: boolean) => void;
  webcamRef: RefObject<Webcam | null>;
  webcamError: string;
  setWebcamError: (v: string) => void;
  onWebcamError: (err: string | DOMException) => void;
  onCaptureFeed: () => void;

  // Images
  images: Images[];
  currentIndex: number;
  currentImage: Images | undefined;

  // Results
  currentResult: InferenceResult | null;
  activeResultKey: string | null;
  getResultsForImage: (
    i: number,
  ) => Array<{ modelConfigId: string; result: InferenceResult }>;

  // Selections (for export)
  checkedImages: Set<number>;
  checkedResults: Set<string>;
  setCheckedImages: Dispatch<SetStateAction<Set<number>>>;
  setCheckedResults: Dispatch<SetStateAction<Set<string>>>;

  // Metadata
  metadataNotSet: boolean;
  metadataOpen: boolean;
  metadataMode: "defaults" | "image";
  metadataImageIndex: number | undefined;
  onOpenMetadataDefaults: () => void;
  onCloseMetadata: () => void;
  onEditMetadata: (i: number) => void;

  // Models
  selectedDetectorId: string;
  selectedClassifierId: string;
  setSelectedDetectorId: (id: string) => void;
  setSelectedClassifierId: (id: string) => void;

  // Edit mode
  isEditing: boolean;
  isDrawingBox: boolean;
  setIsDrawing: (v: boolean) => void;
  onEnterEditMode: () => void;
  onDiscardEdits: () => void;
  onClassifyEdited: () => void;

  // Inference
  onRunInference: () => void;
  canRunInference: boolean;
  canEditBoxes: boolean;
  canClassifyEdited: boolean;
  isLoading: boolean;
  modelLoadProgress: { name: string; progress: number } | null;

  // Gallery actions
  onSelectImage: (i: number) => void;
  onSelectResult: (k: string) => void;
  onRemoveImage: (i: number) => void;
  onRemoveResult: (k: string) => void;
  onClearImages: () => void;

  // Dialogs
  uploadOpen: boolean;
  setUploadOpen: (v: boolean) => void;
  onImageLoaded: (src: string, dims: number[], fileName?: string) => void;
  saveOpen: boolean;
  setSaveOpen: (v: boolean) => void;
  exportOpen: boolean;
  setExportOpen: (v: boolean) => void;
  onExportComplete: () => void;
  versionDialogOpen: boolean;
  remoteVersion: string | null;
  onCloseVersionDialog: () => void;

  // Status / footer
  statusText: string;
  isError: boolean;

  // Results table
  switchTable: boolean;
  setSwitchTable: (v: boolean) => void;
}

const NachetMiniView = (props: NachetMiniViewProps) => {
  const { t } = useTranslation("main");
  const {
    devices,
    activeDeviceId,
    setActiveDeviceId,
    isWebcamActive,
    setIsWebcamActive,
    webcamRef,
    setWebcamError,
    onWebcamError,
    onCaptureFeed,
    images,
    currentIndex,
    currentImage,
    currentResult,
    activeResultKey,
    getResultsForImage,
    checkedImages,
    checkedResults,
    setCheckedImages,
    setCheckedResults,
    metadataNotSet,
    metadataOpen,
    metadataMode,
    metadataImageIndex,
    onOpenMetadataDefaults,
    onCloseMetadata,
    onEditMetadata,
    selectedDetectorId,
    selectedClassifierId,
    setSelectedDetectorId,
    setSelectedClassifierId,
    isEditing,
    isDrawingBox,
    setIsDrawing,
    onEnterEditMode,
    onDiscardEdits,
    onClassifyEdited,
    onRunInference,
    canRunInference,
    canEditBoxes,
    canClassifyEdited,
    isLoading,
    modelLoadProgress,
    onSelectImage,
    onSelectResult,
    onRemoveImage,
    onRemoveResult,
    onClearImages,
    uploadOpen,
    setUploadOpen,
    onImageLoaded,
    saveOpen,
    setSaveOpen,
    exportOpen,
    setExportOpen,
    onExportComplete,
    versionDialogOpen,
    remoteVersion,
    onCloseVersionDialog,
    statusText,
    isError,
    switchTable,
    setSwitchTable,
  } = props;

  return (
    <>
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
                <InputLabel id="camera-select-label" sx={{ fontSize: "1.2vh" }}>
                  {t("controls.camera")}
                </InputLabel>
                <Select
                  id="camera-select"
                  labelId="camera-select-label"
                  value={activeDeviceId ?? ""}
                  onChange={(e) => setActiveDeviceId(e.target.value)}
                  label={t("controls.camera")}
                  displayEmpty
                  SelectDisplayProps={{ "aria-label": t("controls.camera") }}
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
                onClick={onOpenMetadataDefaults}
              />
              <ControlBarButton
                label={t("controls.capture")}
                icon={<AddAPhotoIcon color="inherit" style={iconStyle} />}
                disabled={!isWebcamActive}
                onClick={onCaptureFeed}
              />
              <Tooltip
                title={metadataNotSet ? t("controls.metadataRequired") : ""}
                arrow
                describeChild
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
                    slotProps={{
                      input: { "aria-label": t("controls.imageMode") },
                    }}
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
                  onClick={onEnterEditMode}
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
                    onClick={onDiscardEdits}
                  />
                </>
              )}
              <ControlBarButton
                label={t("controls.runInference")}
                icon={<VisibilityIcon color="inherit" style={iconStyle} />}
                disabled={isEditing ? !canClassifyEdited : !canRunInference}
                onClick={isEditing ? onClassifyEdited : onRunInference}
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
                  onUserMediaError={onWebcamError}
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
              onSelectImage={onSelectImage}
              onSelectResult={onSelectResult}
              onRemoveImage={onRemoveImage}
              onRemoveResult={onRemoveResult}
              onEditMetadata={onEditMetadata}
              onClear={onClearImages}
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
          isError={isError}
          isLoading={isLoading}
          loadProgress={modelLoadProgress}
        />
      </Box>

      <ImageUpload
        open={uploadOpen}
        onClose={() => {
          setUploadOpen(false);
        }}
        onImageLoaded={onImageLoaded}
      />
      <SaveDialog open={saveOpen} onClose={() => setSaveOpen(false)} />
      <ExportDialog
        open={exportOpen}
        onClose={() => setExportOpen(false)}
        checkedImages={checkedImages}
        checkedResults={checkedResults}
        onExportComplete={onExportComplete}
      />
      <MetadataDialog
        open={metadataOpen}
        onClose={onCloseMetadata}
        mode={metadataMode}
        imageIndex={metadataImageIndex}
      />
      <VersionCheckDialog
        open={versionDialogOpen}
        remoteVersion={remoteVersion}
        onClose={onCloseVersionDialog}
      />
    </>
  );
};

export default NachetMiniView;
