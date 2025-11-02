# Batch Upload Cancel Functionality Implementation Plan

## Problem Statement

The cancel button in the batch upload popup currently only closes the modal UI - it does NOT actually cancel the upload process. This leaves uploads running in the background even after the user clicks "Cancel".

### Current Cancel Button Behavior

**What it DOES ✅:**

- Closes the modal popup
- Resets form fields
- Clears local UI state

**What it DOESN'T DO ❌:**

- Stop the queue - BatchUploadQueueManager continues processing files in the background
- Cancel server workflows - DBOS workflows keep running
- Clean up store state - Zustand persists session and upload data
- Abort in-flight requests - Active uploads continue to completion

### Key Finding

The code comment explicitly states this is intentional:

```typescript
// Note: Queue manager continues running even after modal closes
// This allows uploads to complete in the background
```

However, the backend **already has cancellation infrastructure** (`cancel_processing()` function, `DBOS.cancel_workflow()`) but **no API endpoints are exposed** to use it.

---

## Solution Overview

Implement complete cancellation flow covering:

1. Frontend queue management
2. Server-side workflow cancellation
3. State cleanup (Zustand store, database)
4. User confirmation for in-progress uploads

---

## Backend Changes

### 1. Add Workflow Cancellation Endpoint

**File:** `backend/app/api/routes.py`

**New Endpoint:** `POST /workflow/{workflow_id}/cancel`

```python
@router.post("/workflow/{workflow_id}/cancel")
async def cancel_workflow_endpoint(
    workflow_id: str,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Cancel an in-progress workflow.

    Returns:
        - status: "cancelled" or "already_completed"
        - workflow_id: The workflow ID
        - message: Status message
    """
    try:
        result = await cancel_processing(
            session=session,
            image_id=get_image_id_from_workflow(workflow_id),
            user_id=user_id,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
```

**Implementation notes:**

- Uses existing `cancel_processing()` from `workflow_management.py`
- Validates user owns the workflow
- Gracefully handles already-completed workflows
- Returns clear status message

---

### 2. Add Batch Session Cancellation Endpoint

**File:** `backend/app/api/routes.py`

**New Endpoint:** `POST /batch-upload/session/{session_id}/cancel`

```python
@router.post("/batch-upload/session/{session_id}/cancel")
async def cancel_batch_session(
    session_id: UUID,
    user_id: UUID = Depends(get_current_user_id),
    session: AsyncSession = Depends(get_db_session),
) -> Dict[str, Any]:
    """
    Cancel all workflows in a batch upload session.

    Returns:
        - session_id: The session ID
        - cancelled_count: Number of workflows cancelled
        - workflow_ids: List of cancelled workflow IDs
        - failed_count: Number that couldn't be cancelled
    """
    # Get all uploads for this session
    uploads = await get_batch_session_uploads(session_id, user_id)

    cancelled = []
    failed = []

    for upload in uploads:
        if upload.workflow_id and upload.status in ["processing", "pending"]:
            try:
                await cancel_processing(
                    session=session,
                    image_id=upload.image_id,
                    user_id=user_id,
                )
                cancelled.append(str(upload.workflow_id))
            except Exception as e:
                failed.append(str(upload.workflow_id))

    # Mark session as inactive
    await mark_session_inactive(session_id)

    return {
        "session_id": str(session_id),
        "cancelled_count": len(cancelled),
        "workflow_ids": cancelled,
        "failed_count": len(failed),
    }
```

**Implementation notes:**

- Cancels all active workflows in the session
- Marks session as inactive in database
- Returns detailed cancellation results
- Handles partial failures gracefully

---

### 3. Service Layer Enhancements (if needed)

**File:** `backend/app/service/inference/workflow_management.py`

**Verify existing functions:**

- `cancel_processing()` - Already exists (line 545-600)
- `DBOS.cancel_workflow()` - Already available

**Potential additions:**

- Batch cancellation helper function
- Better error handling for edge cases
- Logging for cancellation events

---

## Frontend Changes

### 1. Update BatchUploadQueueManager

**File:** `frontend/src/services/BatchUploadQueueManager.ts`

**Add `cancelAll()` method:**

```typescript
private abortController: AbortController | null = null;

/**
 * Cancel all queued and in-progress uploads
 */
async cancelAll(): Promise<void> {
  // Stop processing new items from queue
  this.stopPolling();
  this.isProcessing = false;

  // Abort any in-flight HTTP requests
  if (this.abortController) {
    this.abortController.abort();
  }

  // Call cancel API for current workflow if exists
  if (this.currentWorkflow) {
    try {
      await cancelWorkflow(this.currentWorkflow.workflowId);
    } catch (error) {
      console.error("Failed to cancel workflow:", error);
    }
  }

  // Clear queue and reset state
  this.queue = [];
  this.currentWorkflow = null;

  console.log("All uploads cancelled");
}
```

**Update fetch calls to use AbortController:**

