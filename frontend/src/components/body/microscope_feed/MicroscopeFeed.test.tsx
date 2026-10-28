import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import "@testing-library/jest-dom/vitest";
import MicroscopeFeed from "./MicroscopeFeed";
import type { MicroscopeFeedWorkspaceViewProps } from "./MicroscopeFeedWorkspaceView";
import { useImageStore } from "@stores/useImageStore";
import { useInferenceResultsStore } from "@stores/useInferenceResultsStore";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));
vi.mock("@hooks", () => ({
  useSpeciesData: () => ({ speciesData: { seeds: [] }, isLoading: false }),
}));
vi.mock("@auth", () => ({
  useNachetAuth: () => ({ isAuthenticated: true, isLoading: false }),
}));
vi.mock("./MicroscopeFeedControlsView", () => ({
  MicroscopeFeedControlsView: () => null,
}));
vi.mock("./MicroscopeFeedWorkspaceView", () => ({
  MicroscopeFeedWorkspaceView: ({
    imageData,
    inferenceForRevision,
    enterFeedbackMode,
    setScaledFeedbackBox,
  }: MicroscopeFeedWorkspaceViewProps) => (
    <>
      <output data-testid="current-image">
        {imageData?.imageId ?? "none"}
      </output>
      <output data-testid="feedback-box">
        {JSON.stringify(inferenceForRevision?.boxes[0].box)}
      </output>
      <button
        onClick={() =>
          enterFeedbackMode(0, {
            left: 73,
            top: 83,
            minWidth: 73,
            minHeight: 73,
            maxWidth: 73,
            maxHeight: 73,
          })
        }
      >
        Review
      </button>
      <button
        onClick={() =>
          setScaledFeedbackBox({
            left: 146,
            top: 156,
            minWidth: 73,
            minHeight: 73,
            maxWidth: 73,
            maxHeight: 73,
          })
        }
      >
        Move
      </button>
    </>
  ),
}));

const props = {
  webcamRef: { current: null },
  canvasRef: { current: null },
  capture: vi.fn(),
  handleInference: vi.fn(),
  handleDirectInference: vi.fn(),
  isWebcamActive: false,
  isLoading: false,
  onCaptureClick: vi.fn(),
  windowSize: { width: 1000, height: 1000 },
  toggleShowInference: vi.fn(),
  backendUrl: "https://example.test",
  uuid: "user",
};

beforeEach(() => {
  useImageStore.setState({
    images: [
      {
        index: 1,
        imageId: "image-one",
        src: "data:image/png;base64,AA==",
        imageDims: [1000, 1000],
        workflowIds: ["workflow"],
        activeWorkflowId: "workflow",
      },
    ],
    currentIndex: 1,
  });
  useInferenceResultsStore.getState().clearAllResults();
  useInferenceResultsStore.getState().addResult(
    "workflow",
    "image-one",
    {
      filename: "image.png",
      imageId: "image-one",
      inferenceId: "inference",
      boxes: [
        {
          topN: [],
          score: 0.9,
          label: "seed",
          classId: "class",
          objectTypeId: "class",
          boxId: "box",
          box: { topX: 100, topY: 100, bottomX: 200, bottomY: 200 },
          overlapping: false,
          overlappingIndices: 0,
        },
      ],
      labelOccurrence: { seed: 1 },
      totalBoxes: 1,
      models: [],
    },
    "pipeline",
    "Pipeline",
  );
});

describe("Microscope feedback state", () => {
  it("updates feedback coordinates without an effect-driven render loop", () => {
    render(<MicroscopeFeed {...props} />);
    fireEvent.click(screen.getByText("Review"));
    fireEvent.click(screen.getByText("Move"));

    const box = JSON.parse(screen.getByTestId("feedback-box").textContent!);
    expect(box.topX).toBeCloseTo(200);
    expect(box.bottomX).toBeCloseTo(300);
    expect(box.topY).toBeCloseTo(200);
    expect(box.bottomY).toBeCloseTo(300);
  });

  it("drops the displayed inference when the image cache is cleared", () => {
    render(<MicroscopeFeed {...props} />);
    expect(screen.getByTestId("current-image")).toHaveTextContent("image-one");
    act(() => useImageStore.getState().clearImages());
    expect(screen.getByTestId("current-image")).toHaveTextContent("none");
  });

  it("does not display an inference with invalid image dimensions", () => {
    useImageStore.setState({
      images: useImageStore.getState().images.map((image) => ({
        ...image,
        imageDims: [Number.NaN, 1000],
      })),
    });
    render(<MicroscopeFeed {...props} />);
    expect(screen.getByTestId("current-image")).toHaveTextContent("none");
  });
});
