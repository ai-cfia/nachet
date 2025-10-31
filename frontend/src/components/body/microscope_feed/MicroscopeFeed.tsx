// \components\body\microscope_feed\index.tsx
// MicroscopeFeed
import Webcam from "react-webcam";
import { useEffect, useMemo, useState } from "react";
import { Box, Button, Switch } from "@mui/material";
// Import icons
import SwitchCameraIcon from "@mui/icons-material/SwitchCamera";
import AddAPhotoIcon from "@mui/icons-material/AddAPhoto";
import UploadFileIcon from "@mui/icons-material/UploadFile";
import DownloadIcon from "@mui/icons-material/Download";
import CropFreeIcon from "@mui/icons-material/CropFree";
import DonutSmallIcon from "@mui/icons-material/DonutSmall";
import FormatShapesOutlinedIcon from "@mui/icons-material/FormatShapesOutlined";
import InfoIcon from "@mui/icons-material/Info";
import ArrowDropDownIcon from "@mui/icons-material/ArrowDropDown";
import { colours } from "@styles/colours";

// Import a loading icon component (ensure you have this)
import CircularProgress from "@mui/material/CircularProgress";
import {
  BoxCSS,
  SpeciesData,
  FeedbackDataNegative,
  FeedbackDataPositive,
  Images,
  ModelMetadata,
} from "@common/types";
import { sendNegativeFeedback, sendPositiveFeedback } from "@common";
import { useSpeciesData } from "@hooks";
import { useMsal, useIsAuthenticated } from "@azure/msal-react";
import { InteractionStatus } from "@azure/msal-browser";
import { acquireAccessToken } from "@common/auth";
import { getUnscaledCoordinates } from "@common/imageutils";
import { FreeformBox, NegativeFeedbackForm } from "../feedback_form";
import ApiAction from "../api_action";
import ScaledInferenceBox from "../scaled_inference_box";
import { useDeviceStore } from "@stores/useDeviceStore";
import { useImageStore } from "@stores/useImageStore";

interface MicroscopeFeedProps {
  webcamRef: React.RefObject<Webcam | null>;
  capture: () => void;
  activeDeviceId: string | undefined;
  devices: MediaDeviceInfo[];
  setSwitchDeviceOpen: React.Dispatch<React.SetStateAction<boolean>>;
  setDeviceInfoOpen: React.Dispatch<React.SetStateAction<boolean>>;
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
  setSaveOpen: React.Dispatch<React.SetStateAction<boolean>>;
  setBatchUploadOpen: React.Dispatch<React.SetStateAction<boolean>>;
  setUploadOpen: React.Dispatch<React.SetStateAction<boolean>>;
  setSwitchModelOpen: React.Dispatch<React.SetStateAction<boolean>>;
  selectedModel: string;
  metadata: ModelMetadata[];
  handleInference: () => void;
  handleDirectInference: () => void;
  isWebcamActive: boolean;
  isLoading: boolean;
  onCaptureClick: () => void;
  windowSize: {
    width: number;
    height: number;
  };
  toggleShowInference: (state: boolean) => void;
  backendUrl: string;
  uuid: string;
  apiScopeClaim: string;
}

const ButtonMicroscopeFeed = (props: {
  label: string;
  icon: React.ReactNode;
  disabled: boolean;
  onClick: () => void;
  endIcon?: React.ReactNode;
  sx?: object;
}) => {
  const { label, icon, onClick, disabled, endIcon, sx } = props;
  const buttonStyle = {
    marginRight: "0.2vh",
    marginLeft: "0.2vh",
    borderRadius: "0.4vh",
    paddingTop: "0.3vh",
    paddingBottom: "0.3vh",
    paddingLeft: "0.7vh",
    paddingRight: "0.7vh",
    fontSize: "1.17vh",
    width: "fit-content",
    border: `0.01vh solid LightGrey`,
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
        {endIcon}
      </div>
    </Button>
  );
};

