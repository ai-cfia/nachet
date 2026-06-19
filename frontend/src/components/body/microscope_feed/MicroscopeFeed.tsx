// \components\body\microscope_feed\index.tsx
// MicroscopeFeed
import Webcam from "react-webcam";
import { useEffect, useMemo, useState } from "react";
import { Box } from "@mui/material";
import { useTranslation } from "react-i18next";
import {
  BoxCSS,
  SpeciesData,
  FeedbackDataNegative,
  FeedbackDataPositive,
  ImageWithInference,
} from "@common/types";
import { sendNegativeFeedback, sendPositiveFeedback } from "@common";
import { useSpeciesData } from "@hooks";
import { getUnscaledCoordinates } from "@common/imageutils";
import { useImageStore } from "@stores/useImageStore";
import { useNotificationStore } from "@stores/useNotificationStore";
import { useInferenceResultsStore } from "@stores/useInferenceResultsStore";
import { MicroscopeFeedControlsView } from "./MicroscopeFeedControlsView";
import { MicroscopeFeedWorkspaceView } from "./MicroscopeFeedWorkspaceView";
import { useNachetAuth } from "../../../auth";

interface MicroscopeFeedProps {
  webcamRef: React.RefObject<Webcam | null>;
  capture: () => void;
  canvasRef: React.RefObject<HTMLCanvasElement | null>;
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
}

const MicroscopeFeed = (props: MicroscopeFeedProps) => {
  const {
    webcamRef,
    capture,
    canvasRef,
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
  } = props;

  const { t } = useTranslation("main");

  const { images: imageCache, currentIndex: imageIndex } = useImageStore();
  const getResult = useInferenceResultsStore((state) => state.getResult);

  const { addWarning } = useNotificationStore();

  const width = windowSize.width * 0.73; // Match 73vw container width
  const height = windowSize.height * 0.75; // Match 75vh container height

  // const defaultBoxPosition: BoxCSS = {
  //   minWidth: 100,
  //   minHeight: 100,
  //   maxWidth: 100,
  //   maxHeight: 100,
  //   left: width / 2 - 50,
  //   top: height / 2 - 50,
  // };

  const [imageData, setImageData] = useState<ImageWithInference | null>(null);
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

  const { isAuthenticated, isLoading: authLoading } = useNachetAuth();
  const { speciesData, isLoading: classListLoading } =
    useSpeciesData(backendUrl);

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

  const submitPositiveFeedback = async (index: number) => {
    if (!isAuthenticated) {
      setApiError(t("microscopeFeed.errors.signInRequired"));
      setApiResultDismissed(false);
      return;
    }

    if (imageData == null) {
      return;
    }
    console.log("Submitting positive feedback for key: ", index);

    if (authLoading) {
      addWarning(t("microscopeFeed.errors.authInProgress"), 8000);
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
      await sendPositiveFeedback({
        feedbackData: feedbackDataPositive,
        backendUrl,
      });
      console.log("Positive Feedback submitted successfully");
      // TODO: Update active inference result with feedback response
      // Need to implement update logic for useInferenceResultsStore
      setApiSuccess(true);
    } catch (error) {
      console.error(
        "Error submitting feedback:",
        error instanceof Error ? error.message : String(error),
      );
      setApiError(error instanceof Error ? error.message : "Unknown error");
    } finally {
      setApiLoading(false);
    }
  };

  const submitNegativeFeedback = async (
    feedbackDataNegative: FeedbackDataNegative,
  ) => {
    if (!isAuthenticated) {
      setApiError(t("microscopeFeed.errors.signInRequired"));
      setApiResultDismissed(false);
      return;
    }

    if (authLoading) {
      setApiError(t("microscopeFeed.errors.authInProgress"));
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
      await sendNegativeFeedback({
        feedbackData: feedbackDataNegative,
        backendUrl,
      });
      console.log("Negative Feedback submitted successfully");
      // TODO: Update active inference result with feedback response
      // Need to implement update logic for useInferenceResultsStore
      setApiSuccess(true);
    } catch (error) {
      console.error(
        "Error submitting feedback:",
        error instanceof Error ? error.message : String(error),
      );
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
            nameCode: "",
          },
        ],
      });
    } else {
      // Find matching species data for the existing box
      const matchingSeed = classList.find(
        (seed) => seed.seedId === imageData.boxes[index].classId,
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
            nameCode: matchingSeed?.nameCode || "",
          },
        ],
      });
    }

    toggleShowInference(false);
    setFeedbackMode(true);
  };

  useEffect(() => {
    if (imageCache.length > 0) {
      const image = imageCache.find((img) => img.index === imageIndex);
      if (!image) {
        setImageData(null);
        return;
      }

      // Get active inference result
      const activeWorkflowId = image.activeWorkflowId;
      if (!activeWorkflowId) {
        setImageData(null);
        return;
      }

      const activeResult = getResult(activeWorkflowId);
      if (!activeResult) {
        setImageData(null);
        return;
      }

      // Check if we have valid inference data
      if (
        activeResult.scores.length > 0 &&
        activeResult.boxes.length > 0 &&
        activeResult.classifications.length > 0 &&
        image.imageDims[0] > 0
      ) {
        // Merge image with inference result
        const mergedImageData: ImageWithInference = {
          ...image,
          annotated: true,
          scores: activeResult.scores,
          classifications: activeResult.classifications,
          boxes: activeResult.boxes,
          topN: activeResult.topN,
          overlapping: activeResult.overlapping,
          overlappingIndices: activeResult.overlappingIndices,
        };
        setImageData(mergedImageData);
      } else {
        setImageData(null);
      }
    }
  }, [imageIndex, imageCache, getResult]);
  return (
    <Box
      sx={{
        minWidth: { xs: "100%", md: "73vw" },
        minHeight: { xs: "50vh", md: "80vh" },
        maxHeight: { xs: "50vh", md: "80vh" },
        border: `0.01vh solid LightGrey`,
        borderRadius: "0.4vh",
      }}
      boxShadow={0}
      data-testid="microscope-component"
    >
      <MicroscopeFeedControlsView
        isWebcamActive={isWebcamActive}
        capture={capture}
        onCaptureClick={onCaptureClick}
        handleInference={handleInference}
        handleDirectInference={handleDirectInference}
      />
      <MicroscopeFeedWorkspaceView
        apiResultDismissed={apiResultDismissed}
        apiLoading={apiLoading}
        apiSuccess={apiSuccess}
        apiError={apiError}
        feedbackMode={feedbackMode}
        scaledFeedbackBox={scaledFeedbackBox}
        inferenceForRevision={inferenceForRevision}
        isNewAnnotation={isNewAnnotation}
        boxDragEnabled={boxDragEnabled}
        isWebcamActive={isWebcamActive}
        isLoading={isLoading}
        imageData={imageData}
        windowSize={windowSize}
        canvasRef={canvasRef}
        webcamRef={webcamRef}
        setScaledFeedbackBox={setScaledFeedbackBox}
        setBoxDragEnabled={setBoxDragEnabled}
        exitFeedbackMode={exitFeedbackMode}
        submitNegativeFeedback={submitNegativeFeedback}
        handleFreeformSubmit={handleFreeformSubmit}
        submitPositiveFeedback={submitPositiveFeedback}
        enterFeedbackMode={enterFeedbackMode}
        classList={classList}
        classListLoading={classListLoading}
      />
    </Box>
  );
};

export default MicroscopeFeed;
