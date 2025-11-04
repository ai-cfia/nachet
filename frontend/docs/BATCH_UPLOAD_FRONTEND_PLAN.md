# Batch Upload Frontend Implementation Plan

**Date:** 2025-10-31
**Status:** 🚧 In Progress (Phases 1-5.5 Complete - 75% Done)
**Related:** See `backend/docs/BATCH_UPLOAD_IMPLEMENTATION_PLAN.md` for backend specification

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current State Analysis](#current-state-analysis)
3. [Critical Mismatches with Backend](#critical-mismatches-with-backend)
4. [API Contract Overview](#api-contract-overview)
5. [Implementation Phases](#implementation-phases)
6. [Technical Implementation Details](#technical-implementation-details)
7. [Testing Strategy](#testing-strategy)
8. [Timeline & Effort Estimation](#timeline--effort-estimation)
9. [Risk Mitigation](#risk-mitigation)

---

## Executive Summary

### 🎉 Implementation Progress: 75% Complete (Phases 1-5.5 Done)

**Completed on 2025-10-31:**

- ✅ Phase 1: Seed Lookup Utility (1h)
- ✅ Phase 2: Type Definitions Update (1h)
- ✅ Phase 3: API Client Updates (2h)
- ✅ Phase 4: Folder Store & Selection UI (2h)
- ✅ Phase 5: Queue-Based Async Workflow Implementation (3h)
- ✅ Phase 5.5: Folder Creation with Get-or-Create Pattern (3h)

**Remaining Work:**

- ⏳ Phase 6: Error Handling (1h)
- ⏳ Phase 7: Testing (3h)

**Deliverables Ready:**

- `frontend/src/utils/seedLookup.ts` + tests (12 tests passing)
- Updated TypeScript types and Zod schemas
- Refactored API client functions (`batchUploadImage`, `batchUploadInit`, `createOrGetFolder`)
- New Zustand folder store + `useFolderData` hook
- `useBatchUploadStore` for upload state persistence
- `BatchUploadQueueManager` service for sequential upload processing
- Updated `BatchUploadPopup.tsx` with:
  - Folder creation UI (parent selection, path preview, create button)
  - Queue integration for async uploads
  - Get-or-create folder pattern (idempotent)
- **Backend:** `POST /folders` endpoint with get-or-create logic
- **All linting passed** (ESLint + TypeScript + Ruff + Pyright)
- **Build successful** (TypeScript + Vite)

**Next Steps:** Phases 6-7 (Error handling refinements, testing)

### Context

The backend batch upload feature (Phases 1-5) has been completed and tested. However, the current frontend implementation is incompatible with the new backend API contract. This document outlines a comprehensive plan to update the frontend to work with the async workflow-based batch upload system.

### Key Changes Required

1. **API Contract:** Transform request payload from taxonomic fields to `seed_id`
2. **Response Handling:** Change from synchronous boolean to async workflow tracking
3. **Folder Selection:** Switch from `folder_name` to `folder_id` (must exist before upload)
4. **Workflow Polling:** Implement status polling for each image upload
5. **Error Handling:** Handle duplicates, session expiration, and seed validation

### 🎉 Excellent News: Seeds Already Loaded

The frontend **already loads seeds automatically** via the `useSpeciesData` hook:

- ✅ `useSpeciesData` hook fetches seeds on mount
- ✅ Already used in `BatchUploadPopup.tsx` line 103
- ✅ Stores in Zustand (`useSpeciesStore`)
- ✅ Has caching, loading, and error states
- ✅ Type definitions (`SpeciesData`) complete

**Impact:** Phase 1 reduced from 2h to **1h** (only need lookup utility), total effort reduced from 14h to **13h**

### Phase 1 Success Criteria

- Frontend successfully uploads batches using backend API
- Each image tracked via workflow polling (30s avg Defender scan time)
- Duplicate detection displays gracefully
- Session expiration handled with clear error messages
- 90%+ test coverage for new functionality

---

## Current State Analysis

### Existing Frontend Implementation

**Location:** `frontend/src/components/body/batch_upload_popup/BatchUploadPopup.tsx`

**Current Behavior:**

- Sends taxonomic fields (`family`, `genus`, `species`, `name_code`) directly to backend
- Expects synchronous `boolean` response
- Treats upload as immediate success/failure
- No workflow polling implementation

### Existing Seed Infrastructure (Already Active!)

**✅ Excellent News:** The frontend already has **fully functional** seed management that's actively being used!

**Active Components:**

1. **Custom Hook:** `frontend/src/hooks/useSpeciesData.ts`
   - Automatically fetches seeds on component mount
   - Handles authentication, loading, and error states
   - Caches data to prevent duplicate API calls
   - **Already in use in `BatchUploadPopup.tsx` line 103**

2. **Zustand Store:** `frontend/src/stores/useSpeciesStore.ts`
   - Stores `ApiSpeciesData` globally
   - Provides `speciesData`, `isLoading`, `error` states
   - Already populated by `useSpeciesData` hook

3. **API Function:** `frontend/src/common/api.ts:636-665`
   - `requestClassList()` calls `GET /seeds` endpoint
   - Returns validated `ApiSpeciesData`
   - Called automatically by `useSpeciesData` hook

4. **Type Definitions:** `frontend/src/common/types.d.ts:90-102`
   - `SpeciesData` interface includes all taxonomic fields
   - Already has `seed_id` field ✅
   - Includes `family`, `genus`, `species`, `name_code`

**Current Status:** Seeds are **already being fetched and cached** when `BatchUploadPopup` mounts. No initialization needed!

**Solution:** Simply create a utility function `getSeedIdByTaxonomy()` to query the existing cached data.

**Current API Client:** `frontend/src/common/api.ts:716-820`

```typescript
// Current implementation (INCOMPATIBLE)
export const batchUploadImage = async ({
  backendUrl,
  data,
  accessToken,
}: {
  backendUrl: string;
  data: BatchUploadMetadata;
  accessToken: string;
}): Promise<boolean> => {
  // ← Returns boolean
  // ... sends family, genus, species, name_code, container_name, user_id
  const response = await handleAxios<unknown>(request);
  return validateApiResponse(
    BooleanResponseSchema, // ← Expects boolean
    response,
    "batchUploadImage",
  );
};
```

**Current Type Definition:** `frontend/src/common/types.d.ts:119-134`

```typescript
export interface BatchUploadMetadata {
  containerName: string; // ← Backend doesn't expect
  uuid: string; // ← Backend doesn't expect (user_id)
  family: string; // ← Backend doesn't expect
  genus: string; // ← Backend doesn't expect
  species: string; // ← Backend doesn't expect
  nameCode: string; // ← Backend doesn't expect
  trayCode: string;
  sampleId: string;
  deviceBrandId: string;
  deviceModelId: string;
  deviceLensId: string;
  magnification: number;
  imageDataUrl: string;
  sessionId: string;
}
```

---

## Critical Mismatches with Backend

### 1. Request Payload Mismatch

| Field            | Frontend Sends | Backend Expects | Status     |
| ---------------- | -------------- | --------------- | ---------- |
| `container_name` | ✅ Sent        | ❌ Not expected | **Remove** |
| `user_id`        | ✅ Sent        | ❌ Not expected | **Remove** |
| `family`         | ✅ Sent        | ❌ Not expected | **Remove** |
| `genus`          | ✅ Sent        | ❌ Not expected | **Remove** |
| `species`        | ✅ Sent        | ❌ Not expected | **Remove** |
| `name_code`      | ✅ Sent        | ❌ Not expected | **Remove** |
| `seed_id`        | ❌ Not sent    | ✅ Required     | **Add**    |
| `session_id`     | ✅ Sent        | ✅ Expected     | ✅ OK      |
| `tray_code`      | ✅ Sent        | ✅ Expected     | ✅ OK      |
| `sample_id`      | ✅ Sent        | ✅ Expected     | ✅ OK      |
| `device_*_id`    | ✅ Sent        | ✅ Expected     | ✅ OK      |
| `magnification`  | ✅ Sent        | ✅ Expected     | ✅ OK      |
| `image`          | ✅ Sent        | ✅ Expected     | ✅ OK      |

### 2. Response Format Mismatch

**Frontend Expects:**

```typescript
Promise<boolean>;
```

**Backend Returns:**

```typescript
{
  success: boolean,
  picture_id: string | null,
  workflow_id: string | null,  // For async polling
  error: string | null
}
```

### 3. Workflow Pattern Mismatch

**Frontend Current:**

- Synchronous: Submit → Immediate response → Mark success/failure

**Backend Implements:**

- Asynchronous: Submit → Get `workflow_id` → Poll status → Mark complete when done

### 4. Session Initialization Mismatch

**Frontend Assumes:**

- Session created with `folder_name` (created if doesn't exist)

**Backend Requires:**

- Session created with `folder_id` (folder MUST exist)

---

## API Contract Overview

### Backend Endpoints

#### POST `/new-batch-import`

**Request:**

```json
{
  "folder_id": "g76jk9lm-1234-5678-90ab-cdef12345678",
  "file_count": 25
}
```

**Response:**

```json
{
  "session_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7"
}
```

**Constraints:**

- `folder_id` must exist in database
- `folder_id` must belong to authenticated user's organization
- `file_count` max 1000
- Session expires after 24 hours

#### POST `/upload-picture`

**Request:**

```json
{
  "session_id": "7c9e6679-7425-40de-944b-e07fc1f90ae7",
  "seed_id": "abc12345-def6-7890-ghij-klmnopqrstuv",
  "tray_code": "A",
  "sample_id": "SAMPLE-2025-001",
  "device_brand_id": "...",
  "device_model_id": "...",
  "device_lens_id": "...",
  "magnification": 10.5,
  "image": "data:image/png;base64,..."
}
```

**Response (Success):**

```json
{
  "success": true,
  "picture_id": "image-uuid",
  "workflow_id": "dbos-workflow-uuid",
  "error": null
}
```

**Response (Duplicate):**

```json
{
  "success": false,
  "picture_id": "existing-image-uuid",
  "workflow_id": null,
  "error": "Duplicate image detected: existing-image-uuid"
}
```

**Response (Session Expired):**

```json
{
  "success": false,
  "picture_id": null,
  "workflow_id": null,
  "error": "Session expired (24-hour limit exceeded)"
}
```

#### GET `/workflow/{workflow_id}/status`

**Response:**

```json
{
  "workflow_id": "...",
  "overall_status": "pending" | "processing" | "completed" | "failed",
  "processing_workflow": {
    "status": "defender_scanning" | "sanitizing" | ...,
    "progress_percentage": 75
  }
}
```

---

## Implementation Phases

### Phase 1: Create Seed Lookup Utility (1h) ✅ COMPLETED

**Goal:** Create utility function to map taxonomic fields to `seed_id` from already-cached data

**Status:** ✅ **COMPLETED** - 2025-10-31

**Deliverables:**

- ✅ `frontend/src/utils/seedLookup.ts` - Seed lookup utility with 3 functions
- ✅ `frontend/src/utils/seedLookup.test.ts` - Unit tests (12 tests, all passing)
- ✅ Integrated into `BatchUploadPopup.tsx` line 467-477

**Key Functions Implemented:**

- `getSeedIdByTaxonomy()` - Converts taxonomy to seed_id
- `seedExists()` - Non-throwing validation function
- `getAllSeeds()` - Access all cached seeds

**Technical Notes:**

- Leverages existing `useSpeciesStore` infrastructure
- No API calls needed (data already cached by `useSpeciesData` hook)
- Full TypeScript type safety with proper error handling

---

### Phase 2: Type Definitions Update (1h) ✅ COMPLETED

**Goal:** Update TypeScript interfaces and Zod schemas for new API contract

**Status:** ✅ **COMPLETED** - 2025-10-31

**Deliverables:**

- ✅ `frontend/src/common/types.d.ts` - Updated interfaces
  - Modified `BatchUploadMetadata` (removed 6 fields, added `seedId`)
  - Added `BatchUploadImageResponse`
  - Added `BatchUploadInitRequest`
  - Added `BatchUploadInitResponse`
- ✅ `frontend/src/common/validation.ts` - Added Zod schemas
  - `BatchUploadImageResponseSchema`
  - `BatchUploadInitResponseSchema`
- ✅ TypeScript compilation successful
- ✅ All tests passing (253 tests)

**Technical Notes:**

- Breaking change: Old `BatchUploadMetadata` format incompatible with new
- Full type safety maintained throughout codebase
- Zod schemas provide runtime validation

---

### Phase 3: API Client Updates (2h) ✅ COMPLETED

**Goal:** Update API functions to match backend contract

**Status:** ✅ **COMPLETED** - 2025-10-31

**Deliverables:**

- ✅ `frontend/src/common/api.ts` - Updated API functions
  - **`batchUploadInit()`**: Changed from `folderName`+`containerUuid` to `folderId`
  - **`batchUploadImage()`**: Changed return type to `Promise<BatchUploadImageResponse>`
  - Request payload uses `seed_id` instead of taxonomic fields
  - Response includes `success`, `picture_id`, `workflow_id`, `error`
- ✅ `frontend/src/common/tests/api.test.ts` - Updated 60 API tests (all passing)
  - Updated mock data to match new format
  - Replaced old field validation tests with `seedId` validation
  - Updated expected request/response structures

**Technical Notes:**

- Breaking API change: Incompatible with old backend
- Full validation coverage maintained
- Error messages updated to reflect new fields (e.g., "Seed ID is null or empty")

---

### Phase 4: Create Folder Store & Selection UI (2h) ✅ COMPLETED

**Goal:** Create Zustand store for folders and add folder selection UI

**Status:** ✅ **COMPLETED** - 2025-10-31

**Deliverables:**

- ✅ `frontend/src/stores/useFolderStore.ts` - Zustand store for folder data
- ✅ `frontend/src/hooks/useFolderData.ts` - Custom hook to fetch folders on mount
- ✅ `frontend/src/hooks/index.tsx` - Updated to export `useFolderData`
- ✅ `frontend/src/components/body/batch_upload_popup/BatchUploadPopup.tsx` - Updated with:
  - Folder selection dropdown (Material-UI Autocomplete) at line 645-672
  - Folder validation before session init (line 410-414)
  - Integration with `useFolderData` hook (line 106)
  - Session init uses `folderId` instead of `folderName` (line 421)
  - Seed lookup integration (line 467-477)
  - Duplicate detection handling (line 505-509)

**Technical Notes:**

- Follows exact `useSpeciesStore` + `useSpeciesData` architecture pattern
- Folders automatically fetched on authentication
- Global state makes folders accessible to all components
- UI uses Autocomplete with helpful text when no folders available
- Type-safe folder selection with TypeScript

---

### Phase 5: Queue-Based Async Workflow Implementation (3h) ✅ COMPLETED

**Goal:** Implement queue manager pattern for batch uploads with persistent state and background processing

**Status:** ✅ **COMPLETED** - 2025-10-31

**Deliverables:**

- ✅ `frontend/src/stores/useBatchUploadStore.ts` - Zustand store for batch upload state persistence
  - Session tracking (`BatchSessionInfo`) with completed/failed counts
  - Upload workflow tracking (`UploadWorkflowInfo`) per file
  - Global state persists across modal close/reopen
  - Automatic session progress calculation
- ✅ `frontend/src/services/BatchUploadQueueManager.ts` - Queue manager following WorkflowQueueManager pattern
  - Sequential file upload processing (one at a time)
  - Workflow status polling (20s initial delay + 10s intervals)
  - File-to-base64 conversion with FileReader
  - Error handling for failed uploads
  - Cleanup on unmount
- ✅ `frontend/src/components/body/batch_upload_popup/BatchUploadPopup.tsx` - Integration complete
  - Queue manager singleton with useRef (persists across renders)
  - Session creation in Zustand store
  - Enqueue files instead of inline processing
  - Display upload status from Zustand store
  - Progress bar with completion stats
  - File list with per-file status (queued, processing, completed, failed)
  - Background processing continues even when modal closes
- ✅ TypeScript compilation successful (all linting passed)

**Architecture Pattern (Following Inference Workflows):**

**Key Components:**

1. **BatchUploadQueueManager** (Service Layer)
   - Non-reactive, imperative queue processing
   - Maintains internal queue of `QueueItem[]`
   - Processes uploads one at a time (prevents overwhelming backend)
   - Polls workflow status after upload submission
   - Terminal states: "completed", "failed"

2. **useBatchUploadStore** (Global State)
   - Zustand store for persistence across component lifecycle
   - Tracks batch session (`sessionId`, `totalFiles`, `completedFiles`, `failedFiles`)
   - Tracks individual upload workflows (status, error, queuePosition)
   - Enables modal close/reopen without losing progress

3. **Integration Pattern:**

```typescript
// Queue manager singleton persists across renders
const queueManagerRef = useRef<BatchUploadQueueManager>(
  new BatchUploadQueueManager(),
);

// Configure on session init
queueManagerRef.current.configure({
  backendUrl,
  accessToken,
  uploadStore: { addUpload, updateUploadStatus, setUploadResult, removeUpload },
  onComplete: (workflowId, file, results) => {
    /* ... */
  },
  onError: (workflowId, file, error) => {
    /* ... */
  },
});

// Enqueue all files
files.forEach((file) => {
  queueManagerRef.current.enqueue(file, metadata);
});

// Cleanup on unmount
useEffect(() => {
  const queueManager = queueManagerRef.current;
  return () => queueManager.clear();
}, []);
```

**Benefits of Queue Pattern:**

- **Background Processing:** Uploads continue even when modal is closed
- **Resume Capability:** Reopen modal to see progress (state in Zustand store)
- **Sequential Processing:** One upload at a time prevents backend overload
- **Persistent State:** Global Zustand store maintains progress across renders
- **Consistent Architecture:** Follows same pattern as inference workflows
- **Error Recovery:** Failed uploads tracked, can be retried
- **Memory Efficient:** Files processed sequentially, not all at once

**Technical Notes:**

- Polling intervals: 20s initial delay (for Defender scan), then 10s
- Queue size displayed in UI with position tracking
- File-to-base64 conversion handled by queue manager
- Workflow status polling uses existing `getWorkflowStatus` API
- Integration follows exact pattern of `WorkflowQueueManager` + `useWorkflowStore`

**Implementation Files:**

- `frontend/src/stores/useBatchUploadStore.ts` (216 lines) - Global state management
- `frontend/src/services/BatchUploadQueueManager.ts` (401 lines) - Queue processing service
- `frontend/src/components/body/batch_upload_popup/BatchUploadPopup.tsx` (updated) - UI integration

**Key Differences from Inline Polling Approach:**

| Aspect           | Old Approach (Planned)                 | New Approach (Implemented)           |
| ---------------- | -------------------------------------- | ------------------------------------ |
| **Processing**   | All files in parallel with Promise.all | Sequential queue (one at a time)     |
| **State**        | Component local state                  | Global Zustand store                 |
| **Persistence**  | Lost on modal close                    | Persists across modal close/reopen   |
| **Polling**      | Inline in component                    | Encapsulated in service layer        |
| **Architecture** | Component-level logic                  | Service layer + global state         |
| **Pattern**      | Custom implementation                  | Follows WorkflowQueueManager pattern |

---

### Phase 5.5: Folder Creation with Get-or-Create Pattern (3h) ✅ COMPLETED

**Goal:** Add folder creation UI to batch upload with path preview and get-or-create API endpoint

**Status:** ✅ **COMPLETED** - 2025-10-31

**Key Backend Rules to Propagate:**

This phase implements frontend validation that **exactly matches** the existing backend folder validation system documented in `backend/app/service/directory.py:142-232`. The backend already has comprehensive path validation that we must mirror:

1. **Path Validation Pattern:** `^[a-zA-Z0-9/_.\-]+[a-zA-Z0-9]$`
   - Allows: alphanumeric, slash `/`, underscore `_`, dash `-`, period `.`
   - Must end with alphanumeric (not `_`, `-`, or `.`)
   - No consecutive slashes `//`
   - Frontend sends relative path (no leading `/`), backend prepends `/{org_prefix}/`

2. **Existing Backend Methods to Reuse:**
   - `DirectoryService._validate_and_parse_fullpath()` - Path validation logic (line 142-232)
   - `DirectoryService.create_directory()` - Folder creation pattern (line 320-383)
   - `RbacService.get_user_org_roles()` - Get org_prefix automatically

3. **Backend Tests Document Valid/Invalid Patterns:**
   - See `backend/tests/integration/test_directory_integration.py:242-344`
   - Valid: `"org/team/project"`, `"org/my_project-v1.0"`
   - Invalid: `"/org/project"` (leading slash), `"org/team/"` (trailing slash), `"org//team"` (consecutive slashes)

**Requirements:**

1. **Frontend UI Components (BatchUploadPopup.tsx)**
   - Add read-only TextField showing normalized full path preview below folder name field
     - Format: `{selected_parent_prefix}/{normalized_folder_name}`
     - Example: `cfia/mycology/avena-fatua`
   - Add "Root" option to parent folder Autocomplete dropdown
     - Root folder has `folder_prefix: "/"`
     - Display as "Root (/)" in dropdown
   - Add "Create Folder" button below folder name field
     - Calls new `createOrGetFolder` API endpoint
     - Returns `folder_id` (creates if doesn't exist, returns existing if exists)
     - Stores result in `createdFolderId` state variable
   - Disable "Select Files" button until `createdFolderId` is present
   - Update folder normalization logic to use `folder_prefix` from selected parent

2. **Frontend API Client (api.ts)**
   - New function: `createOrGetFolder()`
     - Parameters: `backendUrl`, `accessToken`, `normalizedPath` (e.g., "avena-fatua")
     - Calls: `POST /folders`
     - Returns: `{ folder_id: string }`
     - Idempotent: Returns existing folder_id if path already exists

3. **Frontend Types & Validation**
   - Add `CreateOrGetFolderRequest` interface in types.d.ts
   - Add `CreateOrGetFolderResponse` interface in types.d.ts
   - Add `normalizedPathSchema` in validation.ts
     - **Follows Backend Validation Rules** (see backend/app/service/directory.py:142-232)
     - Pattern: `^[a-zA-Z0-9/_.\-]+[a-zA-Z0-9]$`
     - Allowed characters: alphanumeric, slash `/`, underscore `_`, dash `-`, period `.`
     - Must end with alphanumeric character (not `_`, `-`, or `.`)
     - Cannot contain consecutive slashes `//`
     - Cannot start or end with slash (frontend provides relative path, backend adds org prefix)

4. **Backend API Endpoint (routes.py)**
   - New route: `POST /folders`
     - Request: `{ normalized_path: string }` (e.g., "avena-fatua")
     - Response: `{ folder_id: string }`
     - Behavior:
       1. Construct fullpath: `/{org_prefix}/{normalized_path}`
       2. Check if folder exists (query by org_user_role_id + name + folder_prefix)
       3. If exists: return existing folder_id
       4. If not exists: create folder and return new folder_id

5. **Backend Service Layer (directory.py)**
   - New method: `DirectoryService.get_or_create_folder()`
     - Parameters: `user_id`, `normalized_path`
     - **Reuses existing validation logic** from `DirectoryService.create_directory()` (line 320-383)
     - Steps:
       1. Get user's organization prefix and roles via `RbacService.get_user_org_roles()`
       2. Construct fullpath: `{org_prefix}/{normalized_path}` (e.g., "cfia/avena-fatua")
       3. Parse fullpath into `folder_name` and `folder_prefix` using existing `_validate_and_parse_fullpath()` (line 142-232)
          - This validates all path rules (alphanumeric, no consecutive slashes, etc.)
          - Extracts folder_name (e.g., "avena-fatua") and folder_prefix (e.g., "cfia/")
       4. Call `DirectoryDataService.find_folder_by_path()` to check if exists
       5. If exists: return existing folder_id
       6. If not exists: create via `DirectoryService.create()` and return new folder_id

6. **Backend Data Layer (datastore/directory.py)**
   - New method: `DirectoryDataService.find_folder_by_path()`
     - Parameters: `org_user_role_id`, `folder_name`, `folder_prefix`
     - Query: SELECT id FROM folder WHERE org_user_role_id = ? AND name = ? AND folder_prefix = ? AND active = true
     - Returns: folder_id (UUID) or None

7. **Backend Request Model (model/directory.py)**
   - New Pydantic model: `CreateOrGetFolderRequest`
     - Field: `normalized_path: str`
     - **Backend validates in service layer** (not in Pydantic model)
     - Validation handled by `DirectoryService._validate_and_parse_fullpath()`
     - Accepts alphanumeric, slash, underscore, dash, period (same as existing folders)

**Folder Path Construction Logic:**

Based on backend `DirectoryService.create_directory()` implementation:

```text
Example 1: Root parent (NEW - needs implementation)
- User selects: "Root (/)"
- User enters genus "Avena", species "fatua"
- Frontend normalizes: "avena-fatua" (genus-species pattern, lowercase)
- Frontend sends to backend: normalized_path="avena-fatua"
- Backend gets org_prefix from user: "cfia"
- Backend constructs fullpath: "/cfia/avena-fatua"
- Backend validates via _validate_and_parse_fullpath()
- Backend extracts: folder_name="avena-fatua", folder_prefix="/cfia/"
- Full path in database: folder_prefix="/cfia/", name="avena-fatua"

Example 2: Nested parent (EXISTING pattern - already works)
- User enters relative path: "mycology/samples/avena-fatua"
- Frontend sends to backend: normalized_path="mycology/samples/avena-fatua"
- Backend gets org_prefix from user: "cfia"
- Backend constructs fullpath: "/cfia/mycology/samples/avena-fatua"
- Backend validates via _validate_and_parse_fullpath()
- Backend extracts: folder_name="avena-fatua", folder_prefix="/cfia/mycology/samples/"
- Full path in database: folder_prefix="/cfia/mycology/samples/", name="avena-fatua"

Validation Examples (from backend tests):
✅ Valid: "org/team/project" → folder_name="project", folder_prefix="/cfia/org/team/"
✅ Valid: "org/my_project-v1.0" → folder_name="my_project-v1.0", folder_prefix="/cfia/org/"
❌ Invalid: "/org/team/project" (starts with /, causes /cfia//org - consecutive slashes)
❌ Invalid: "org/team/" (ends with /, must end with alphanumeric)
❌ Invalid: "org//team/project" (consecutive slashes)
❌ Invalid: "org/team$/project" (invalid character $)
```

**Authorization:**

- Folder creation: CFIA admin only (existing `DirectoryService.verify_create_access`)
- Folder lookup: User must belong to same organization (via `org_user_role_id`)
- Get-or-create: Same as create (CFIA admin only)

**Edge Cases:**

- **Duplicate paths:** Backend returns existing folder_id (idempotent get-or-create)
- **Invalid characters:** Frontend validation prevents submission
- **Missing parent:** Default to Root ("/")
- **Permissions:** Non-admin users receive 403 on create attempt
- **Path conflicts:** Existing path with same name but different prefix treated as separate folder

**Technical Notes:**

- Get-or-create pattern prevents duplicate folder creation (idempotent)
- Path normalization ensures consistent folder naming (genus-species pattern)
- Read-only path preview helps users understand folder hierarchy
- "Root" option simplifies top-level folder creation under organization prefix
- Backend constructs full path with organization prefix automatically
- **Frontend validation must match backend rules exactly:**
  - Pattern: `^[a-zA-Z0-9/_.\-]+[a-zA-Z0-9]$` (see backend/app/service/directory.py:193)
  - No leading slash (frontend sends relative path)
  - No trailing slash (must end with alphanumeric)
  - No consecutive slashes
  - Allowed: alphanumeric, `/`, `_`, `-`, `.`
- Reuses existing `DirectoryService.create_directory()` validation logic
- Backend tests provide validation examples (see backend/tests/integration/test_directory_integration.py:242-344)

**Testing Requirements:**

- [ ] Test folder creation with root parent
- [ ] Test folder creation with nested parent
- [ ] Test get-or-create idempotency (call twice with same path)
- [ ] Test path preview updates when parent/name changes
- [ ] Test validation for invalid folder names
- [ ] Test "Select Files" button disabled state
- [ ] Test non-admin user receives 403 error
- [ ] Test path normalization (uppercase → lowercase, spaces → hyphens)

**Deliverables (Completed):**

✅ **Backend Implementation:**

- `backend/app/api/routes.py:421-457` - New `POST /folders` endpoint
- `backend/app/service/directory.py:385-452` - `get_or_create_folder()` method with idempotent logic
- `backend/app/datastore/directory.py:246-269` - `find_folder_by_path()` data layer method
- `backend/app/model/directory.py:8-17` - `CreateOrGetFolderRequest` Pydantic model

✅ **Frontend Implementation:**

- `frontend/src/components/body/batch_upload_popup/BatchUploadPopup.tsx:851-938` - Folder creation UI
  - Parent folder selection (optional, defaults to root)
  - Folder name input field
  - Normalized path preview (read-only)
  - Create folder button with success state
  - Disabled "Select Files" until folder created
- `frontend/src/common/api.ts:825-872` - `createOrGetFolder()` API function
- `frontend/src/common/types.d.ts:147-153` - TypeScript interfaces
- `frontend/src/common/validation.ts:860-879` - Zod validation schemas with backend-matching rules

✅ **Key Features:**

- Get-or-create pattern (idempotent - returns existing folder_id if already exists)
- Real-time path preview showing normalized path
- Frontend validation matches backend rules exactly
- CFIA admin authorization (reuses existing `verify_create_access`)
- All linting and type checking passed
- Frontend build successful

**Technical Notes:**

- Session initialization now uses `createdFolderId` instead of `selectedFolderId`
- Folder creation is mandatory before file selection
- Path normalization: lowercase, alphanumeric + `/_.-`, must end with alphanumeric
- Parent folder optional (empty = root level)
- Error handling includes validation errors and API failures

---

### Phase 6: Error Handling (1h)

**Goal:** Handle all error scenarios gracefully

**Tasks:**

- [ ] Handle duplicate detection
  - [ ] Display info message (not error): "Image already uploaded"
  - [ ] Mark as complete (don't retry)
  - [ ] Show existing `picture_id` in logs
- [ ] Handle session expiration
  - [ ] Display clear error: "Session expired (24-hour limit)"
  - [ ] Prompt user to restart batch upload
  - [ ] Clear session state
- [ ] Handle seed validation errors
  - [ ] Display error: "Seed not found: {taxonomy}"
  - [ ] Allow user to skip file or cancel upload
  - [ ] Log error for debugging
- [ ] Handle workflow timeout
  - [ ] Display timeout message after 5 minutes
  - [ ] Allow retry or cancel
- [ ] Handle network errors
  - [ ] Retry logic (max 3 attempts)
  - [ ] Display network error message
- [ ] Handle file count limit (1000)
  - [ ] Validate before session init
  - [ ] Display error if exceeds limit

**Deliverables:**

- Comprehensive error handling
- User-friendly error messages
- Error recovery mechanisms

**Implementation:**

```typescript
// Error handling examples

// Duplicate detection (not critical)
if (!response.success && response.error?.includes("Duplicate")) {
  console.log(`Duplicate detected: ${file.name} (existing: ${response.picture_id})`);
  // Don't treat as error - mark as complete
  resolve(true);
  return;
}

// Session expired
if (!response.success && response.error?.includes("Session expired")) {
  alert("Session expired (24-hour limit). Please start a new batch upload.");
  clearSessionState();
  reject(new Error("Session expired"));
  return;
}

// Seed not found
try {
  const seedId = await getSeedIdByTaxonomy(...);
} catch (error) {
  alert(`Seed not found: ${family} ${genus} ${species} (${nameCode}). Please verify taxonomic data.`);
  reject(error);
  return;
}

// Workflow timeout
if (attempts >= maxAttempts) {
  alert(`Processing timeout for ${file.name}. The image may still be processing in the background.`);
  reject(new Error("Processing timeout"));
  return;
}

// File count limit
if (files.length > 1000) {
  alert("Maximum 1000 files allowed per batch upload. Please split into multiple batches.");
  return;
}
```

---

### Phase 7: Testing (3h)

**Goal:** Comprehensive testing of new functionality

**Tasks:**

- [ ] Unit tests
  - [ ] Test `getSeedIdByTaxonomy()` function
  - [ ] Test request payload transformation
  - [ ] Test response parsing
  - [ ] Test error handling logic
- [ ] Integration tests
  - [ ] Test with backend API (local dev server)
  - [ ] Test session initialization with folder selection
  - [ ] Test image upload with async polling
  - [ ] Test duplicate detection
  - [ ] Test session expiration
- [ ] End-to-end tests
  - [ ] Upload 5-10 images successfully
  - [ ] Verify all images appear in folder
  - [ ] Verify workflow polling completes
  - [ ] Test progress indicators
- [ ] Error scenario tests
  - [ ] Test with non-existent seed
  - [ ] Test with expired session (wait 24h or mock)
  - [ ] Test with duplicate images
  - [ ] Test timeout scenario
- [ ] Performance tests
  - [ ] Test with 50 images
  - [ ] Measure average upload time
  - [ ] Monitor memory usage

**Deliverables:**

- Test suite with 90%+ coverage
- Manual testing checklist completed
- Performance benchmarks documented

---

## Technical Implementation Details

### State Management Architecture

**Zustand Global Store (`useBatchUploadStore`):**

```typescript
interface BatchUploadState {
  currentSession: BatchSessionInfo | null;  // Session tracking
  uploads: Map<string, UploadWorkflowInfo>; // Upload workflows

  // Session management
  createSession: (sessionId: string, totalFiles: number) => void;
  updateSessionProgress: () => void;
  clearSession: () => void;

  // Upload workflow management
  addUpload: (workflowId: string, file: File, queuePosition?: number) => void;
  updateUploadStatus: (workflowId: string, status: WorkflowStatus, ...) => void;
  setUploadResult: (workflowId: string, resultData: unknown) => void;
  removeUpload: (workflowId: string) => void;

  // Utility queries
  getUploadsByStatus: (status: WorkflowStatus) => UploadWorkflowInfo[];
  hasActiveUploads: () => boolean;
}
```

**Component State (Local to BatchUploadPopup):**

```typescript
// Form fields
const [family, setFamily] = useState<string>("");
const [genus, setGenus] = useState<string>("");
const [species, setSpecies] = useState<string>("");
const [nameCode, setNameCode] = useState<string>("");
const [trayCode, setTrayCode] = useState<string>("");
const [sampleId, setSampleId] = useState<string>("");
const [selectedFolderId, setSelectedFolderId] = useState<string>("");
// ... device fields, magnification, etc.

// Upload state (managed by Zustand + Queue Manager)
const queueManagerRef = useRef<BatchUploadQueueManager>(
  new BatchUploadQueueManager()
);
const { currentSession, uploads, createSession, addUpload, ... } = useBatchUploadStore();
```

### Queue Manager (Service Layer)

**No polling hook needed** - polling logic is encapsulated in `BatchUploadQueueManager`:

```typescript
// BatchUploadQueueManager handles:
// 1. Sequential file processing
// 2. File-to-base64 conversion
// 3. Upload submission to backend
// 4. Workflow status polling (20s initial + 10s intervals)
// 5. State updates via Zustand store
// 6. Completion/error callbacks

// Component just enqueues files:
queueManagerRef.current.enqueue(file, metadata);
```

### UI Components

**Folder Selection (Autocomplete with folder details):**

```tsx
<Autocomplete
  id="input-folder"
  renderInput={(params) => (
    <TextField
      {...params}
      label="Folder *"
      placeholder="Select a folder"
      helperText={
        folders.length === 0
          ? "No folders available. Please create a folder first."
          : "Select the folder where images will be uploaded"
      }
    />
  )}
  options={folders}
  getOptionLabel={(option) =>
    `${option.folderName} (${option.pictureCount} images)`
  }
  value={folders.find((f) => f.folderId === selectedFolderId) || null}
  onChange={(_event, newValue) => {
    setSelectedFolderId(newValue?.folderId || "");
  }}
  disabled={uploading || folders.length === 0}
/>
```

**Upload Progress Display:**

```tsx
{
  uploading && currentSession && (
    <Stack spacing={1} sx={{ width: "100%", marginBottom: "20px" }}>
      <LinearProgress
        variant="determinate"
        value={uploadProgress}
        sx={{ width: "100%", height: "10px" }}
      />
      <Typography variant="caption" sx={{ textAlign: "center" }}>
        {currentSession.completedFiles} of {currentSession.totalFiles} completed
        {currentSession.failedFiles > 0 &&
          ` (${currentSession.failedFiles} failed)`}
      </Typography>
      <LinearProgress
        variant="indeterminate"
        sx={{ width: "100%", height: "10px" }}
      />
    </Stack>
  );
}
```

**Per-File Status List (from Zustand store):**

```tsx
{
  files && fileCount > 0 && (
    <List dense={true} subheader={<ListSubheader>Upload Status</ListSubheader>}>
      {Array.from({ length: fileCount }).map((_, index) => {
        const file = files[index];
        const uploadInfo = Array.from(uploads.values()).find(
          (u) => u.fileName === file.name,
        );
        const status = uploadInfo?.status || "pending";

        return (
          <ListItem key={index}>
            {/* Status icon: completed (green check), failed (red X), pending (grey) */}
            <ListItemText
              primary={file.name}
              secondary={
                uploadInfo?.error
                  ? `Error: ${uploadInfo.error}`
                  : status === "queued"
                    ? `Queued (${uploadInfo?.queuePosition ?? ""})`
                    : status === "processing"
                      ? "Processing..."
                      : status
              }
            />
          </ListItem>
        );
      })}
    </List>
  );
}
```

---

## Testing Strategy

### Unit Tests

**Completed Test Files:**

- ✅ `frontend/src/utils/seedLookup.test.ts` - 12 tests passing
- ✅ `frontend/src/common/api.test.ts` - Updated with batch upload tests (60 API tests passing)

**Test Files Needed:**

- [ ] `frontend/src/stores/useBatchUploadStore.test.ts` - Test Zustand store
- [ ] `frontend/src/services/BatchUploadQueueManager.test.ts` - Test queue manager
- [ ] `frontend/src/components/body/batch_upload_popup/BatchUploadPopup.test.tsx` - Integration tests

**Test Cases:**

- Seed lookup by taxonomy (success)
- Seed lookup by taxonomy (not found)
- Seed caching mechanism
- API request payload transformation
- Response parsing
- Error handling for each scenario

### Integration Tests

**Test with Backend:**

- Start backend server (`cd backend && uv run hypercorn -b :8080 app/main:app`)
- Start frontend dev server (`cd frontend && npm run dev`)
- Test full workflow:
  1. Select folder
  2. Initialize session
  3. Upload 5 images
  4. Verify workflow polling completes
  5. Check images in database

### Manual Testing Checklist

- [ ] Folder selection displays user's folders
- [ ] Session initialization succeeds with folder_id
- [ ] Image upload returns workflow_id
- [ ] Workflow polling updates progress indicators
- [ ] Duplicate images handled gracefully
- [ ] Session expiration displays clear error
- [ ] Seed not found displays clear error
- [ ] Workflow timeout after 5 minutes
- [ ] All images appear in selected folder after upload
- [ ] UI responsive during uploads
- [ ] Error messages user-friendly

### Performance Benchmarks

**Metrics to Track:**

- Average upload time per image (target: 30-40s with Defender scan)
- Memory usage during 50-image batch
- UI responsiveness during concurrent uploads
- API request rate (should not exceed rate limits)

---

## Timeline & Effort Estimation

| Phase         | Description                                | Effort       | Status           | Completion Date |
| ------------- | ------------------------------------------ | ------------ | ---------------- | --------------- |
| **Phase 1**   | Create Seed Lookup Utility ✨✨            | **1h**       | ✅ **COMPLETED** | 2025-10-31      |
| **Phase 2**   | Type Definitions Update                    | 1h           | ✅ **COMPLETED** | 2025-10-31      |
| **Phase 3**   | API Client Updates                         | 2h           | ✅ **COMPLETED** | 2025-10-31      |
| **Phase 4**   | Folder Store & Selection UI                | 2h           | ✅ **COMPLETED** | 2025-10-31      |
| **Phase 5**   | Queue-Based Async Workflow Implementation  | 3h           | ✅ **COMPLETED** | 2025-10-31      |
| **Phase 5.5** | Folder Creation with Get-or-Create Pattern | 3h           | ✅ **COMPLETED** | 2025-10-31      |
| **Phase 6**   | Error Handling                             | 1h           | ⏳ **PENDING**   | -               |
| **Phase 7**   | Testing                                    | 3h           | ⏳ **PENDING**   | -               |
| **Total**     |                                            | **16 hours** | **12h Complete** | **75% Done**    |

**Progress Summary:**

- ✅ **Phases 1-5.5 Complete (12h)** - Core implementation + folder creation ready
- ⏳ **Phases 6-7 Remaining (4h)** - Error handling refinements, testing
- 🎯 **Current Status:** Frontend ready for integration testing with backend
- 📝 **Next Step:** Error handling refinements (Phase 6)

### Implementation Actual vs Planned

| Day       | Planned        | Actual                         |
| --------- | -------------- | ------------------------------ |
| **Day 1** | Phase 1-5 (9h) | ✅ Phase 1-5.5 completed (12h) |
| **Day 2** | Phase 6-7 (4h) | ⏳ Remaining work              |

**Note:** Phase 5.5 was completed on Day 1 instead of Day 2, accelerating the timeline.

---

## Risk Mitigation

### Risk 1: Seed Lookup Failure

**Risk:** Seed not found for uploaded images

**Mitigation:**

- Pre-validate seed data before batch upload starts
- Display all unique seeds in preview
- Allow user to verify seeds exist before proceeding
- Provide clear error messages with taxonomy info

### Risk 2: Workflow Polling Timeout

**Risk:** Defender scan takes longer than 5 minutes

**Mitigation:**

- Increase timeout to 10 minutes if needed
- Display informative message: "Processing is taking longer than expected..."
- Allow user to check status later via folder view
- Log workflow_id for manual tracking

### Risk 3: Session Expiration During Upload

**Risk:** 24-hour session expires mid-upload

**Mitigation:**

- Display time remaining in session
- Warn user when < 1 hour remaining
- Allow user to create new session and resume
- Track uploaded vs remaining files

### Risk 4: Rate Limiting

**Risk:** Exceeding 60 req/min rate limit for `/upload-picture`

**Mitigation:**

- Implement upload queue with rate limiting
- Max 1 request per second (60/min)
- Display upload rate in UI
- Batch uploads stagger requests automatically

### Risk 5: Browser Memory Issues

**Risk:** Large batches (500+ images) cause memory issues

**Mitigation:**

- Process images in chunks (50 at a time)
- Release memory after each upload
- Display memory usage warning if batch too large
- Recommend splitting into multiple sessions

---

## Success Criteria

### Functional Requirements

- [ ] Frontend successfully uploads batches using backend API
- [ ] Each image tracked via workflow polling
- [ ] Duplicate detection displays gracefully
- [ ] Session expiration handled with clear error messages
- [ ] Folder selection works correctly
- [ ] Progress indicators accurate and responsive

### Non-Functional Requirements

- [ ] Average upload time: 30-40s per image (Defender scan)
- [ ] UI remains responsive during uploads
- [ ] Memory usage acceptable for 100-image batches
- [ ] 90%+ test coverage for new functionality
- [ ] No console errors during normal operation
- [ ] Error messages user-friendly and actionable

### User Experience

- [ ] Users can upload batches without confusion
- [ ] Progress clearly communicated
- [ ] Errors explained in plain language
- [ ] Recovery paths obvious when errors occur
- [ ] No data loss during failures

---

## Appendix

### Related Documents

- `backend/docs/BATCH_UPLOAD_IMPLEMENTATION_PLAN.md` - Backend specification
- `CLAUDE.md` - Project overview and architecture
- `frontend/TESTING.md` - Testing guidelines

### API Reference

See backend documentation for full API specification:

- POST `/new-batch-import`
- POST `/upload-picture`
- GET `/workflow/{workflow_id}/status`

### Glossary

- **Workflow ID:** UUID returned by backend for tracking async processing
- **Session ID:** UUID for batch upload session (24-hour TTL)
- **Seed ID:** UUID linking to taxonomic seed record
- **Defender Scan:** Azure Defender malware scan (~30s)
- **Sanitization:** Image processing step after Defender scan
- **Duplicate Detection:** SHA256 hash collision check