- Modify `processNextInQueue()` to create and use AbortController
- Pass abort signal to all fetch requests
- Handle AbortError gracefully

---

### 2. Update BatchUploadPopupContainer

**File:** `frontend/src/components/body/batch_upload_popup/BatchUploadPopupContainer.tsx`

**Add state for confirmation dialog:**

```typescript
const [showCancelConfirmation, setShowCancelConfirmation] = useState(false);
```

**Modify `handleClose()` function (lines 553-560):**

```typescript
const handleClose = (): void => {
  // Check if uploads are in progress
  const hasActiveUploads = currentSession &&
    currentSession.status === "active" &&
    (currentSession.completedFiles + currentSession.failedFiles) < currentSession.totalFiles;

  if (hasActiveUploads && uploading) {
    // Show confirmation dialog
    setShowCancelConfirmation(true);
  } else {
    // No active uploads, close immediately
    performClose();
  }
};
```

**Add `handleCancelConfirmed()` function:**

```typescript
const handleCancelConfirmed = async (): Promise<void> => {
  setShowCancelConfirmation(false);

  try {
    // Cancel queue manager
    await queueManagerRef.current.cancelAll();

    // Cancel batch session on server
    if (currentSession?.sessionId) {
      const accessToken = await acquireAccessToken(msalInstance, [apiScopeClaim]);
      await cancelBatchSession({
        backendUrl,
        accessToken,
        sessionId: currentSession.sessionId,
      });
    }

    // Clean up Zustand store
    clearSession();

    // Show notification
    addWarning("Batch upload cancelled", 5000);
  } catch (error) {
    console.error("Error during cancellation:", error);
    addError("Failed to cancel some uploads", "batch-upload");
  } finally {
    performClose();
  }
};

const performClose = (): void => {
  resetUpload();
  resetForm();
  closeBatchUploadPopup();
};
```

---

### 3. Update API Client

**File:** `frontend/src/common/api.ts`

**Add cancellation functions:**

```typescript
/**
 * Cancel a workflow
 */
export const cancelWorkflow = async ({
  backendUrl,
  accessToken,
  workflowId,
}: {
  backendUrl: string;
  accessToken: string;
  workflowId: string;
}): Promise<{ status: string; message: string }> => {
  const response = await fetch(
    `${backendUrl}/workflow/${workflowId}/cancel`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
      },
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to cancel workflow: ${response.statusText}`);
  }

  return response.json();
};

/**
 * Cancel a batch upload session
 */
