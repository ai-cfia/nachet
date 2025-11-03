// \components\body\microscope_feed\MicroscopeFeedWorkspaceView.tsx
// Workspace view for MicroscopeFeed component
import { useState } from "react";
import { Box } from "@mui/material";
import CircularProgress from "@mui/material/CircularProgress";
import Webcam from "react-webcam";
import { colours } from "@styles/colours";
import {
  BoxCSS,
  SpeciesData,
  FeedbackDataNegative,
  ImageWithInference,
} from "@common/types";
import { NegativeFeedbackForm } from "../feedback_form";
import ApiAction from "../api_action";
import ScaledInferenceBox from "../scaled_inference_box";
import { useWebcamStore } from "@stores/useWebcamStore";

export interface MicroscopeFeedWorkspaceViewProps {
  // Shared state from parent
  apiResultDismissed: boolean;
  apiLoading: boolean;
  apiSuccess: boolean;
  apiError: string | null;
  feedbackMode: boolean;
  scaledFeedbackBox: BoxCSS | null;
  inferenceForRevision: FeedbackDataNegative | null;
  isNewAnnotation: boolean;
  boxDragEnabled: boolean;
  isWebcamActive: boolean;
  isLoading: boolean;
  imageData: ImageWithInference | null;

  // Dimensions
  windowSize: {
    width: number;
    height: number;
  };

  // Refs
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
  webcamRef: React.RefObject<Webcam | null>;

  // State setters for shared state
  setScaledFeedbackBox: React.Dispatch<React.SetStateAction<BoxCSS | null>>;
  setBoxDragEnabled: React.Dispatch<React.SetStateAction<boolean>>;

  // Callbacks
  exitFeedbackMode: () => void;
  submitNegativeFeedback: (
    feedbackDataNegative: FeedbackDataNegative,
  ) => Promise<void>;
  handleFreeformSubmit: (box: BoxCSS) => void;
  submitPositiveFeedback: (index: number) => Promise<void>;
  enterFeedbackMode: (index: number, boxPosition: BoxCSS) => void;

  // Data
  classList: SpeciesData[];
  classListLoading: boolean;
}

export const MicroscopeFeedWorkspaceView = (
  props: MicroscopeFeedWorkspaceViewProps,
) => {
  const {
    apiResultDismissed,
    apiLoading,
    apiSuccess,
    apiError,
    feedbackMode,
    scaledFeedbackBox,
    inferenceForRevision,
    isNewAnnotation,
    boxDragEnabled,
    isWebcamActive,
    isLoading,
    imageData,
    windowSize,
    canvasRef,
    webcamRef,
    setScaledFeedbackBox,
    setBoxDragEnabled,
    exitFeedbackMode,
    submitNegativeFeedback,
    handleFreeformSubmit,
    submitPositiveFeedback,
    enterFeedbackMode,
    classList,
    classListLoading,
  } = props;

  // Read activeDeviceId from store
  const { activeDeviceId } = useWebcamStore();

  // Local state (only used within workspace)
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

  // Calculate dimensions from windowSize
  const width = windowSize.width * 0.73; // Match 73vw container width
  const height = windowSize.height * 0.75; // Match 75vh container height

  // Helper function to determine resize handle
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

  // Helper function to check if mouse is inside box
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

  // Canvas mouse event handlers
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

  return (
    <Box
      sx={{
        position: "relative",
        width: { xs: "100%", md: "73vw" },
        height: { xs: "50vh", md: "75vh" },
        // minHeight: { xs: "50vh", md: "75vh" },
        // maxHeight: { xs: "50vh", md: "75vh" },
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
          key={activeDeviceId}
          ref={webcamRef}
          mirrored={false}
          width="100%"
          height="100%"
          style={{ objectFit: "fill" }}
          videoConstraints={{
            width: 1920,
            height: 1080,
            deviceId: activeDeviceId ? { exact: activeDeviceId } : undefined,
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
                        String((imageData.scores[index] * 100).toFixed(0)) + "%"
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
    </Box>
  );
};
