# Image Store Migration to Zustand

**Date**: 2025-10-31
**Author**: AI Assistant
**Status**: ✅ Complete

## Overview

This document describes the migration of image state management from React's `useState` with prop drilling to a centralized Zustand store pattern. The migration eliminates prop drilling across 4 major component hierarchies and provides a single source of truth for image data.

## Problem Statement

### Before Migration

The image data (`imageCache` and `imageIndex`) was managed in `body.tsx` using React's `useState`:

```typescript
const [imageCache, setImageCache] = useState<Images[]>([]);
const [imageIndex, setImageIndex] = useState<number>(0);
```

This led to extensive prop drilling:

1. **Body → MicroscopeFeed**: `imageCache`, `setImageCache`, `imageIndex`
2. **Body → ImageCache**: `savedImages`, `imageIndex`, `setImageIndex`, `removeImage`, `clearImageCache`
3. **Body → ClassificationResults**: `savedImages`, `imageIndex`
4. **Body → SaveCapturePopup**: `imageCache`, `imageSrc`

**Total props passed**: 12+ image-related props through component hierarchy

### Issues

- **Prop Drilling**: Components in the middle of the hierarchy had to pass props they didn't use
- **Tight Coupling**: Child components were tightly coupled to parent state management
- **Maintenance Burden**: Changes to image state required updating multiple component signatures
- **Code Duplication**: Similar logic repeated across components

## Solution: Zustand Store

### Architecture Decision

We chose Zustand because:

- ✅ Already used in the codebase (`useWorkflowStore`, `useDeviceStore`, `useSpeciesStore`)
- ✅ Simple API with minimal boilerplate
- ✅ TypeScript support out of the box
- ✅ Optional persistence support
- ✅ No provider wrapper needed

### Store Implementation

**Location**: `frontend/src/stores/useImageStore.ts`

```typescript
interface ImageState {
  images: Images[];
  currentIndex: number;
  addCapturedImage: (src: string) => Promise<void>;
  loadInferenceResults: (inferenceData: ApiInferenceData, imageIndex: number) => void;
  removeImage: (index: number) => number;
  clearImages: () => void;
  setImages: (images: Images[]) => void;
  setCurrentIndex: (index: number) => void;
  getCurrentImage: () => Images | undefined;
}
```

#### Key Actions

1. **`addCapturedImage(src: string)`**:
   - Async function that handles image capture/upload
   - Uses `loadCaptureToCache` from utilities
   - Automatically calculates next index
   - Updates both images array and current index

2. **`loadInferenceResults(inferenceData, imageIndex)`**:
   - Integrates ML inference results into stored images
   - Uses `loadResultsToCache` utility
   - Called after successful inference requests

3. **`removeImage(index: number)`**:
   - Removes image from array
   - Calculates next appropriate index to display
   - Returns the new current index

4. **`clearImages()`**:
   - Resets images array and index to initial state

5. **`getCurrentImage()`**:
   - Helper to get current image data
   - Used for deriving `imageSrc` in components

### Persistence Decision

**Decision**: No localStorage persistence

**Rationale**:

- Images are base64-encoded and can be very large (5MB+ each)
- localStorage has ~5MB limit per domain
- Risk of exceeding quota with just a few high-resolution images
- Images are temporary captures, not critical to persist across sessions
- Workflow data is persisted separately in `useWorkflowStore`

**Alternative Considered**: Persist only metadata (index, count) without image data, but this was deemed unnecessary as the workflow store already tracks processing state.

## Migration Details

### Files Changed (6 total)

#### 1. New Store: `useImageStore.ts`

```typescript
export const useImageStore = create<ImageState>()((set, get) => ({
  images: [],
  currentIndex: 0,

  addCapturedImage: async (src: string) => {
    const state = get();
    const nextIndex = nextCacheIndex(state.currentIndex, state.images);
    const newImages = await loadCaptureToCache(src, state.images, nextIndex);
    set({ images: newImages, currentIndex: nextIndex });
  },

  loadInferenceResults: (inferenceData, imageIndex) => {
    const state = get();
    const newImages = loadResultsToCache(inferenceData, state.images, imageIndex);
    set({ images: newImages });
  },

  // ... other actions
}));
```

#### 2. `MicroscopeFeed.tsx`

**Removed Props**:

```typescript
- imageCache: Images[]
- setImageCache: React.Dispatch<React.SetStateAction<Images[]>>
- imageIndex: number
```

**Store Usage**:

```typescript
const {
  images: imageCache,
  currentIndex: imageIndex,
  loadInferenceResults,
} = useImageStore();
```

**Updated**:

- Feedback submission functions now call `loadInferenceResults(response, imageIndex)` instead of `setImageCache(loadResultsToCache(...))`

#### 3. `ImageCache.tsx`

**Removed Props**:

```typescript
- savedImages: any[]
- setImageIndex: React.Dispatch<React.SetStateAction<number>>
- removeImage: (index: number) => void
- clearImageCache: () => void
- imageIndex: number
```

