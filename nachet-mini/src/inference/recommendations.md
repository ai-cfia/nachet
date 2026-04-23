# worker.ts — Unit Testing Recommendations

## What's in worker.ts

There are three distinct categories of code:

**Pure functions — testable right now, no refactor needed:**

- `buildLabelOccurrence(classifications)` — pure string→count reducer
- `emptyResult(config)` — pure object construction
- `patchProcessorSize(processor)` — mutates the input object based on its shape
- `makeProgressCallback(phase)` — returns a closure with throttle logic

**Browser-API functions — testable in browser mode with mocks:**

- `cropRegion(bitmap, xmin, ymin, xmax, ymax)` — uses `OffscreenCanvas` + `URL.createObjectURL`, both real in Chromium
- `getDevice()` — checks `navigator.gpu`, easily stubbed

**ML-coupled orchestration — not unit testable as written:**

- The `addEventListener("message", ...)` handler mixes model loading, inference calls, and result assembly all in one closure, using module-level mutable state (`detectorModel`, `classifierProcessor`, etc.)

---

## What you can do today

**Step 1 — extract the pure helpers** into a sibling file:

```text
src/inference/workerUtils.ts   ← buildLabelOccurrence, emptyResult, patchProcessorSize, makeProgressCallback
src/inference/worker.ts        ← imports from workerUtils, unchanged logic
```

Those four functions are pure or near-pure. They can be imported and tested with regular Vitest (jsdom or browser) — no worker, no transformers.js, no mocking.

**Step 2 — test `cropRegion` in browser mode**, since `OffscreenCanvas` is available in Chromium. You'd pass a real `ImageBitmap` created from a small test image and assert the returned URL is a valid blob URL.

---

## Why the message handler is hard

The handler has two structural issues that make unit testing it expensive:

1. **Module-level mutable state** — `detectorModel`, `classifierProcessor`, `loadedConfig`, etc. are `let` variables at module scope. Reloading state between tests requires either `vi.resetModules()` (slow) or passing the state as parameters.

2. **Untree-shakeable `@huggingface/transformers` calls** — `vi.mock('@huggingface/transformers')` would work in principle, but the mock would need to return plausible tensor objects (with `.dims`, `.data`, `.tolist()`, etc.) for every code path, which is substantial scaffolding.

---

## Recommendation

Extract `workerUtils.ts` now — those four functions have real logic worth protecting (the throttle in `makeProgressCallback`, the `max_height`/`max_width` → `longest_edge` patch in `patchProcessorSize`, the sentinel-skipping in `buildLabelOccurrence`). That's the part where a bug could silently produce wrong results.

The message handler orchestration is better covered by integration/E2E tests that load real (small) models, which gives you confidence the whole pipeline connects without the scaffolding cost of mocking tensors.
