import { useRef, useCallback, useEffect } from "react";
import type { BoxCoordinates } from "@common/types";
import type { ModelConfig, WorkerInMessage, WorkerOutMessage } from "./models";
import { useInferenceStore } from "@stores/useInferenceStore";
import { resultKey } from "@stores/useInferenceStore";

/**
 * React hook that manages the inference Web Worker lifecycle.
 *
 * Creates the worker on mount, tears it down on unmount.
 * Translates worker messages into Zustand store updates.
 *
 * Usage:
 *   const { loadModels, runInference, isModelLoaded } = useInference();
 */

export const useInference = (currentIndex: number) => {
  const workerRef = useRef<Worker | null>(null);
  const isModelLoadedRef = useRef(false);

  const setStatus = useInferenceStore((s) => s.setStatus);
  const setResult = useInferenceStore((s) => s.setResult);
  const setActiveResultKey = useInferenceStore((s) => s.setActiveResultKey);
  const setModelLoaded = useInferenceStore((s) => s.setModelLoaded);
  const setModelLoadProgress = useInferenceStore((s) => s.setModelLoadProgress);
  const setError = useInferenceStore((s) => s.setError);

  const currentIndexRef = useRef<number | null>(null);

  // Create worker on mount, terminate on unmount
  useEffect(() => {
    const worker = new Worker(new URL("./worker.ts", import.meta.url), {
      type: "module",
    });

    // Throttle model-progress events. When the worker forwards a big external-
    // data fetch (e.g. SAM3's 1.75 GB vision_encoder.onnx.data), ORT-Web fires
    // progress callbacks dozens of times per second. Pushing every one into
    // the Zustand store re-renders subscribed components fast enough to trip
    // React's "Maximum update depth exceeded" guard. We coalesce to one
    // update per (name, integer-percent) combo and at most one per 2000ms.
    let lastProgressName = "";
    let lastProgressPct = -1;
    let lastProgressTime = 0;
    worker.onmessage = (event: MessageEvent) => {
      const msg = event.data as WorkerOutMessage;
      switch (msg.type) {
        case "model-progress": {
          const pct = Math.floor(msg.progress);
          const now = Date.now();
          const sameAsBefore =
            msg.name === lastProgressName && pct === lastProgressPct;
          const tooSoon = now - lastProgressTime < 2000;
          if (sameAsBefore || (tooSoon && pct < 100)) break;
          lastProgressName = msg.name;
          lastProgressPct = pct;
          lastProgressTime = now;
          setModelLoadProgress({ name: msg.name, progress: msg.progress });
          break;
        }
        case "model-loaded":
          isModelLoadedRef.current = true;
          setStatus("idle");
          setModelLoadProgress(null);
          setModelLoaded(true);
          break;
        case "status":
          setStatus(msg.status);
          break;
        case "partial-result":
          setResult(msg.imageIndex, msg.modelConfigId, msg.result);
          if (msg.imageIndex === currentIndexRef.current) {
            setActiveResultKey(resultKey(msg.imageIndex, msg.modelConfigId));
          }
          break;
        case "result":
          setResult(msg.imageIndex, msg.modelConfigId, msg.result);
          if (msg.imageIndex === currentIndexRef.current) {
            setActiveResultKey(resultKey(msg.imageIndex, msg.modelConfigId));
          }
          setStatus("complete");
          break;
        case "error":
          setError(msg.message);
          setStatus("error");
          break;
      }
    };

    worker.onerror = (err: ErrorEvent) => {
      setError(err.message);
      setStatus("error");
    };

    workerRef.current = worker;
    return () => {
      worker.terminate();
      workerRef.current = null;
      isModelLoadedRef.current = false;
    };
  }, [
    setStatus,
    setResult,
    setActiveResultKey,
    setModelLoaded,
    setModelLoadProgress,
    setError,
  ]);

  /** Download and warm up both pipelines for the given model config. */
  const loadModels = useCallback(
    (config: ModelConfig) => {
      if (!workerRef.current) return;
      isModelLoadedRef.current = false;
      setStatus("loading-model");
      setModelLoaded(false);
      const msg: WorkerInMessage = { type: "load-models", config };
      workerRef.current.postMessage(msg);
    },
    [setStatus, setModelLoaded],
  );

  /**
   * Run detection + classification on an image.
   * The result is written directly to the Zustand store keyed by imageIndex.
   *
   * @param prompt Optional text prompt for text-promptable detectors (SAM3).
   *               Ignored by closed-vocabulary detectors (RT-DETR, DETR).
   */
  const runInference = useCallback(
    (imageSrc: string, imageIndex: number, prompt?: string | null) => {
      if (!workerRef.current || !isModelLoadedRef.current) return;
      const msg: WorkerInMessage = {
        type: "run-inference",
        imageSrc,
        imageIndex,
        prompt,
      };
      workerRef.current.postMessage(msg);
    },
    [],
  );

  /**
   * Run classification only on user-provided boxes (skip detection).
   * Used for re-classifying edited bounding boxes.
   */
  const runClassifyOnly = useCallback(
    (
      imageSrc: string,
      imageIndex: number,
      boxes: BoxCoordinates[],
      modelConfigId: string,
    ) => {
      if (!workerRef.current || !isModelLoadedRef.current) return;
      const msg: WorkerInMessage = {
        type: "run-classify-only",
        imageSrc,
        imageIndex,
        boxes,
        modelConfigId,
      };
      workerRef.current.postMessage(msg);
    },
    [],
  );

  useEffect(() => {
    currentIndexRef.current = currentIndex;
  }, [currentIndex]);

  return {
    loadModels,
    runInference,
    runClassifyOnly,
    /** True after `model-loaded` is received from the worker. */
    get isModelLoaded() {
      return isModelLoadedRef.current;
    },
  };
};
