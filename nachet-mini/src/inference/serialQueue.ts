/**
 * A minimal serial task runner: async tasks submitted to it run strictly one
 * at a time, in submission order, regardless of how quickly they are enqueued.
 *
 * The worker uses this so a `load-models` message can't run concurrently with
 * an in-flight `run-inference` — doing so would release ORT sessions that
 * inference is still using and crash with a "function signature mismatch".
 */
export const createSerialQueue = (): ((task: () => Promise<void>) => void) => {
  // The tail of the chain. Each new task is appended with `.then`, so it only
  // starts once the previous task has settled (fulfilled OR rejected).
  let chain: Promise<void> = Promise.resolve();

  return (task: () => Promise<void>): void => {
    chain = chain.then(task, task);
  };
};
