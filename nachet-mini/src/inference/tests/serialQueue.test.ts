import { describe, it, expect } from "vitest";
import { createSerialQueue } from "../serialQueue";

/** A promise plus its resolver, for controlling task timing in tests. */
const deferred = () => {
  let resolve!: () => void;
  const promise = new Promise<void>((res) => {
    resolve = res;
  });
  return { promise, resolve };
};

/** Flush pending microtasks and one macrotask turn. */
const flush = () => new Promise<void>((r) => setTimeout(r, 0));

describe("createSerialQueue", () => {
  it("runs tasks one at a time, in submission order", async () => {
    const run = createSerialQueue();
    const events: string[] = [];
    const first = deferred();

    run(async () => {
      events.push("start1");
      await first.promise;
      events.push("end1");
    });
    run(async () => {
      events.push("start2");
    });

    await flush();
    // The second task must not begin while the first is still pending.
    expect(events).toEqual(["start1"]);

    first.resolve();
    await flush();
    expect(events).toEqual(["start1", "end1", "start2"]);
  });

  it("continues to the next task even if a task rejects", async () => {
    const run = createSerialQueue();
    const events: string[] = [];

    run(async () => {
      events.push("a");
      throw new Error("boom");
    });
    run(async () => {
      events.push("b");
    });

    await flush();
    expect(events).toEqual(["a", "b"]);
  });

  it("does not start a model load until an in-flight inference finishes", async () => {
    // The exact race from the review: switching models mid-inference must wait.
    const run = createSerialQueue();
    const order: string[] = [];
    const inference = deferred();

    run(async () => {
      order.push("inference:start");
      await inference.promise;
      order.push("inference:end");
    });
    run(async () => {
      order.push("load:start");
    });

    await flush();
    expect(order).toEqual(["inference:start"]); // load is still blocked

    inference.resolve();
    await flush();
    expect(order).toEqual(["inference:start", "inference:end", "load:start"]);
  });
});
