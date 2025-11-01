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
// import FormatShapesOutlinedIcon from "@mui/icons-material/FormatShapesOutlined";
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
import { useMsal, useIsAuthenticated, useAccount } from "@azure/msal-react";
import { InteractionStatus } from "@azure/msal-browser";
import { acquireAccessToken } from "@common/auth";
import { getUnscaledCoordinates } from "@common/imageutils";
import { NegativeFeedbackForm } from "../feedback_form";
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
  onFreeformBoxChange?: (box: BoxCSS | null, dragEnabled: boolean) => void;
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
    onFreeformBoxChange,
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

  const width = windowSize.width * 0.73; // Match 73vw container width
  const height = windowSize.height * 0.75; // Match 75vh container height

  // Find the model name from metadata based on selectedModel (pipeline_id)
  const selectedModelName = useMemo(() => {
    const model = metadata.find((m) => m.pipeline_id === selectedModel);
    return model?.model_name || selectedModel;
  }, [metadata, selectedModel]);

  // const defaultBoxPosition: BoxCSS = {
  //   minWidth: 100,
  //   minHeight: 100,
  //   maxWidth: 100,
  //   maxHeight: 100,
  //   left: width / 2 - 50,
  //   top: height / 2 - 50,
  // };

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
  const [boxDragEnabled, setBoxDragEnabled] = useState<boolean>(true);
  const [boxChangesSaved, setBoxChangesSaved] = useState<boolean>(true);
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [isResizing, setIsResizing] = useState<boolean>(false);
  const [resizeHandle, setResizeHandle] = useState<string>("none");
  const [dragStart, setDragStart] = useState<{ x: number; y: number }>({
    x: 0,
    y: 0,
  });
  const [boxStart, setBoxStart] = useState<BoxCSS | null>(null);
  const [canvasCursor, setCanvasCursor] = useState<string>("default");

  const { instance: msalInstance, inProgress } = useMsal();
  const isAuthenticated = useIsAuthenticated();
  const accountInfo = useAccount();
  const { speciesData, isLoading: classListLoading } = useSpeciesData(
    backendUrl,
    apiScopeClaim,
  );

  // Derive isGuest from accountInfo
  // acct === 0 means member account, acct !== 0 or undefined means guest account
  // Defensive: treat missing/undefined acct as guest (hide D button)
  const isGuest = (() => {
    const idTokenClaims = accountInfo?.idTokenClaims as
      | { acct?: number }
      | undefined;
    const acctClaim = idTokenClaims?.acct;

    // Only acct === 0 means member (show D button)
    // Everything else (undefined, null, non-zero) means guest (hide D button)
    return acctClaim !== 0;
  })();

  const classList: SpeciesData[] = useMemo(() => {
    if (!speciesData?.seeds) return [];
    return speciesData.seeds.map((seed, index) => ({
      ...seed,
      id: index,
    }));
  }, [speciesData]);

  // Notify parent when freeform box or drag state changes
  useEffect(() => {
    if (onFreeformBoxChange && feedbackMode) {
      onFreeformBoxChange(scaledFeedbackBox, boxDragEnabled);
    } else if (onFreeformBoxChange && !feedbackMode) {
      onFreeformBoxChange(null, true);
    }
  }, [scaledFeedbackBox, boxDragEnabled, feedbackMode, onFreeformBoxChange]);

  // Update inferenceForRevision box coordinates when scaledFeedbackBox changes
  useEffect(() => {
    if (
      feedbackMode &&
      scaledFeedbackBox &&
      inferenceForRevision &&
      imageData
    ) {
      const unscaledBox = getUnscaledCoordinates(
        width,
        height,
        imageData.imageDims[0],
        imageData.imageDims[1],
        scaledFeedbackBox,
      );

      setInferenceForRevision({
        ...inferenceForRevision,
        boxes: [
          {
            ...inferenceForRevision.boxes[0],
            box: unscaledBox,
          },
        ],
      });
    }
  }, [
    scaledFeedbackBox,
    feedbackMode,
    imageData,
    width,
    height,
    inferenceForRevision,
  ]);

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

  // const handleAnnotate = () => {
  //   setIsNewAnnotation(true);
  //   enterFeedbackMode(imageIndex, defaultBoxPosition);
  // };

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
    setIsDragging(false);
    setIsResizing(false);
  };

  const getResizeHandle = (
    mouseX: number,
    mouseY: number,
    box: BoxCSS,
  ): string => {
    if (boxDragEnabled || !box) return "none";

    const HANDLE_SIZE = 10;
    const boxX = box.left;
    const boxY = box.top;
    const boxWidth = box.minWidth;
    const boxHeight = box.minHeight;

    // Check corners first
    if (
      Math.abs(mouseX - boxX) < HANDLE_SIZE &&
      Math.abs(mouseY - boxY) < HANDLE_SIZE
    )
      return "top-left";
    if (
      Math.abs(mouseX - (boxX + boxWidth)) < HANDLE_SIZE &&
      Math.abs(mouseY - boxY) < HANDLE_SIZE
    )
      return "top-right";
    if (
      Math.abs(mouseX - (boxX + boxWidth)) < HANDLE_SIZE &&
      Math.abs(mouseY - (boxY + boxHeight)) < HANDLE_SIZE
    )
      return "bottom-right";
    if (
      Math.abs(mouseX - boxX) < HANDLE_SIZE &&
      Math.abs(mouseY - (boxY + boxHeight)) < HANDLE_SIZE
    )
      return "bottom-left";

    // Check edges
    if (
      mouseX >= boxX &&
      mouseX <= boxX + boxWidth &&
      Math.abs(mouseY - boxY) < HANDLE_SIZE
    )
      return "top";
    if (
      mouseX >= boxX &&
      mouseX <= boxX + boxWidth &&
      Math.abs(mouseY - (boxY + boxHeight)) < HANDLE_SIZE
    )
      return "bottom";
    if (
      mouseY >= boxY &&
      mouseY <= boxY + boxHeight &&
      Math.abs(mouseX - boxX) < HANDLE_SIZE
    )
      return "left";
    if (
      mouseY >= boxY &&
      mouseY <= boxY + boxHeight &&
      Math.abs(mouseX - (boxX + boxWidth)) < HANDLE_SIZE
    )
      return "right";

    return "none";
  };

  const isInsideBox = (
    mouseX: number,
    mouseY: number,
    box: BoxCSS,
  ): boolean => {
    if (!box) return false;
    return (
      mouseX >= box.left &&
      mouseX <= box.left + box.minWidth &&
      mouseY >= box.top &&
      mouseY <= box.top + box.minHeight
    );
  };

  const handleCanvasMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!feedbackMode || !scaledFeedbackBox) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    console.log("Mouse down:", {
      mouseX,
      mouseY,
      box: scaledFeedbackBox,
      boxDragEnabled,
    });

    const handle = getResizeHandle(mouseX, mouseY, scaledFeedbackBox);
    const inside = isInsideBox(mouseX, mouseY, scaledFeedbackBox);

    console.log("Handle:", handle, "Inside:", inside);

    if (handle !== "none") {
      console.log("Starting resize");
      setIsResizing(true);
      setResizeHandle(handle);
      setDragStart({ x: mouseX, y: mouseY });
      setBoxStart(scaledFeedbackBox);
      setBoxChangesSaved(false);
    } else if (inside && boxDragEnabled) {
      console.log("Starting drag");
      setIsDragging(true);
      setDragStart({ x: mouseX, y: mouseY });
      setBoxStart(scaledFeedbackBox);
      setBoxChangesSaved(false);
    }
  };

  const handleCanvasMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    if (!feedbackMode || !scaledFeedbackBox) return;

    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    if (isDragging && boxStart) {
      const deltaX = mouseX - dragStart.x;
      const deltaY = mouseY - dragStart.y;
      const displayWidth = rect.width;
      const displayHeight = rect.height;

      const newLeft = Math.max(
        0,
        Math.min(displayWidth - boxStart.minWidth, boxStart.left + deltaX),
      );
      const newTop = Math.max(
        0,
        Math.min(displayHeight - boxStart.minHeight, boxStart.top + deltaY),
      );

      console.log("Dragging:", { deltaX, deltaY, newLeft, newTop });

      setScaledFeedbackBox({
        ...boxStart,
        left: newLeft,
        top: newTop,
      });
    } else if (isResizing && boxStart) {
      const deltaX = mouseX - dragStart.x;
      const deltaY = mouseY - dragStart.y;

      let newLeft = boxStart.left;
      let newTop = boxStart.top;
      let newWidth = boxStart.minWidth;
      let newHeight = boxStart.minHeight;

      switch (resizeHandle) {
        case "top-left":
          newLeft = boxStart.left + deltaX;
          newTop = boxStart.top + deltaY;
          newWidth = boxStart.minWidth - deltaX;
          newHeight = boxStart.minHeight - deltaY;
          break;
        case "top-right":
          newTop = boxStart.top + deltaY;
          newWidth = boxStart.minWidth + deltaX;
          newHeight = boxStart.minHeight - deltaY;
          break;
        case "bottom-right":
          newWidth = boxStart.minWidth + deltaX;
          newHeight = boxStart.minHeight + deltaY;
          break;
        case "bottom-left":
          newLeft = boxStart.left + deltaX;
          newWidth = boxStart.minWidth - deltaX;
          newHeight = boxStart.minHeight + deltaY;
          break;
        case "top":
          newTop = boxStart.top + deltaY;
          newHeight = boxStart.minHeight - deltaY;
          break;
        case "bottom":
          newHeight = boxStart.minHeight + deltaY;
          break;
        case "left":
          newLeft = boxStart.left + deltaX;
          newWidth = boxStart.minWidth - deltaX;
          break;
        case "right":
          newWidth = boxStart.minWidth + deltaX;
          break;
      }

      // Enforce minimum size
      if (newWidth >= 20 && newHeight >= 20) {
        setScaledFeedbackBox({
          ...boxStart,
          left: newLeft,
          top: newTop,
          minWidth: newWidth,
          minHeight: newHeight,
          maxWidth: newWidth,
          maxHeight: newHeight,
        });
      }
    } else {
      // Update cursor based on hover position
      const handle = getResizeHandle(mouseX, mouseY, scaledFeedbackBox);
      if (handle !== "none") {
        const cursors: Record<string, string> = {
          none: "default",
          top: "ns-resize",
          right: "ew-resize",
          bottom: "ns-resize",
          left: "ew-resize",
          "top-right": "nesw-resize",
          "bottom-right": "nwse-resize",
          "bottom-left": "nesw-resize",
          "top-left": "nwse-resize",
        };
        setCanvasCursor(cursors[handle] || "default");
      } else if (
        isInsideBox(mouseX, mouseY, scaledFeedbackBox) &&
        boxDragEnabled
      ) {
        setCanvasCursor("move");
      } else {
        setCanvasCursor("default");
      }
    }
  };

  const handleCanvasMouseUp = () => {
    setIsDragging(false);
    setIsResizing(false);
    setResizeHandle("none");
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
            family: "",
            genus: "",
            species: "",
            name_code: "",
          },
        ],
      });
    } else {
      // Find matching species data for the existing box
      const matchingSeed = classList.find(
        (seed) => seed.seed_id === imageData.boxes[index].classId,
      );

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
            family: matchingSeed?.family || "",
            genus: matchingSeed?.genus || "",
            species: matchingSeed?.species || "",
            name_code: matchingSeed?.name_code || "",
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
        minWidth: "73vw",
        minHeight: "80vh",
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
        {!isGuest && (
          <ButtonMicroscopeFeed
            label="D"
            icon={<CropFreeIcon color="inherit" style={iconStyle} />}
            disabled={isWebcamActive || imageCache.length == 0} // Disable when the webcam is active
            onClick={() => {
              handleDirectInference();
            }}
          />
        )}
        {/* <ButtonMicroscopeFeed
          label="ANNOTATE"
          icon={<FormatShapesOutlinedIcon color="inherit" style={iconStyle} />}
          disabled={isWebcamActive || imageCache.length == 0} // Disable when the webcam is active
          onClick={() => {
            handleAnnotate();
          }}
        /> */}
      </Box>
      <div
        style={{
          position: "relative",
          width: "73vw",
          height: "75vh",
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
          <NegativeFeedbackForm
            inference={inferenceForRevision}
            classList={classList}
            onCancel={exitFeedbackMode}
            onSubmit={submitNegativeFeedback}
            isNewAnnotation={isNewAnnotation}
            classListLoading={classListLoading}
            dragEnabled={boxDragEnabled}
            onToggleDragResize={() => setBoxDragEnabled(!boxDragEnabled)}
            onSaveBox={() => {
              handleFreeformSubmit(scaledFeedbackBox);
              setBoxChangesSaved(true);
            }}
            boxChangesSaved={boxChangesSaved}
          />
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
              onMouseDown={handleCanvasMouseDown}
              onMouseMove={handleCanvasMouseMove}
              onMouseUp={handleCanvasMouseUp}
              onMouseLeave={handleCanvasMouseUp}
              sx={{
                height: "100%",
                width: "100%",
                objectFit: "contain",
                cursor: canvasCursor,
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
                  pointerEvents: feedbackMode ? "none" : "auto",
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