export const cancelBatchSession = async ({
  backendUrl,
  accessToken,
  sessionId,
}: {
  backendUrl: string;
  accessToken: string;
  sessionId: string;
}): Promise<{
  session_id: string;
  cancelled_count: number;
  workflow_ids: string[];
  failed_count: number;
}> => {
  const response = await fetch(
    `${backendUrl}/batch-upload/session/${sessionId}/cancel`,
    {
      method: "POST",
      headers: {
        Authorization: `Bearer ${accessToken}`,
        "Content-Type": "application/json",
      },
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to cancel batch session: ${response.statusText}`);
  }

  return response.json();
};
```

---

### 4. Add Confirmation Dialog

**File:** `frontend/src/components/body/batch_upload_popup/BatchUploadPopupView.tsx`

**Add confirmation dialog component:**

```typescript
{showCancelConfirmation && (
  <Dialog open={showCancelConfirmation} onClose={() => setShowCancelConfirmation(false)}>
    <DialogTitle>Cancel Upload?</DialogTitle>
    <DialogContent>
      <DialogContentText>
        {currentSession && (
          <>
            {currentSession.totalFiles - currentSession.completedFiles - currentSession.failedFiles}
            {" files are currently uploading. Are you sure you want to cancel all uploads?"}
          </>
        )}
      </DialogContentText>
    </DialogContent>
    <DialogActions>
      <Button onClick={() => setShowCancelConfirmation(false)}>
        Continue Uploading
      </Button>
      <Button onClick={onCancelConfirmed} color="error" autoFocus>
        Cancel All
      </Button>
    </DialogActions>
  </Dialog>
)}
```

**Pass new props:**

- `showCancelConfirmation`
- `onCancelConfirmed`
- `onCancelDialogClose`

---

## UI/UX Enhancements

### Button Behavior Matrix

| Scenario | User Action | Behavior |
|----------|-------------|----------|
| No uploads started | Click Cancel | Close immediately |
| Uploads in progress | Click Cancel | Show confirmation dialog |
| User confirms cancel | Click "Cancel All" | Cancel uploads, clean up, close |
| User declines cancel | Click "Continue" | Dismiss dialog, keep uploading |
| Uploads complete | Click Close | Close immediately |

### User Notifications

**On cancellation start:**

- Info toast: "Cancelling uploads..."

**On cancellation complete:**

- Warning toast: "Batch upload cancelled" (5 seconds)

**On cancellation error:**

- Error toast: "Failed to cancel some uploads" (logged to error system)

---

## Testing Plan

### Backend Tests

**File:** `backend/tests/test_workflow_cancellation.py` (new)

```python
@pytest.mark.asyncio
async def test_cancel_workflow_endpoint():
    """Test cancelling a single workflow"""
    # Start workflow
    # Call cancel endpoint
    # Verify workflow cancelled in DBOS
    # Verify status updated in database

@pytest.mark.asyncio
async def test_cancel_batch_session():
    """Test cancelling entire batch session"""
    # Create session with 5 uploads
    # Start processing
    # Call cancel session endpoint
    # Verify all workflows cancelled
    # Verify session marked inactive

@pytest.mark.asyncio
async def test_cancel_already_completed():
    """Test cancelling already-completed workflow"""
    # Complete workflow
    # Call cancel endpoint
    # Verify graceful handling
    # Verify returns "already_completed" status
```

### Frontend Tests

**File:** `frontend/src/components/body/batch_upload_popup/BatchUploadPopupContainer.test.tsx`

```typescript
describe("Cancel functionality", () => {
  it("closes immediately when no uploads active", () => {
    // Render with no uploads
    // Click cancel
    // Verify modal closed without confirmation
  });

  it("shows confirmation when uploads active", () => {
    // Start uploads
    // Click cancel
    // Verify confirmation dialog shown
  });

  it("cancels uploads on confirmation", async () => {
    // Start uploads
    // Click cancel
    // Confirm cancellation
    // Verify queue.cancelAll() called
    // Verify API called
    // Verify store cleared
  });

  it("continues uploads on decline", () => {
    // Start uploads
    // Click cancel
    // Decline cancellation
    // Verify uploads continue
  });
});
```

### Integration Tests

**Manual test scenarios:**

1. **Mid-upload cancellation:**
   - Start batch upload with 20 files
   - Wait for 5 files to complete
   - Click cancel → Confirm
   - Verify: Queue stops, workflows cancelled on server, store cleared

2. **Network error handling:**
   - Start batch upload
   - Disconnect network
   - Click cancel → Confirm
   - Verify: Graceful error handling, local cleanup still occurs

3. **Already-completed session:**
   - Complete batch upload
   - Click close
   - Verify: Closes immediately without confirmation

---

## Edge Cases to Handle

1. **Workflow already completed:** Backend should return status without error
2. **Network failure during cancel:** Local cleanup should still occur
3. **User navigates away:** Existing unmount cleanup should handle
4. **Rapid cancel clicks:** Debounce or disable button during cancellation
5. **Partial cancellation failure:** Show warning, clean up what succeeded

---

## Database Schema Changes

**No schema changes required** - existing tables support cancellation:

- `ImageProcessingState.status` already has `CANCELLED` enum value
- `BatchUploadSession.active` can be set to `false`
- Workflow state tracked by DBOS

---

## Rollout Plan

### Phase 1: Backend (Safe to deploy independently)

- [ ] Add workflow cancellation endpoint
- [ ] Add batch session cancellation endpoint
- [ ] Test thoroughly
- [ ] Deploy to staging/production

### Phase 2: Frontend (Depends on Phase 1)

- [ ] Update API client with cancel functions
- [ ] Update BatchUploadQueueManager with cancelAll()
- [ ] Update BatchUploadPopupContainer with confirmation logic
- [ ] Add confirmation dialog UI
- [ ] Test thoroughly
- [ ] Deploy to staging/production

### Phase 3: Polish

- [ ] Add analytics/logging for cancellation events
- [ ] Add unit tests
- [ ] Update documentation

---

## Success Criteria

- [ ] Cancel button stops queue processing
- [ ] Server-side workflows terminated via DBOS
- [ ] Zustand store cleaned up properly
- [ ] User sees confirmation for in-progress uploads
- [ ] No uploads continue after cancellation
- [ ] Graceful error handling for edge cases
- [ ] Clear user feedback via notifications

---

## Related Files

**Backend:**

- `backend/app/api/routes.py` - Add cancel endpoints
- `backend/app/service/inference/workflow_management.py` - Use existing cancel_processing()
- `backend/app/datastore/batch_upload_session.py` - Use mark_inactive()

**Frontend:**

- `frontend/src/components/body/batch_upload_popup/BatchUploadPopupContainer.tsx` - Add cancel logic
- `frontend/src/components/body/batch_upload_popup/BatchUploadPopupView.tsx` - Add confirmation dialog
- `frontend/src/services/BatchUploadQueueManager.ts` - Add cancelAll() method
- `frontend/src/common/api.ts` - Add cancel API functions
- `frontend/src/stores/useBatchUploadStore.ts` - Use existing clearSession()

---

## Notes

- Backend already has `cancel_processing()` infrastructure - just needs API exposure
- DBOS provides `cancel_workflow()` capability out of the box
- Zustand store already has `clearSession()` method - just needs to be called
- Main work is connecting existing pieces together with proper UX
