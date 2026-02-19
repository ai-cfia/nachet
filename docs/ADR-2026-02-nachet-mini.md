# ADR : Nachet Mini - Client-Side Inference UI

## Optional Illustration

| Feature/Aspect             | Option A: Monorepo Shared Package       | Option B: Same App, Different Mode              | Option C: Separate Standalone App        | Option D: Cross-Project Path Aliases     |
|----------------------------|-----------------------------------------|-------------------------------------------------|------------------------------------------|------------------------------------------|
| **Upfront Effort**         | High (extract shared component library) | Medium (add route + inference provider)         | Low (copy ~4 components, new thin shell) | Low (alias paths into frontend/)         |
| **Component Sharing**      | Proper npm package, versioned           | Natural (same codebase)                         | Copy with manual sync                    | Implicit file-level import               |
| **Independent Deployment** | Yes (separate build targets)            | No (single bundle)                              | Yes (static site, no server)             | No (depends on frontend/ structure)      |
| **Bundle Size Impact**     | None (separate packages)                | Risk of bloat without aggressive code-splitting | None (fully separate)                    | None (separate build)                    |
| **Maintenance Burden**     | Low long-term, high setup               | Medium (conditional logic throughout)           | Medium (manual component sync)           | High (fragile cross-project coupling)    |
| **Offline / Static Deploy**| Yes                                     | Requires conditional server removal             | Yes (GitHub Pages, USB drive, CDN)       | Yes                                      |
| **Refactoring of Main App**| Required (extract components)           | Required (add provider abstraction)             | None                                     | None                                     |

## Executive Summary

This ADR evaluates approaches for building Nachet Mini, a lightweight,
standalone version of the Nachet UI that performs image object detection and
classification entirely client-side using transformers.js. Nachet Mini requires
no authentication, no backend server, and no Azure infrastructure. After
evaluating four architectural options, the decision is to create a separate
standalone application in a `nachet-mini/` directory (Option C). This approach
requires the least effort, avoids refactoring the main frontend, and produces an
independently deployable static site suitable for demos, field use, and
environments without network connectivity.

## Context

Nachet is a CFIA AI-powered seed identification system with a React TypeScript
frontend and Python FastAPI backend. The full application requires Azure Blob
Storage, PostgreSQL, Azure ML endpoints, MSAL authentication, and DBOS workflow
orchestration. This infrastructure makes it difficult to run quick demos, use the
tool in offline field scenarios, or provide a lightweight entry point for
evaluating the technology.

There is a need for a minimal version of the UI that:

- Performs object detection and classification entirely in the browser
- Requires no backend server, no authentication, and no cloud infrastructure
- Can be deployed as a static site (GitHub Pages, CDN, USB drive)
- Reuses visual components from the main frontend where practical
- Uses [transformers.js](https://huggingface.co/docs/transformers.js) for
  client-side ML inference with models loaded from Hugging Face Hub

The main frontend is a monolithic SPA (not built as a library). Key display
components (`ScaledInferenceBox`, `ClassificationResults`, `ImageCache`,
`UploadPopup`) are reasonably decoupled from backend APIs, receiving data via
props and Zustand stores. However, the orchestrator (`body.tsx`) and data-
fetching hooks are tightly coupled to the backend. The application uses 12
Zustand stores, MSAL authentication throughout, and Material-UI for its
component library.

## Decision

Create a separate standalone application in `nachet-mini/` (Option C). This is
an independent Vite + React + TypeScript application with its own `package.json`
and build configuration. It copies a small number of display components from the
main frontend (~4 components, ~500-800 lines) and implements a new thin
application shell with transformers.js integration for client-side inference.

### Proposed Structure

```text
nachet-mini/
├── public/
├── src/
│   ├── components/
│   │   ├── InferenceOverlay/     # Adapted from ScaledInferenceBox
│   │   ├── ResultsTable/         # Adapted from ClassificationResults
│   │   ├── ImageUpload/          # Adapted from UploadPopup
│   │   └── ImageGallery/         # Adapted from ImageCache
│   ├── inference/
│   │   ├── worker.ts             # Web Worker for transformers.js
│   │   ├── pipeline.ts           # Detection + classification pipeline
│   │   └── models.ts             # Model registry and loading config
│   ├── stores/
│   │   ├── useImageStore.ts      # Local image state
│   │   └── useInferenceStore.ts  # Inference results state
│   ├── App.tsx                   # Minimal shell (no auth, no routing)
│   └── main.tsx
├── package.json
├── vite.config.ts
├── tsconfig.json
└── index.html
```

### Transformers.js Integration

Client-side inference uses `@huggingface/transformers` with the following
approach:

- **Object detection**: DETR, RT-DETR, or YOLOS (architectures natively
  supported by transformers.js). Standard YOLO (v5/v8) is not natively
  supported and would require manual ONNX conversion with custom
  post-processing.
- **Image classification**: Swin Transformer or ViT (both supported). The
  existing Nachet Swin classifiers are convertible to ONNX via Hugging Face
  Optimum.
- **Model loading**: Models fetched from Hugging Face Hub on first use, then
  cached via the browser Cache API. Quantized models (q8 for WASM, fp16 for
  WebGPU) keep downloads in the 20-100 MB range per model.
- **Execution backend**: WebGPU when available (~70%+ browser support) with
  automatic WASM fallback for full compatibility.
- **Web Worker**: All inference runs in a dedicated Web Worker to keep the UI
  thread responsive.

```typescript
// Simplified inference flow
const device = navigator.gpu ? 'webgpu' : 'wasm';
const dtype = device === 'webgpu' ? 'fp16' : 'q8';

const detector = await pipeline('object-detection', 'model-id', { device, dtype });
const classifier = await pipeline('image-classification', 'model-id', { device, dtype });

// Detection -> Classification pipeline
const detections = await detector(image, { threshold: 0.5 });
for (const det of detections) {
  const crop = cropImage(image, det.box);
  const classification = await classifier(crop, { topk: 5 });
  det.classifications = classification;
}
```

### Components Adapted from Main Frontend

| Component              | Source                          | Adaptations Required                         |
|------------------------|---------------------------------|----------------------------------------------|
| Bounding box overlay   | `ScaledInferenceBox.tsx`        | Remove feedback API calls, simplify menu     |
| Results table          | `ClassificationResults.tsx`     | Remove workflow/backend references           |
| Image upload           | `UploadPopup.tsx`               | Keep validation, remove Azure storage logic  |
| Image gallery          | `ImageCache.tsx`                | Keep thumbnail display, simplify store usage |

### What is Not Included

Nachet Mini intentionally excludes:

- Authentication (MSAL, Azure AD)
- Backend API communication (axios client, workflow polling)
- Azure Blob Storage integration
- DBOS workflow orchestration
- Feedback submission
- Directory/folder management
- Device/microscope management
- Batch upload workflows
- Ensemble model support (single detection + classification pipeline only)
- i18n (can be added later if needed)

## Alternatives Considered

### Option A: Monorepo with Shared Component Package

Extract reusable components into a `packages/ui-components/` library consumed by
both `frontend/` and `nachet-mini/` via pnpm workspaces or Turborepo.

**Pros:**

1. **Proper sharing**: Components published as a versioned npm package, no code
   duplication.
2. **Clean dependency management**: Each app declares explicit dependency on the
   shared package.
3. **Scales well**: If more apps need the same components, they are already
   available.

**Cons:**

1. **High upfront effort**: Requires extracting components from the monolithic
   frontend, setting up monorepo tooling, and restructuring imports.
2. **Refactoring risk**: Modifying the main frontend to consume from an external
   package risks introducing regressions.
3. **Premature abstraction**: Only ~4 components need sharing. The overhead of a
   shared package is not justified until more consumers exist.
4. **Slower iteration**: Changes to shared components require building and
   publishing the package before consumers can use them.

### Option B: Same App, Different Mode

Add a `/mini` route or build-time flag to the existing frontend that skips
authentication and uses a local inference provider backed by transformers.js.

**Pros:**

1. **No code duplication**: Shared components used naturally within the same
   codebase.
2. **Single build pipeline**: One CI/CD configuration, one test suite.
3. **Easier to maintain**: Changes to display components automatically apply to
   both modes.

**Cons:**

1. **Bundle bloat**: transformers.js and ONNX runtime WASM binaries would be
   included in the main bundle unless aggressively code-split with
   `React.lazy`.
2. **Conditional complexity**: Auth guards, API calls, and provider selection
   would require conditional logic throughout the codebase.
3. **Cannot deploy independently**: The mini version cannot be deployed as a
   standalone static site without the full app infrastructure.
4. **Tight coupling**: Changes to the full app (auth flow, API layer) could
   accidentally break the mini mode.

### Option D: Cross-Project Path Aliases

Configure Vite path aliases in `nachet-mini/` to import directly from
`../frontend/src/components/`.

**Pros:**

1. **No code duplication**: Components imported directly from source.
2. **Low setup effort**: Just Vite alias configuration.

**Cons:**

1. **Fragile coupling**: Any restructuring of `frontend/src/` breaks
   nachet-mini imports silently.
2. **Implicit dependency**: nachet-mini depends on frontend's `node_modules`
   (Material-UI, emotion, etc.) without declaring them.
3. **Build complexity**: TypeScript path resolution, Vite module resolution, and
   dependency hoisting all need careful alignment.
4. **Not suitable beyond prototyping**: Too brittle for anything that needs
   reliability.

## Consequences

### Positive Outcomes

1. **Zero impact on main frontend**: No refactoring, no new dependencies, no
   risk of regressions in the production application.
2. **Independently deployable**: Nachet Mini builds to a static site deployable
   on GitHub Pages, a CDN, or a USB drive with no server infrastructure.
3. **Fast to prototype**: Copying ~4 components and writing a thin app shell is
   achievable in days, not weeks.
4. **Offline-capable**: Once models are cached, the entire application works
   without network connectivity.
5. **Clear scope boundary**: The separate codebase makes it obvious what Nachet
   Mini does and does not support.

### Negative Outcomes

1. **Component divergence**: Copied components will drift from their main
   frontend counterparts over time unless manually synchronized.
2. **No ensemble models**: Transformers.js runs single models. The full Nachet
   pipeline's ensemble logic is not supported client-side.
3. **Model conversion required**: Existing Nachet ML models must be exported to
   ONNX and validated for accuracy after quantization. This is a prerequisite
   before Nachet Mini can use domain-specific models.
4. **Accuracy validation**: Quantized models (q8, q4) may have reduced accuracy
   compared to server-side inference. For regulatory use cases, this must be
   validated thoroughly.
5. **Large initial download**: Users must download 20-100 MB of model files per
   model on first use. A two-stage pipeline (detection + classification) means
   two separate downloads.
6. **Browser compatibility**: WebGPU acceleration requires Chrome/Edge. Users on
   Firefox or Safari fall back to WASM (CPU), which is significantly slower for
   large models.

### Migration Path

If Nachet Mini proves valuable and the shared component surface grows, the
project can graduate to Option A (monorepo with shared package) by:

1. Extracting the common components into `packages/ui-components/`
2. Updating both `frontend/` and `nachet-mini/` to consume from the package
3. Removing the duplicated component copies from `nachet-mini/`

This migration is incremental and does not need to happen upfront.

## References

- <https://huggingface.co/docs/transformers.js>
- <https://huggingface.co/docs/transformers.js/guides/webgpu>
- <https://huggingface.co/docs/optimum/en/exporters/onnx/usage_guides/export_a_model>
- <https://developer.mozilla.org/en-US/docs/Web/API/WebGPU_API>
- <https://onnxruntime.ai/docs/tutorials/web/>
- <https://huggingface.co/models?pipeline_tag=object-detection&library=transformers.js>
- <https://huggingface.co/models?pipeline_tag=image-classification&library=transformers.js>