**Store Usage**:

```typescript
const {
  images: savedImages,
  currentIndex: imageIndex,
  setCurrentIndex: setImageIndex,
  removeImage,
  clearImages: clearImageCache,
} = useImageStore();
```

**Result**: Component is now self-contained with no external state dependencies.

#### 4. `ClassificationResults.tsx`

**Removed Props**:

```typescript
- savedImages: any[]
- imageIndex: number
```

**Store Usage**:

```typescript
const { images: savedImages, currentIndex: imageIndex } = useImageStore();
```

**Note**: Still receives `imageSrc` as a prop since it's derived state calculated in `body.tsx` with `useMemo`.

#### 5. `SaveCapturePopup.tsx`

**Removed Props**:

```typescript
- imageSrc: string
- imageCache: Images[]
```

**Store Usage**:

```typescript
const { images: imageCache, getCurrentImage } = useImageStore();

const imageSrc = useMemo(() => {
  const currentImage = getCurrentImage();
  return currentImage?.src ?? "";
}, [getCurrentImage]);
```

**Updated**: Image saving logic now uses local `imageCache` and `imageSrc` from store.

#### 6. `body.tsx` (Main Component)

**Removed State**:

```typescript
- const [imageCache, setImageCache] = useState<Images[]>([]);
- const [imageIndex, setImageIndex] = useState<number>(0);
```

**Removed Functions**:

```typescript
- pushImageToCache(src: string)
- removeFromCache(index: number)
- clearCache()
```

**Added Store Usage**:

```typescript
const {
  images: imageCache,
  currentIndex: imageIndex,
  addCapturedImage,
  loadInferenceResults,
} = useImageStore();
```

**Simplified Functions**:

```typescript
// Before: 10+ lines with state management
const captureFeed = (): void => {
  const src = webcamRef.current?.getScreenshot();
  if (!src) return;
  addCapturedImage(src); // Now just 1 line!
};

const pushImageToCache = (src: string): void => {
  addCapturedImage(src); // Simplified wrapper for UploadPopup
};
```

**Updated Inference Handlers**:

```typescript
// Direct inference (synchronous)
.then((response) => {
  setReadAzureStorage(!readAzureStorage);
  loadInferenceResults(response, imageIndex); // Was: setImageCache(loadResultsToCache(...))
  setModelDisplayName(selectedModel);
})

// Async workflow polling
onComplete: (results) => {
  setReadAzureStorage(!readAzureStorage);
  loadInferenceResults(results, imageIndex); // Was: setImageCache(loadResultsToCache(...))
  setModelDisplayName(selectedModel);
  // ...
}
```

**Kept Derived State**:

```typescript
// These remain in body.tsx as useMemo calculations
const currentImageData = useMemo(() =>
  imageCache.find((img) => img.index === imageIndex),
  [imageCache, imageIndex]
);

const imageSrc = useMemo(() =>
  currentImageData?.src ?? defaultImageSrc,
  [currentImageData, defaultImageSrc]
);

const imageTiff = useMemo(() =>
  currentImageData?.src.includes("image/tiff") ? currentImageData.src : "",
  [currentImageData]
);

const labelOccurrences = useMemo(() =>
  currentImageData ? getLabelOccurrence(currentImageData) : {},
  [currentImageData]
);
```

**Rationale**: These derived values are used by multiple child components and benefit from memoization at the parent level. Moving them to store would complicate the store logic.

## Component Dependency Graph

### Before Migration deux

```text
body.tsx (state: imageCache, imageIndex)
  │
  ├─► MicroscopeFeed (props: imageCache, setImageCache, imageIndex)
  │     └─► [Uses all props]
  │
  ├─► ImageCache (props: savedImages, imageIndex, setImageIndex, removeImage, clearImageCache)
  │     └─► [Uses all props]
  │
  ├─► ClassificationResults (props: savedImages, imageIndex)
  │     └─► [Uses all props]
  │
  └─► SaveCapturePopup (props: imageCache, imageSrc)
        └─► [Uses all props]
```

### After Migration

```text
useImageStore (global state)
  ▲
  │
  ├─ body.tsx (derives: imageSrc, imageTiff, labelOccurrences)
  │    │
  │    └─► MicroscopeFeed (no image props)
  │    └─► ImageCache (no image props)
  │    └─► ClassificationResults (props: imageSrc - derived)
  │    └─► SaveCapturePopup (no image props)
  │
  ├─ MicroscopeFeed → useImageStore()
  ├─ ImageCache → useImageStore()
  ├─ ClassificationResults → useImageStore()
  └─ SaveCapturePopup → useImageStore()
```

**Key Improvement**: Components directly access store instead of receiving props from parent.

## Benefits

### 1. **Eliminated Prop Drilling**

- **Before**: 12+ image-related props passed through hierarchy
- **After**: 0 image props (only derived state like `imageSrc` passed where needed)

