# SDK Integration Plan: Adopt Auto-Generated OpenAPI Client

## Overview

This document outlines the plan to integrate the auto-generated SDK from `/src/client/` into the Nachet frontend application. The generated SDK provides type-safe API calls with automatic Zod validation for all backend endpoints.

## Architecture Principle

```text
/src/client/           ← Generated (DO NOT EDIT - gets overwritten)
  ├── client.gen.ts    ← Base axios client
  ├── sdk.gen.ts       ← 50+ API wrapper functions
  ├── types.gen.ts     ← TypeScript type definitions
  └── zod.gen.ts       ← Zod validation schemas

/src/common/           ← Custom code (safe from regeneration)
  ├── apiClient.ts     ← NEW: Configure the generated client
  ├── api.ts           ← Legacy functions (gradually remove)
  ├── validation.ts    ← Custom schemas (keep if needed)
  └── types.d.ts       ← Manual types (gradually remove)
```

**Key Rule**: Never edit files in `/src/client/` - they will be overwritten when regenerating the SDK.

---

## Implementation Checklist

### Phase 1: Setup & Configuration

- [ ] **Step 1.1**: Create SDK Configuration Module
  - File: `frontend/src/common/apiClient.ts` (NEW)
  - Import `client` from `'../client/client.gen'`
  - Import `setupAxiosInterceptor` from `'./apiInterceptor'`
  - Import `errorLogger` from `'../logging'`
  - Create `configureApiClient()` function that:
    - Sets baseURL on the imported client
    - Applies MSAL interceptor to `client.instance`
    - Adds correlation ID request interceptor
    - Adds response logging interceptor
  - Export the configuration function

- [ ] **Step 1.2**: Initialize Client in Application Startup
  - File: `frontend/src/main.tsx`
  - Import `configureApiClient` from `'./common/apiClient'`
  - Call after MSAL initialization
  - Pass backend URL, MSAL instance, and scopes
  - Keep legacy `initializeApi()` for backward compatibility during migration

- [ ] **Step 1.3**: Create Convenience Re-exports (Optional)
  - File: `frontend/src/common/apiClient.ts`
  - Re-export SDK functions with shorter, friendly names:

    ```typescript
    export {
      uploadPictureInBatchAuthRequiredUploadPicturePost as uploadBatchImage,
      initializeBatchUploadAuthRequiredNewBatchImportPost as initBatchUpload,
      getWorkflowStatusAuthRequiredWorkflowWorkflowIdStatusGet as getWorkflowStatus,
      // ... etc
    } from '../client';
    ```

---

### Phase 2: Batch Upload Migration (Proof of Concept)

- [ ] **Step 2.1**: Migrate BatchUploadPopupContainer
  - File: `frontend/src/components/body/batch_upload_popup/BatchUploadPopupContainer.tsx`
  - Replace imports from `'@common/api'` with `'@common/apiClient'`
  - Update API calls to use SDK pattern:
    - `const { data } = await uploadBatchImage({ body: {...} })`
  - Remove manual validation if SDK handles it
  - Update error handling for SDK errors

- [ ] **Step 2.2**: Migrate BatchUploadQueueManager
  - File: `frontend/src/services/BatchUploadQueueManager.ts`
  - Import SDK functions from `'../common/apiClient'`
  - Replace `batchUploadImage` calls with SDK equivalent
  - Update error handling

- [ ] **Step 2.3**: Update Type Imports (Optional)
  - Import generated types from `'../client/types.gen'` as needed
  - Keep using manual types for now (can migrate later)
  - No rush to change everything at once

---

### Phase 3: Testing & Validation

- [ ] **Step 3.1**: Run Test Suite
  - Run: `npm run test`
  - Run: `npm run format`
  - Verify all tests pass

- [ ] **Step 3.2**: Manual Testing
  - Test batch upload flow end-to-end
  - Verify MSAL authentication works
  - Verify correlation IDs appear in logs
  - Verify error handling works correctly
  - Test file validation and upload progress

- [ ] **Step 3.3**: Review Error Scenarios
  - Test invalid image formats
  - Test network errors
  - Test authentication failures
  - Test validation errors

---

### Phase 4: Documentation

