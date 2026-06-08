import { create } from "zustand";

export interface QueuedInferenceItem {
  id: string;
  imageSrc: string;
  imageIndex: number;
  status: "pending" | "processing" | "done" | "cancelled";
  addedAt: number;
}

interface InferenceQueueState {
  queue: QueuedInferenceItem[];
  lastInferenceDurationMs: number | null;

  enqueue: (
    item: Omit<QueuedInferenceItem, "id" | "status" | "addedAt">,
  ) => void;
  cancel: (id: string) => void;
  markProcessing: (id: string) => void;
  markDone: (id: string, durationMs: number) => void;
  setLastInferenceDuration: (durationMs: number) => void;
  clearCompleted: () => void;
}

export const useInferenceQueueStore = create<InferenceQueueState>()((set) => ({
  queue: [],
  lastInferenceDurationMs: null,

  enqueue: (item) =>
    set((state) => ({
      queue: [
        ...state.queue,
        {
          ...item,
          id: crypto.randomUUID(),
          status: "pending",
          addedAt: Date.now(),
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
        item.id === id ? { ...item, status: "processing" } : item,
      ),
    })),

  markDone: (id, durationMs) =>
    set((state) => ({
      queue: state.queue
        .map(
          (item): QueuedInferenceItem =>
            item.id === id ? { ...item, status: "done" } : item,
        )
        .filter(
          (item) => item.status !== "done" && item.status !== "cancelled",
        ),
      lastInferenceDurationMs: durationMs,
    })),
  setLastInferenceDuration: (durationMs: number) =>
    set({ lastInferenceDurationMs: durationMs }),

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

export const selectEtaMs = (state: InferenceQueueState) => {
  if (state.lastInferenceDurationMs === null) return null;

  const pendingCount = state.queue.filter((i) => i.status === "pending").length;
  const processingItem = state.queue.find((i) => i.status === "processing");

  if (pendingCount === 0 && !processingItem) return null;

  const processingEta = processingItem
    ? Math.max(
        0,
        state.lastInferenceDurationMs - (Date.now() - processingItem.addedAt),
      )
    : 0;

  return processingEta + pendingCount * state.lastInferenceDurationMs;
};