const MicroscopeFeed = (props: MicroscopeFeedProps) => {
  const {
    webcamRef,
    capture,
    activeDeviceId,
    devices,
    setSwitchDeviceOpen,
    setDeviceInfoOpen,
    canvasRef,
    setSaveOpen,
    setBatchUploadOpen,
    setUploadOpen,
    setSwitchModelOpen,
    selectedModel,
    metadata,
    handleInference,
    handleDirectInference,
    isWebcamActive,
    isLoading,
    onCaptureClick,
    windowSize,
    toggleShowInference,
    backendUrl,
    uuid,
    apiScopeClaim,
  } = props;

  const { isDeviceInfoSet } = useDeviceStore();
  const {
    images: imageCache,
    currentIndex: imageIndex,
    loadInferenceResults,
  } = useImageStore();

  const width = windowSize.width * 0.575;
  const height = windowSize.height * 0.605;

  // Find the model name from metadata based on selectedModel (pipeline_id)
  const selectedModelName = useMemo(() => {
    const model = metadata.find((m) => m.pipeline_id === selectedModel);
    return model?.model_name || selectedModel;
  }, [metadata, selectedModel]);

  const defaultBoxPosition: BoxCSS = {
    minWidth: 100,
    minHeight: 100,
    maxWidth: 100,
    maxHeight: 100,
    left: width / 2 - 50,
    top: height / 2 - 50,
  };

  const [imageData, setImageData] = useState<Images | null>(null);
  const [feedbackMode, setFeedbackMode] = useState<boolean>(false);
  const [isNewAnnotation, setIsNewAnnotation] = useState<boolean>(false);
  const [scaledFeedbackBox, setScaledFeedbackBox] = useState<BoxCSS | null>(
    null,
  );
  const [inferenceForRevision, setInferenceForRevision] =
    useState<FeedbackDataNegative | null>(null);
  const [apiLoading, setApiLoading] = useState<boolean>(false);
  const [apiSuccess, setApiSuccess] = useState<boolean>(false);
  const [apiError, setApiError] = useState<string | null>(null);
  const [apiResultDismissed, setApiResultDismissed] = useState<boolean>(true);

  const { instance: msalInstance, inProgress } = useMsal();
  const isAuthenticated = useIsAuthenticated();
  const { speciesData, isLoading: classListLoading } = useSpeciesData(
    backendUrl,
    apiScopeClaim,
  );

  const classList: SpeciesData[] = useMemo(() => {
    if (!speciesData?.seeds) return [];
    return speciesData.seeds.map((seed, index) => ({
      ...seed,
      id: index,
    }));
  }, [speciesData]);

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

  const endIconStyle = {
    fontSize: "1.7vh",
    margin: 0,
    padding: 0,
  };

  const activeDevice = devices.find(
    (device) => device.deviceId === activeDeviceId,
  );
  const deviceLabel = activeDevice?.label || "SWITCH";

  const submitPositiveFeedback = async (index: number) => {
    if (!isAuthenticated) {
      setApiError("You must be signed in to submit feedback");
      setApiResultDismissed(false);
      return;
    }

    if (imageData == null) {
      return;
    }
    console.log("Submitting positive feedback for key: ", index);

    if (inProgress !== InteractionStatus.None) {
      alert("Authentication in progress, please wait");
      return;
    }

    const feedbackDataPositive: FeedbackDataPositive = {
      userId: uuid,
      inferenceId: imageData.boxes[index].inferenceId,
      boxes: [{ boxId: imageData.boxes[index].boxId }],
    };

    setApiLoading(true);
    setApiResultDismissed(false);

    try {
      const accessToken = await acquireAccessToken(msalInstance, [
        apiScopeClaim,
      ]);
      const response = await sendPositiveFeedback({
        feedbackData: feedbackDataPositive,
        backendUrl,
        accessToken,
      });
      console.log("Positive Feedback submitted successfully");
      loadInferenceResults(response, imageIndex);
      setApiSuccess(true);
    } catch (error) {
      console.error("Error submitting feedback: ", error);
      setApiError(error instanceof Error ? error.message : "Unknown error");
    } finally {
      setApiLoading(false);
    }
  };

  const submitNegativeFeedback = async (
    feedbackDataNegative: FeedbackDataNegative,
  ) => {
    if (!isAuthenticated) {
      setApiError("You must be signed in to submit feedback");
      setApiResultDismissed(false);
      return;
    }

    if (inProgress !== InteractionStatus.None) {
      setApiError("Authentication in progress, please wait");
      setApiResultDismissed(false);
      return;
    }

    if (imageData === null) {
      return;
    }
    console.log("Submitting negative feedback");
    setApiLoading(true);
    setApiResultDismissed(false);

    try {
      const accessToken = await acquireAccessToken(msalInstance, [
        apiScopeClaim,
      ]);
      const response = await sendNegativeFeedback({
        feedbackData: feedbackDataNegative,
        backendUrl,
        accessToken,
      });
      console.log("Negative Feedback submitted successfully");
      loadInferenceResults(response, imageIndex);
      setApiSuccess(true);
    } catch (error) {
      console.error("Error submitting feedback: ", error);
      setApiError(error instanceof Error ? error.message : "Unknown error");
    } finally {
      setApiLoading(false);
    }
  };

  const handleFreeformSubmit = (box: BoxCSS) => {
    setScaledFeedbackBox(box);
    setInferenceForRevision((prev) => {
      return prev
        ? {
            ...prev,
            boxes: [
              {
                ...prev.boxes[0],
                box: getUnscaledCoordinates(
                  width,
                  height,
                  imageData!.imageDims[0],
                  imageData!.imageDims[1],
                  box,
                ),
              },
            ],
          }
        : null;
    });
  };

  const handleAnnotate = () => {
    setIsNewAnnotation(true);
    enterFeedbackMode(imageIndex, defaultBoxPosition);
  };

  const exitFeedbackMode = () => {
    toggleShowInference(true);
    setFeedbackMode(false);
    setInferenceForRevision(null);
    setScaledFeedbackBox(null);
    setIsNewAnnotation(false);
    setApiLoading(false);
    setApiSuccess(false);
    setApiResultDismissed(true);
    setApiError(null);
  };

  const enterFeedbackMode = (index: number, boxPosition: BoxCSS) => {
    if (imageData == null) {
      exitFeedbackMode();
      return;
    }

    setScaledFeedbackBox(boxPosition);
    if (isNewAnnotation) {
      const unscaledBox = getUnscaledCoordinates(
        width,
        height,
        imageData.imageDims[0],
        imageData.imageDims[1],
        boxPosition,
      );
      setInferenceForRevision({
        userId: uuid,
        inferenceId: imageData.boxes[0].inferenceId,
        boxes: [
          {
            classId: "",
            label: "",
            boxId: "",
            box: unscaledBox,
            comment: "",
          },
        ],
      });
    } else {
      setInferenceForRevision({
        userId: uuid,
        inferenceId: imageData.boxes[index].inferenceId,
        boxes: [
          {
            classId: imageData.boxes[index].classId,
            label: imageData.boxes[index].label,
            boxId: imageData.boxes[index].boxId,
            box: {
              topX: imageData.boxes[index].topX,
              topY: imageData.boxes[index].topY,
              bottomX: imageData.boxes[index].bottomX,
              bottomY: imageData.boxes[index].bottomY,
            },
            comment: "",
          },
        ],
      });
    }

    toggleShowInference(false);
    setFeedbackMode(true);
  };

  useEffect(() => {
    if (imageCache.length > 0) {
      const image = imageCache.find((image) => image.index === imageIndex);
      if (
        image &&
        image.annotated &&
        image.scores.length > 0 &&
        image.boxes.length > 0 &&
        image.classifications.length > 0 &&
        image.imageDims[0] > 0
      ) {
        setImageData(image);
      } else {
        setImageData(null);
      }
    }
  }, [imageIndex, imageCache]);
  return (
    <Box
      sx={{
        width: width,
        minHeight: "100%",
        border: `0.01vh solid LightGrey`,
        borderRadius: "0.4vh",
      }}
      boxShadow={0}
      data-testid="microscope-component"
    >
      <Box
        sx={{
          display: "flex",
          flexDirection: "row",
          justifyContent: "center",
          flexWrap: "wrap",
          alignItems: "center",
          padding: "0.8vh",
        }}
      >
        <ButtonMicroscopeFeed
          label={deviceLabel.slice(0, 8)} // Limit label length to 8 characters
          icon={<SwitchCameraIcon color="inherit" style={iconStyle} />}
          endIcon={<ArrowDropDownIcon color="inherit" />}
          disabled={!isWebcamActive} // Disable when the webcam is active
          onClick={() => {
            setSwitchDeviceOpen(true);
          }}
          sx={{ paddingRight: "0.2vh" }}
        />
        <ButtonMicroscopeFeed
          label="DEVICE"
          icon={<InfoIcon color="inherit" style={iconStyle} />}
          disabled={false} // Always active
          onClick={() => {
            setDeviceInfoOpen(true);
          }}
        />
        <ButtonMicroscopeFeed
          label="CAPTURE"
          icon={<AddAPhotoIcon color="inherit" style={iconStyle} />}
          disabled={!isWebcamActive || !isDeviceInfoSet()} // Disable when the webcam is inactive or device info is not set
          onClick={() => {
            capture();
          }}
        />
        <Switch
          checked={!isWebcamActive}
          onChange={onCaptureClick}
          size="small"
          sx={{
            "& .MuiSwitch-switchBase": {
              color: colours.CFIA_Background_Blue,
            },
            "& .MuiSwitch-track": {
              backgroundColor: colours.CFIA_Background_Blue,
            },
          }}
        />
        <ButtonMicroscopeFeed
          label="LOAD"
          icon={<UploadFileIcon color="inherit" style={iconStyle} />}
          disabled={isWebcamActive} // Disable when the webcam is active
          onClick={() => {
            setUploadOpen(true);
          }}
        />
        <ButtonMicroscopeFeed
          label="SAVE"
          icon={<DownloadIcon color="inherit" style={iconStyle} />}
          disabled={isWebcamActive} // Disable when the webcam is active
          onClick={() => {
            setSaveOpen(true);
          }}
          sx={{ marginRight: "0.6vh" }}
        />
        <ButtonMicroscopeFeed
          label="BATCH"
          icon={<UploadFileIcon color="inherit" style={iconStyle} />}
          disabled={isWebcamActive} // Disable when the webcam is active
          onClick={() => {
            setBatchUploadOpen(true);
          }}
          sx={{ marginRight: "0.6vh" }}
        />
        <ButtonMicroscopeFeed
          label={selectedModelName.slice(0, 10)}
          icon={<DonutSmallIcon color="inherit" style={iconStyle} />}
          disabled={isWebcamActive} // Disable when the webcam is active
          onClick={() => {
            setSwitchModelOpen(true);
          }}
          endIcon={<ArrowDropDownIcon color="inherit" style={endIconStyle} />}
          sx={{ paddingRight: "0.2vh" }}
        />
        <ButtonMicroscopeFeed
          label="CLASSIFY"
          icon={<CropFreeIcon color="inherit" style={iconStyle} />}
          disabled={isWebcamActive || imageCache.length == 0} // Disable when the webcam is active
          onClick={() => {
            handleInference();
          }}
        />
        <ButtonMicroscopeFeed
          label="D"
          icon={<CropFreeIcon color="inherit" style={iconStyle} />}
          disabled={isWebcamActive || imageCache.length == 0} // Disable when the webcam is active
          onClick={() => {
            handleDirectInference();
          }}
        />
        <ButtonMicroscopeFeed
          label="ANNOTATE"
          icon={<FormatShapesOutlinedIcon color="inherit" style={iconStyle} />}
          disabled={isWebcamActive || imageCache.length == 0} // Disable when the webcam is active
          onClick={() => {
            handleAnnotate();
          }}
        />
      </Box>
      <div
        style={{
          position: "relative",
          width: width,
          height,
          borderTop: `0.01vh solid LightGrey`,
        }}
      >
        {!apiResultDismissed ? (
          // <Overlay>
          <Box
            sx={{
              width: "15vw",
              height: "fit-content",
              zIndex: 30,
              border: `0.01vh solid LightGrey`,
              borderRadius: 1,
              background: colours.CFIA_Background_White,
            }}
            boxShadow={1}
          >
            <ApiAction
              loading={apiLoading}
              success={apiSuccess}
              error={apiError}
              dismiss={() => {
                exitFeedbackMode();
              }}
            />
          </Box>
        ) : // </Overlay>
        null}
        {feedbackMode && scaledFeedbackBox && inferenceForRevision && (
          <>
            <NegativeFeedbackForm
              inference={inferenceForRevision}
              position={scaledFeedbackBox}
              classList={classList}
              onCancel={exitFeedbackMode}
              onSubmit={submitNegativeFeedback}
              isNewAnnotation={isNewAnnotation}
              classListLoading={classListLoading}
            />
            <FreeformBox
              position={scaledFeedbackBox}
              onCancel={exitFeedbackMode}
              onSubmit={handleFreeformSubmit}
            />
          </>
        )}
        {isWebcamActive ? (
          <Webcam
            ref={webcamRef}
            mirrored={false}
            width="100%"
            height="100%"
            style={{ objectFit: "fill" }}
            videoConstraints={{
              width: 1920,
              height: 1080,
              deviceId: activeDeviceId,
            }}
            screenshotFormat="image/png"
            screenshotQuality={1}
            forceScreenshotSourceSize={true}
          />
        ) : (
          <>
            <Box
              component="canvas"
              ref={canvasRef}
              sx={{
                height: "100%",
                width: "100%",
                objectFit: "contain",
              }}
            />
            {!isLoading && (
              <Box
                sx={{
                  height: "100%",
                  width: "100%",
                  position: "absolute",
                  top: 0,
                  left: 0,
                }}
              >
                {imageData !== null &&
                  imageData.boxes.map((box, index) => {
                    return (
                      <ScaledInferenceBox
                        key={index}
                        index={index}
                        box={box}
                        label={
                          String((imageData.scores[index] * 100).toFixed(0)) +
                          "%"
                        }
                        imageWidth={imageData.imageDims[0]}
                        imageHeight={imageData.imageDims[1]}
                        canvasWidth={width}
                        canvasHeight={height}
                        visible={!feedbackMode}
                        submitPositiveFeedback={submitPositiveFeedback}
                        handleNegativeFeedback={enterFeedbackMode}
                      />
                    );
                  })}
              </Box>
            )}
            {isLoading && (
              <div
                style={{
                  position: "absolute",
                  top: 0,
                  left: 0,
                  width: "100%",
                  height: "100%",
                  display: "flex",
                  justifyContent: "center",
                  alignItems: "center",
                  background: "rgba(0, 0, 0, 0.5)", // Darkens the canvas area to make the loader visible
                }}
              >
                <CircularProgress style={{ color: "#FFFFFF" }} />{" "}
                {/* Adjust the color as needed */}
              </div>
            )}
          </>
        )}
      </div>
    </Box>
  );
};

export default MicroscopeFeed;
