import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { render, cleanup } from "@testing-library/react";
import { page } from "vitest/browser";
import { I18nextProvider } from "react-i18next";
import i18n from "../../i18n";
import enMain from "../../locales/en/main";
import { useInferenceQueueStore } from "@stores/useInferenceQueueStore";
import QueueSummary from "../QueueSummary";

const renderSummary = () =>
  render(
    <I18nextProvider i18n={i18n}>
      <QueueSummary />
    </I18nextProvider>,
  );

const makePendingItem = (id: string, imageIndex: number) => ({
  id,
  imageSrc: `img-${imageIndex}.jpg`,
  imageIndex,
  status: "pending" as const,
  addedAt: Date.now(),
  inferenceStartedAt: null,
  detectionDoneAt: null,
  detectedBoxCount: null,
});

const makeProcessingItem = (id: string, imageIndex: number) => ({
  id,
  imageSrc: `img-${imageIndex}.jpg`,
  imageIndex,
  status: "processing" as const,
  addedAt: Date.now(),
  inferenceStartedAt: Date.now(),
  detectionDoneAt: null,
  detectedBoxCount: null,
});

describe("QueueSummary", () => {
  beforeEach(async () => {
    await i18n.changeLanguage("en");
    useInferenceQueueStore.setState({
      queue: [],
      lastDetectionDurationMs: null,
      lastClassificationPerBoxMs: null,
    });
  });

  afterEach(cleanup);

  it("renders nothing when queue is empty", async () => {
    renderSummary();
    await expect.element(page.getByRole("region")).not.toBeInTheDocument();
    // No chips visible
    const chips = await page.getByRole("generic").all();
    expect(chips.length).toBe(0);
  });

  it("shows item count chip when queue has pending items", async () => {
    useInferenceQueueStore.setState({
      queue: [makePendingItem("id-1", 0), makePendingItem("id-2", 1)],
    });
    renderSummary();
    await expect.element(page.getByText(/2 items in queue/i)).toBeVisible();
  });

  it("shows singular form for one item", async () => {
    useInferenceQueueStore.setState({
      queue: [makePendingItem("id-1", 0)],
    });
    renderSummary();
    await expect.element(page.getByText(/1 item in queue/i)).toBeVisible();
  });

  it("shows estimating when no inference has completed yet", async () => {
    useInferenceQueueStore.setState({
      queue: [makePendingItem("id-1", 0)],
    });
    renderSummary();
    await expect
      .element(page.getByText(enMain.inferenceQueue.etaUnknown))
      .toBeVisible();
  });

  it("shows ETA chip when timing data is available", async () => {
    const now = Date.now();
    useInferenceQueueStore.setState({
      queue: [
        {
          id: "id-1",
          imageSrc: "img-0.jpg",
          imageIndex: 0,
          status: "processing",
          addedAt: now - 2000,
          inferenceStartedAt: now - 2000,
          detectionDoneAt: now - 1000,
          detectedBoxCount: 4,
        },
      ],
      lastDetectionDurationMs: 3000,
      lastClassificationPerBoxMs: 500,
    });
    renderSummary();
    await expect.element(page.getByText(/~\d+s/i)).toBeVisible();
  });

  it("counts processing items toward the total", async () => {
    useInferenceQueueStore.setState({
      queue: [makeProcessingItem("id-1", 0), makePendingItem("id-2", 1)],
    });
    renderSummary();
    await expect.element(page.getByText(/2 items in queue/i)).toBeVisible();
  });

  it("hides when all items are done", async () => {
    useInferenceQueueStore.setState({
      queue: [{ ...makePendingItem("id-1", 0), status: "done" as const }],
    });
    renderSummary();
    await expect
      .element(page.getByText(/item in queue/i))
      .not.toBeInTheDocument();
  });
});