### 2. **Cleaner Component Interfaces**

**ImageCache Before**:

```typescript
interface params {
  savedImages: any[];
  setImageIndex: React.Dispatch<React.SetStateAction<number>>;
  removeImage: (index: number) => void;
  clearImageCache: () => void;
  imageIndex: number;
  windowSize: { width: number; height: number };
}
```

**ImageCache After**:

```typescript
const ImageCache: React.FC = () => {
  const { images, currentIndex, setCurrentIndex, removeImage, clearImages } = useImageStore();
  // ...
}
```

### 3. **Single Source of Truth**

- All image state in one place (`useImageStore`)
- No risk of state getting out of sync between components
- Easier debugging with browser devtools

### 4. **Better Maintainability**

- Changes to image state logic only need updates in the store
- No cascading changes through component props
- Clear separation of concerns

### 5. **Consistent Pattern**

- Follows existing patterns (`useWorkflowStore`, `useDeviceStore`, `useSpeciesStore`)
- New developers can understand the pattern quickly
- Easier to extend with new features

### 6. **Improved Testability**

- Store logic can be tested independently
- Components can be tested with mocked store
- No need to mock complex prop chains

## Testing & Validation

### Verification Steps

✅ **ESLint**: All linting checks pass
✅ **TypeScript**: No compilation errors
✅ **Build**: Production build successful
✅ **Tests**: All 246 tests pass across 11 test files

### Test Results

```bash
Test Files  11 passed (11)
     Tests  246 passed (246)
  Start at  01:02:45
  Duration  3.59s (transform 2.23s, setup 1.72s, collect 7.88s, tests 1.74s, environment 5.95s, prepare 156ms)
```

### Manual Testing Checklist

The following operations should be manually tested:

- [ ] **Capture Image**: Click capture button on webcam feed
- [ ] **Upload Image**: Upload image via upload popup
- [ ] **View Images**: Click through images in ImageCache
- [ ] **Delete Image**: Remove individual image from cache
- [ ] **Clear All**: Clear entire image cache
- [ ] **Inference**: Run inference on captured/uploaded image
- [ ] **Workflow Polling**: Verify async inference updates image cache
- [ ] **Feedback**: Submit positive/negative feedback
- [ ] **Save Individual**: Save single image to file
- [ ] **Save All**: Save all images as ZIP
- [ ] **Canvas Rendering**: Verify bounding boxes render correctly
- [ ] **Classification Results**: Verify results display matches selected image

## Migration Pattern

This migration can serve as a template for other state management refactoring:

### Step 1: Create Store

```typescript
// stores/useXStore.ts
export const useXStore = create<XState>()((set, get) => ({
  data: initialData,
  actions: () => { /* ... */ },
}));
```

### Step 2: Update Components

```typescript
// components/Component.tsx
- function Component(props: { data, setData }) {
+ function Component() {
+   const { data, setData } = useXStore();
```

### Step 3: Remove Props from Parent

```typescript
// parent.tsx
- const [data, setData] = useState();
- <Component data={data} setData={setData} />
+ <Component />
```

### Step 4: Verify & Test

- Run linter
- Run type checker
- Run tests
- Manual testing

## Future Considerations

### Potential Enhancements

1. **Store Persistence (Optional)**:
   - Could add persistence for image metadata (not base64 data)
   - Track recently used images or image history

2. **Store Devtools Integration**:
   - Add Zustand devtools middleware for debugging
   - Track state changes and time-travel debugging

3. **Image Caching Strategy**:
   - Implement LRU cache for images
   - Automatic cleanup of old images
   - Memory usage monitoring

4. **Optimistic Updates**:
   - Immediate UI updates before async operations complete
   - Rollback on error

5. **Store Slicing**:
   - If store grows, consider splitting into slices
   - Separate concerns (images, selection, operations)

### Other State to Consider Migrating

Based on this successful migration, consider moving:

1. **Model Selection State**: Currently in `body.tsx`
2. **Device Selection State**: Partially done in `useDeviceStore`, could be completed
3. **Directory State**: `curDir`, `azureStorageDir` state management
4. **UI State**: Popup open/close states could be centralized

## References

- **Zustand Documentation**: <https://github.com/pmndrs/zustand>
- **Existing Stores**:
  - `src/stores/useWorkflowStore.ts`
  - `src/stores/useDeviceStore.ts`
  - `src/stores/useSpeciesStore.ts`
- **Related Files**:
  - `src/common/cacheutils.ts` - Image utilities
  - `src/common/types.d.ts` - Type definitions
  - `CLAUDE.md` - Project documentation

## Conclusion

The migration successfully eliminates prop drilling and provides a clean, maintainable state management solution for images. The pattern can be applied to other state management needs in the application.

**Key Takeaway**: Centralized state management with Zustand reduces complexity, improves maintainability, and follows established patterns in the codebase.
