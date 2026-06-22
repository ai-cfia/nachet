import { create } from "zustand";

export interface QueuedInferenceItem {
  id: string;
  imageSrc: string;
  imageIndex: number;
  status: "pending" | "processing" | "done" | "cancelled";
  addedAt: number;
  inferenceStartedAt: number | null; // set when processing starts
  detectionDoneAt: number | null; // set when detection completes
  detectedBoxCount: number | null; // set when detection completes
}

interface InferenceQueueState {
  queue: QueuedInferenceItem[];
  lastDetectionDurationMs: number | null;
  lastClassificationPerBoxMs: number | null;

  enqueue: (
    item: Omit<
      QueuedInferenceItem,
      | "id"
      | "status"
      | "addedAt"
      | "inferenceStartedAt"
      | "detectionDoneAt"
      | "detectedBoxCount"
    >,
  ) => void;
  cancel: (id: string) => void;
  markProcessing: (id: string) => void;
  markDetectionDone: (id: string, durationMs: number, boxCount: number) => void;
  markDone: (id: string, classificationDurationMs: number) => void;
  setLastInferenceDuration: (durationMs: number) => void;
  clearCompleted: () => void;
}

export const useInferenceQueueStore = create<InferenceQueueState>()((set) => ({
  queue: [],
  lastDetectionDurationMs: null,
  lastClassificationPerBoxMs: null,

  enqueue: (item) =>
    set((state) => ({
      queue: [
        ...state.queue,
        {
          ...item,
          id: crypto.randomUUID(),
          status: "pending",
          addedAt: Date.now(),
          inferenceStartedAt: null,
          detectionDoneAt: null,
          detectedBoxCount: null,
        },
      ],
    })),

  cancel: (id) =>
    set((state) => ({
      queue: state.queue.map((item) =>
        item.id === id ? { ...item, status: "cancelled" } : item,
      ),
    })),

  markProcessing: (id) =>
    set((state) => ({
      queue: state.queue.map((item) =>
        item.id === id
          ? { ...item, status: "processing", inferenceStartedAt: Date.now() }
          : item,
      ),
    })),

  markDetectionDone: (id, durationMs, boxCount) =>
    set((state) => ({
      queue: state.queue.map(
        (item): QueuedInferenceItem =>
          item.id === id
            ? {
                ...item,
                detectionDoneAt: Date.now(),
                detectedBoxCount: boxCount,
              }
            : item,
      ),
      lastDetectionDurationMs: durationMs,
    })),

  markDone: (id, classificationDurationMs) =>
    set((state) => {
      const item = state.queue.find((i) => i.id === id);
      const boxCount = item?.detectedBoxCount ?? null;
      const perBoxMs =
        boxCount && boxCount > 0 ? classificationDurationMs / boxCount : null;

      return {
        queue: state.queue
          .map(
            (i): QueuedInferenceItem =>
              i.id === id ? { ...i, status: "done" } : i,
          )
          .filter((i) => i.status !== "done" && i.status !== "cancelled"),
        lastClassificationPerBoxMs:
          perBoxMs ?? state.lastClassificationPerBoxMs,
      };
    }),

  setLastInferenceDuration: (durationMs: number) =>
    set((state) => ({
      lastDetectionDurationMs: durationMs,
      lastClassificationPerBoxMs: state.lastClassificationPerBoxMs,
    })),

  clearCompleted: () =>
    set((state) => ({
      queue: state.queue.filter(
        (item) => item.status !== "done" && item.status !== "cancelled",
      ),
    })),
}));

// Selectors
export const selectActiveQueue = (state: InferenceQueueState) =>
  state.queue.filter(
    (item) => item.status === "pending" || item.status === "processing",
  );

export const selectNextPending = (state: InferenceQueueState) =>
  state.queue.find((item) => item.status === "pending") ?? null;

export const selectIsClassifying = (state: InferenceQueueState): boolean => {
  const processingItem = state.queue.find((i) => i.status === "processing");
  return (
    processingItem !== undefined && processingItem.detectionDoneAt !== null
  );
};

export const selectEtaMs = (state: InferenceQueueState): number | null => {
  const { lastDetectionDurationMs, lastClassificationPerBoxMs } = state;
  const processingItem = state.queue.find((i) => i.status === "processing");
  if (!processingItem) return null;

  // Don't show ETA until we have learned from at least one completed inference
  if (lastDetectionDurationMs === null || lastClassificationPerBoxMs === null)
    return null;

  const detectionDoneAt = processingItem.detectionDoneAt;
  const isClassifying = detectionDoneAt !== null;

  if (isClassifying && processingItem.detectedBoxCount !== null) {
    const elapsedClassification = Date.now() - detectionDoneAt;
    const totalClassification =
      lastClassificationPerBoxMs * processingItem.detectedBoxCount;
    return Math.max(1000, totalClassification - elapsedClassification);
  } else {
    const elapsed = processingItem.inferenceStartedAt
      ? Date.now() - processingItem.inferenceStartedAt
      : 0;
    return Math.max(1000, lastDetectionDurationMs - elapsed);
  }
};
