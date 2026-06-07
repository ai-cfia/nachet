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

  enqueue: (item: Omit<QueuedInferenceItem, "id" | "status" | "addedAt">) => void;
  cancel: (id: string) => void;
  markProcessing: (id: string) => void;
  markDone: (id: string, durationMs: number) => void;
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
      queue: state.queue.map((item) =>
        item.id === id ? { ...item, status: "done" } : item,
      ),
      lastInferenceDurationMs: durationMs,
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

export const selectEtaMs = (state: InferenceQueueState) => {
  const remaining = selectActiveQueue(state).length;
  if (remaining === 0 || state.lastInferenceDurationMs === null) return null;
  return remaining * state.lastInferenceDurationMs;
};
