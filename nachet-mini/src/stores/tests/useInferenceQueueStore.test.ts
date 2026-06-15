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
    lastInferenceDurationMs: null,
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

    it("does not affect other items", () => {
      getStore().enqueue({ imageSrc: "a.jpg", imageIndex: 0 });
      getStore().enqueue({ imageSrc: "b.jpg", imageIndex: 1 });
      const firstId = getStore().queue[0].id;
      getStore().markProcessing(firstId);
      expect(getStore().queue[1].status).toBe("pending");
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

    it("updates lastInferenceDurationMs", () => {
      getStore().enqueue({ imageSrc: "a.jpg", imageIndex: 0 });
      const id = getStore().queue[0].id;
      getStore().markDone(id, 1234);
      expect(getStore().lastInferenceDurationMs).toBe(1234);
    });

    it("also removes cancelled items in the same update", () => {
      getStore().enqueue({ imageSrc: "a.jpg", imageIndex: 0 });
      getStore().enqueue({ imageSrc: "b.jpg", imageIndex: 1 });
      getStore().enqueue({ imageSrc: "c.jpg", imageIndex: 2 });
      const [firstId, secondId] = getStore().queue.map((i) => i.id);
      getStore().cancel(secondId);
      getStore().markDone(firstId, 500);
      // only the third item should remain
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
    it("updates lastInferenceDurationMs", () => {
      getStore().setLastInferenceDuration(999);
      expect(getStore().lastInferenceDurationMs).toBe(999);
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
    it("returns null when lastInferenceDurationMs is null", () => {
      getStore().enqueue({ imageSrc: "a.jpg", imageIndex: 0 });
      expect(selectEtaMs(getStore())).toBeNull();
    });

    it("returns null when queue is empty", () => {
      getStore().setLastInferenceDuration(1000);
      expect(selectEtaMs(getStore())).toBeNull();
    });

    it("returns duration * pendingCount when no item is processing", () => {
      getStore().setLastInferenceDuration(1000);
      getStore().enqueue({ imageSrc: "a.jpg", imageIndex: 0 });
      getStore().enqueue({ imageSrc: "b.jpg", imageIndex: 1 });
      const eta = selectEtaMs(getStore());
      // 2 pending * 1000ms each
      expect(eta).toBeGreaterThan(0);
      expect(eta).toBeLessThanOrEqual(2000);
    });
  });
});