- [ ] **Step 4.1**: Update CLAUDE.md
  - Document SDK regeneration command: `npm run generate:api`
  - Note: Never edit files in `src/client/` - they get overwritten
  - Document that custom config goes in `src/common/apiClient.ts`
  - Add SDK usage examples

- [ ] **Step 4.2**: Create Migration Guide
  - Add examples for migrating other endpoints
  - Document SDK function naming patterns
  - Create troubleshooting guide

- [ ] **Step 4.3**: Update Team Documentation
  - Add to developer onboarding docs
  - Update API integration guidelines
  - Document testing patterns for SDK calls

---

## File Organization

### Generated Files (DO NOT EDIT)

- `/src/client/*.gen.ts` - Auto-generated, will be overwritten on regeneration

### Custom Files (Safe to Edit)

- `/src/common/apiClient.ts` - SDK configuration and re-exports
- `/src/common/apiInterceptor.ts` - Existing MSAL interceptor
- `/src/common/api.ts` - Legacy functions (remove gradually)
- `/src/common/validation.ts` - Custom Zod schemas
- `/src/common/types.d.ts` - Manual types (remove gradually)

---

## Benefits of This Approach

✅ **Separation of concerns**: Generated vs custom code clearly separated
✅ **Safe regeneration**: Run `npm run generate:api` anytime without losing work
✅ **Friendly names**: Re-export SDK functions with better names
✅ **Backward compatible**: Can keep legacy API alongside SDK during migration
✅ **Gradual migration**: No big bang rewrite required
✅ **Team clarity**: Clear convention - never edit `client/`, customize in `common/`
✅ **Type safety**: Full TypeScript + Zod validation
✅ **Auto-sync**: Types stay in sync with backend changes

---

## Example Usage After Migration

```typescript
// In any component:
import { uploadBatchImage, getWorkflowStatus } from '@common/apiClient';

// Clean API - no backendUrl, no accessToken needed
const { data } = await uploadBatchImage({
  body: {
    sessionId,
    seedId,
    trayCode,
    sampleId,
    imageDescription,
    deviceBrandId,
    deviceModelId,
    deviceLensId,
    magnification,
    image
  }
});

const { data: status } = await getWorkflowStatus({
  path: { workflow_id: workflowId }
});
```

---

## Timeline Estimate

| Phase | Task | Estimated Time |
|-------|------|----------------|
| **Phase 1** | SDK Configuration Module | 45 mins |
| | Initialize in main.tsx | 15 mins |
| | Convenience re-exports | 30 mins |
| **Phase 2** | Migrate BatchUploadPopupContainer | 1 hour |
| | Migrate BatchUploadQueueManager | 30 mins |
| | Update type imports | 15 mins |
| **Phase 3** | Run test suite | 30 mins |
| | Manual testing | 30 mins |
| | Error scenario testing | 30 mins |
| **Phase 4** | Update CLAUDE.md | 15 mins |
| | Create migration guide | 15 mins |
| | Update team docs | 15 mins |
| **Total** | | **~5 hours** |

---

## Future Migration Targets

After batch upload is complete, migrate these endpoints in order:

- [ ] Workflow status endpoints (`getWorkflowStatus`, `getWorkflowResults`)
- [ ] Inference endpoints (`submitImageForProcessing`)
- [ ] Folder/directory endpoints (`createOrGetFolder`, `readAzureStorageDir`)
- [ ] Device endpoints (`getAllDevices`)
- [ ] Seed endpoints (`getSeedData`)
- [ ] User/auth endpoints (`checkUserRegistration`)

---

## Regenerating the SDK

When the backend OpenAPI spec changes:

```bash
cd frontend
npm run generate:api
```

This will regenerate all files in `/src/client/` while preserving your custom configuration in `/src/common/apiClient.ts`.

---

## Notes

- **Generated SDK uses camelCase**: Matches our current manual types exactly
- **Zod validation built-in**: Request/response validation automatic
- **Axios-based**: Works with existing MSAL interceptor
- **50+ endpoints ready**: Just configure once, use everywhere

---

## Progress Tracking

**Started**: [Date]
**Completed Phase 1**: [Date]
**Completed Phase 2**: [Date]
**Completed Phase 3**: [Date]
**Completed Phase 4**: [Date]
**Fully Integrated**: [Date]
