import { describe, it, expect, beforeEach, afterEach } from "vitest";
import {
  render as rtlRender,
  cleanup,
  fireEvent,
} from "@testing-library/react";
import { I18nextProvider } from "react-i18next";
import type { ReactElement } from "react";
import type { InferenceBox, InferenceResult } from "@common/types";
import {
  useInferenceStore,
  boxKey,
  type CamBoxResult,
} from "@stores/useInferenceStore";
import i18n from "../../i18n";
import CamRankToggles from "../CamRankToggles";

// Render through the i18n provider so the component's t() calls resolve to the
// (English by default) translations rather than raw keys.
const render = (ui: ReactElement) =>
  rtlRender(<I18nextProvider i18n={i18n}>{ui}</I18nextProvider>);

const RESULT_KEY = "0:model-a";

const makeBox = (boxId: string): InferenceBox => ({
  inferenceId: "inf-1",
  boxId,
  classId: "class-1",
  label: "wheat",
  isVerified: false,
  bboxSource: "model",
  topX: 0,
  topY: 0,
  bottomX: 10,
  bottomY: 10,
});

const makeResult = (boxIds: string[]): InferenceResult => ({
  scores: [],
  classifications: [],
  boxes: boxIds.map(makeBox),
  topN: [],
  overlapping: [],
  overlappingIndices: [],
  labelOccurrence: {},
  totalBoxes: boxIds.length,
  models: [],
  completedAt: "2024-01-01T00:00:00Z",
  isActive: true,
  minBoxSize: 10,
});

const makeCam = (classCount: number, grid = 2): CamBoxResult => ({
  grid,
  classes: Array.from({ length: classCount }, (_, i) => ({
    classIndex: i,
    label: `species-${i}`,
    score: 1 - i * 0.1,
    heatmap: Array.from({ length: grid * grid }, () => 0),
  })),
});

const seedCam = (boxId: string, classCount: number) => {
  const cams = new Map(useInferenceStore.getState().camResults);
  cams.set(boxKey(0, "model-a", boxId), makeCam(classCount));
  useInferenceStore.setState({ camResults: cams });
};

describe("CamRankToggles", () => {
  beforeEach(() => {
    useInferenceStore.setState({
      camResults: new Map(),
      camRank: new Map(),
      activeResultKey: null,
    });
  });

  afterEach(cleanup);

  it("renders nothing when the run has no CAM data", () => {
    const { container } = render(
      <CamRankToggles resultKey={RESULT_KEY} result={makeResult(["box-1"])} />,
    );
    expect(container.querySelector('[data-testid="cam-rank-0"]')).toBeNull();
  });

  it("renders one toggle per CAM class, labelled Top 1..N", () => {
    seedCam("box-1", 3);
    const { getByTestId } = render(
      <CamRankToggles resultKey={RESULT_KEY} result={makeResult(["box-1"])} />,
    );
    expect(getByTestId("cam-rank-0")).toHaveTextContent("Top 1");
    expect(getByTestId("cam-rank-1")).toHaveTextContent("Top 2");
    expect(getByTestId("cam-rank-2")).toHaveTextContent("Top 3");
  });

  it("derives the rank count from the first box that has CAM data", () => {
    // box-1 has no CAM; box-2 does. Rank count must come from box-2.
    seedCam("box-2", 2);
    const { getByTestId, queryByTestId } = render(
      <CamRankToggles
        resultKey={RESULT_KEY}
        result={makeResult(["box-1", "box-2"])}
      />,
    );
    expect(getByTestId("cam-rank-0")).toBeInTheDocument();
    expect(getByTestId("cam-rank-1")).toBeInTheDocument();
    expect(queryByTestId("cam-rank-2")).toBeNull();
  });

  it("reflects the active rank via aria-pressed", () => {
    seedCam("box-1", 3);
    useInferenceStore.setState({ camRank: new Map([[RESULT_KEY, 1]]) });
    const { getByTestId } = render(
      <CamRankToggles resultKey={RESULT_KEY} result={makeResult(["box-1"])} />,
    );
    expect(getByTestId("cam-rank-0")).toHaveAttribute("aria-pressed", "false");
    expect(getByTestId("cam-rank-1")).toHaveAttribute("aria-pressed", "true");
    expect(getByTestId("cam-rank-2")).toHaveAttribute("aria-pressed", "false");
  });

  it("activates a rank and the run on click", () => {
    seedCam("box-1", 3);
    const { getByTestId } = render(
      <CamRankToggles resultKey={RESULT_KEY} result={makeResult(["box-1"])} />,
    );
    fireEvent.click(getByTestId("cam-rank-2"));
    expect(useInferenceStore.getState().camRank.get(RESULT_KEY)).toBe(2);
    expect(useInferenceStore.getState().activeResultKey).toBe(RESULT_KEY);
  });

  it("clears the overlay when the active rank is clicked again", () => {
    seedCam("box-1", 3);
    useInferenceStore.setState({ camRank: new Map([[RESULT_KEY, 0]]) });
    const { getByTestId } = render(
      <CamRankToggles resultKey={RESULT_KEY} result={makeResult(["box-1"])} />,
    );
    fireEvent.click(getByTestId("cam-rank-0"));
    expect(useInferenceStore.getState().camRank.has(RESULT_KEY)).toBe(false);
  });

  it("toggles via the eye icon button without double-handling the row click", () => {
    seedCam("box-1", 3);
    const { getByLabelText } = render(
      <CamRankToggles resultKey={RESULT_KEY} result={makeResult(["box-1"])} />,
    );
    fireEvent.click(getByLabelText("overlay top 2"));
    // stopPropagation means only the button handler runs, not the row's too;
    // a single toggle leaves rank 1 active rather than cancelling itself out.
    expect(useInferenceStore.getState().camRank.get(RESULT_KEY)).toBe(1);
  });
});
