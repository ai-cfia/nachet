import { describe, it, expect, beforeEach } from "vitest";
import {
  useInferenceQueueStore,
  selectNextPending,
  selectEtaMs,
} from "../useInferenceQueueStore";

const getStore = () => useInferenceQueueStore.getState();

const reset = () =>
  useInferenceQueueStore.setState({
    queue: [],
    lastDetectionDurationMs: null,
    lastClassificationPerBoxMs: null,
  });

describe("useInferenceQueueStore", () => {
  beforeEach(reset);

  // ─── enqueue ────────────────────────────────────────────────────────────────

  describe("enqueue", () => {
    it("adds an item with status pending", () => {
      getStore().enqueue({ imageSrc: "a.jpg", imageIndex: 0 });
      const { queue } = getStore();
      expect(queue).toHaveLength(1);
      expect(queue[0].status).toBe("pending");
      expect(queue[0].imageSrc).toBe("a.jpg");
      expect(queue[0].imageIndex).toBe(0);
    });

    it("assigns a unique id to each item", () => {
      getStore().enqueue({ imageSrc: "a.jpg", imageIndex: 0 });
      getStore().enqueue({ imageSrc: "b.jpg", imageIndex: 1 });
      const { queue } = getStore();
      expect(queue[0].id).not.toBe(queue[1].id);
    });

    it("preserves insertion order", () => {
      getStore().enqueue({ imageSrc: "a.jpg", imageIndex: 0 });
      getStore().enqueue({ imageSrc: "b.jpg", imageIndex: 1 });
      getStore().enqueue({ imageSrc: "c.jpg", imageIndex: 2 });
      const { queue } = getStore();
      expect(queue.map((i) => i.imageIndex)).toEqual([0, 1, 2]);
    });

    it("sets addedAt to a recent timestamp", () => {
      const before = Date.now();
      getStore().enqueue({ imageSrc: "a.jpg", imageIndex: 0 });
      const after = Date.now();
      expect(getStore().queue[0].addedAt).toBeGreaterThanOrEqual(before);
      expect(getStore().queue[0].addedAt).toBeLessThanOrEqual(after);
    });

    it("initializes timing fields to null", () => {
      getStore().enqueue({ imageSrc: "a.jpg", imageIndex: 0 });
      const item = getStore().queue[0];
      expect(item.inferenceStartedAt).toBeNull();
      expect(item.detectionDoneAt).toBeNull();
      expect(item.detectedBoxCount).toBeNull();
    });
  });

  // ─── cancel ─────────────────────────────────────────────────────────────────

  describe("cancel", () => {
    it("marks the item as cancelled", () => {
      getStore().enqueue({ imageSrc: "a.jpg", imageIndex: 0 });
      const id = getStore().queue[0].id;
      getStore().cancel(id);
      expect(getStore().queue[0].status).toBe("cancelled");
    });

    it("does not affect other items", () => {
      getStore().enqueue({ imageSrc: "a.jpg", imageIndex: 0 });
      getStore().enqueue({ imageSrc: "b.jpg", imageIndex: 1 });
      const firstId = getStore().queue[0].id;
      getStore().cancel(firstId);
      expect(getStore().queue[1].status).toBe("pending");
    });

    it("is a no-op for unknown ids", () => {
      getStore().enqueue({ imageSrc: "a.jpg", imageIndex: 0 });
      getStore().cancel("non-existent-id");
      expect(getStore().queue[0].status).toBe("pending");
    });
  });

  // ─── markProcessing ─────────────────────────────────────────────────────────

  describe("markProcessing", () => {
    it("sets the item status to processing", () => {
      getStore().enqueue({ imageSrc: "a.jpg", imageIndex: 0 });
      const id = getStore().queue[0].id;
      getStore().markProcessing(id);
      expect(getStore().queue[0].status).toBe("processing");
    });

    it("sets inferenceStartedAt to a recent timestamp", () => {
      const before = Date.now();
      getStore().enqueue({ imageSrc: "a.jpg", imageIndex: 0 });
      const id = getStore().queue[0].id;
      getStore().markProcessing(id);
      const after = Date.now();
      const { inferenceStartedAt } = getStore().queue[0];
      expect(inferenceStartedAt).not.toBeNull();
      expect(inferenceStartedAt!).toBeGreaterThanOrEqual(before);
      expect(inferenceStartedAt!).toBeLessThanOrEqual(after);
    });

    it("does not affect other items", () => {
      getStore().enqueue({ imageSrc: "a.jpg", imageIndex: 0 });
      getStore().enqueue({ imageSrc: "b.jpg", imageIndex: 1 });
      const firstId = getStore().queue[0].id;
      getStore().markProcessing(firstId);
      expect(getStore().queue[1].status).toBe("pending");
    });
  });

  // ─── markDetectionDone ──────────────────────────────────────────────────────

  describe("markDetectionDone", () => {
    it("sets detectionDoneAt and detectedBoxCount", () => {
      getStore().enqueue({ imageSrc: "a.jpg", imageIndex: 0 });
      const id = getStore().queue[0].id;
      getStore().markProcessing(id);
      const before = Date.now();
      getStore().markDetectionDone(id, 800, 5);
      const after = Date.now();
      const item = getStore().queue[0];
      expect(item.detectedBoxCount).toBe(5);
      expect(item.detectionDoneAt).not.toBeNull();
      expect(item.detectionDoneAt!).toBeGreaterThanOrEqual(before);
      expect(item.detectionDoneAt!).toBeLessThanOrEqual(after);
    });

    it("updates lastDetectionDurationMs", () => {
      getStore().enqueue({ imageSrc: "a.jpg", imageIndex: 0 });
      const id = getStore().queue[0].id;
      getStore().markDetectionDone(id, 800, 5);
      expect(getStore().lastDetectionDurationMs).toBe(800);
    });
  });

  // ─── markDone ───────────────────────────────────────────────────────────────

  describe("markDone", () => {
    it("removes the done item from the queue", () => {
      getStore().enqueue({ imageSrc: "a.jpg", imageIndex: 0 });
      const id = getStore().queue[0].id;
      getStore().markProcessing(id);
      getStore().markDone(id, 1000);
      expect(getStore().queue).toHaveLength(0);
    });

    it("updates lastClassificationPerBoxMs when box count is known", () => {
      getStore().enqueue({ imageSrc: "a.jpg", imageIndex: 0 });
      const id = getStore().queue[0].id;
      getStore().markProcessing(id);
      getStore().markDetectionDone(id, 500, 2);
      // classification took 1000ms for 2 boxes = 500ms per box
      getStore().markDone(id, 1000);
      expect(getStore().lastClassificationPerBoxMs).toBe(500);
    });

    it("does not update lastClassificationPerBoxMs when box count is null", () => {
      getStore().enqueue({ imageSrc: "a.jpg", imageIndex: 0 });
      const id = getStore().queue[0].id;
      getStore().markProcessing(id);
      // no markDetectionDone called — detectedBoxCount stays null
      getStore().markDone(id, 1000);
      expect(getStore().lastClassificationPerBoxMs).toBeNull();
    });

    it("also removes cancelled items in the same update", () => {
      getStore().enqueue({ imageSrc: "a.jpg", imageIndex: 0 });
      getStore().enqueue({ imageSrc: "b.jpg", imageIndex: 1 });
      getStore().enqueue({ imageSrc: "c.jpg", imageIndex: 2 });
      const [firstId, secondId] = getStore().queue.map((i) => i.id);
      getStore().cancel(secondId);
      getStore().markDone(firstId, 500);
      expect(getStore().queue).toHaveLength(1);
      expect(getStore().queue[0].imageIndex).toBe(2);
    });

    it("preserves remaining pending items", () => {
      getStore().enqueue({ imageSrc: "a.jpg", imageIndex: 0 });
      getStore().enqueue({ imageSrc: "b.jpg", imageIndex: 1 });
      const firstId = getStore().queue[0].id;
      getStore().markDone(firstId, 500);
      expect(getStore().queue).toHaveLength(1);
      expect(getStore().queue[0].status).toBe("pending");
    });
  });

  // ─── setLastInferenceDuration ───────────────────────────────────────────────

  describe("setLastInferenceDuration", () => {
    it("updates lastDetectionDurationMs", () => {
      getStore().setLastInferenceDuration(999);
      expect(getStore().lastDetectionDurationMs).toBe(999);
    });
  });

  // ─── clearCompleted ─────────────────────────────────────────────────────────

  describe("clearCompleted", () => {
    it("removes done and cancelled items", () => {
      getStore().enqueue({ imageSrc: "a.jpg", imageIndex: 0 });
      getStore().enqueue({ imageSrc: "b.jpg", imageIndex: 1 });
      getStore().enqueue({ imageSrc: "c.jpg", imageIndex: 2 });
      const [firstId, secondId] = getStore().queue.map((i) => i.id);
      getStore().cancel(firstId);
      getStore().markProcessing(secondId);
      getStore().clearCompleted();
      expect(getStore().queue).toHaveLength(2);
      expect(getStore().queue.map((i) => i.imageIndex)).toEqual([1, 2]);
    });

    it("is a no-op when queue is empty", () => {
      getStore().clearCompleted();
      expect(getStore().queue).toHaveLength(0);
    });
  });

  // ─── selectNextPending ──────────────────────────────────────────────────────

  describe("selectNextPending", () => {
    it("returns the first pending item", () => {
      getStore().enqueue({ imageSrc: "a.jpg", imageIndex: 0 });
      getStore().enqueue({ imageSrc: "b.jpg", imageIndex: 1 });
      const firstId = getStore().queue[0].id;
      getStore().markProcessing(firstId);
      const next = selectNextPending(getStore());
      expect(next?.imageIndex).toBe(1);
    });

    it("returns null when no pending items", () => {
      expect(selectNextPending(getStore())).toBeNull();
    });

    it("skips processing and cancelled items", () => {
      getStore().enqueue({ imageSrc: "a.jpg", imageIndex: 0 });
      getStore().enqueue({ imageSrc: "b.jpg", imageIndex: 1 });
      getStore().enqueue({ imageSrc: "c.jpg", imageIndex: 2 });
      const [firstId, secondId] = getStore().queue.map((i) => i.id);
      getStore().markProcessing(firstId);
      getStore().cancel(secondId);
      expect(selectNextPending(getStore())?.imageIndex).toBe(2);
    });
  });

  // ─── selectEtaMs ────────────────────────────────────────────────────────────

  describe("selectEtaMs", () => {
    it("returns null when no timing data available", () => {
      getStore().enqueue({ imageSrc: "a.jpg", imageIndex: 0 });
      expect(selectEtaMs(getStore())).toBeNull();
    });

    it("returns null when queue is empty", () => {
      useInferenceQueueStore.setState({
        lastDetectionDurationMs: 1000,
        lastClassificationPerBoxMs: 500,
      });
      expect(selectEtaMs(getStore())).toBeNull();
    });

    it("returns null when no item is processing", () => {
      useInferenceQueueStore.setState({
        lastDetectionDurationMs: 1000,
        lastClassificationPerBoxMs: 500,
      });
      getStore().enqueue({ imageSrc: "a.jpg", imageIndex: 0 });
      getStore().enqueue({ imageSrc: "b.jpg", imageIndex: 1 });
      expect(selectEtaMs(getStore())).toBeNull();
    });

    it("returns null on first inference before any timing is learned", () => {
      getStore().enqueue({ imageSrc: "a.jpg", imageIndex: 0 });
      const id = getStore().queue[0].id;
      getStore().markProcessing(id);
      expect(selectEtaMs(getStore())).toBeNull();
    });

    it("returns detection ETA when item is processing and timing is known", () => {
      useInferenceQueueStore.setState({
        lastDetectionDurationMs: 5000,
        lastClassificationPerBoxMs: 100,
      });
      getStore().enqueue({ imageSrc: "a.jpg", imageIndex: 0 });
      const id = getStore().queue[0].id;
      getStore().markProcessing(id);
      const eta = selectEtaMs(getStore());
      expect(eta).not.toBeNull();
      expect(eta!).toBeGreaterThanOrEqual(1000);
      expect(eta!).toBeLessThanOrEqual(5000);
    });

    it("returns classification ETA when detection is done", () => {
      useInferenceQueueStore.setState({
        lastDetectionDurationMs: 5000,
        lastClassificationPerBoxMs: 500,
      });
      getStore().enqueue({ imageSrc: "a.jpg", imageIndex: 0 });
      const id = getStore().queue[0].id;
      getStore().markProcessing(id);
      getStore().markDetectionDone(id, 5000, 4);
      const eta = selectEtaMs(getStore());
      // 4 boxes * 500ms = 2000ms total classification, minus elapsed
      expect(eta).not.toBeNull();
      expect(eta!).toBeGreaterThanOrEqual(1000);
      expect(eta!).toBeLessThanOrEqual(2000);
    });
  });
});
