# Image Cache Individual Item Cancellation - Implementation Plan

## Executive Summary

Add cancel functionality to the image cache component that allows users to cancel **queued** inference items (items waiting in the frontend queue that have NOT yet been submitted to the backend). Items that have already been submitted to `/inf` endpoint will NOT be cancellable as they are already processing in the backend DBOS workflows.

---

## Problem Statement

Currently, users can only delete images from the cache after inference completes. There is no way to cancel an inference request once the user clicks "CLASSIFY" and the item enters the queue. This can be frustrating when:

- User accidentally clicks CLASSIFY on the wrong image
- User wants to reorder the queue
- User realizes they need to adjust settings before processing
- Queue is full (10 items + 1 active) and user wants to free up slots

---

## Current System Architecture

### Two-Tier Queue System

#### 1. Frontend Queue (Cancellable)

- Managed by `WorkflowQueueManager.ts`
- Items with `status === "queued"`
- Has temporary IDs: `"temp-{timestamp}-{random}"`
- Stored in memory array: `WorkflowQueueManager.queue[]`
- Max 10 items queued at once

#### 2. Backend DBOS Queue (Not Cancellable - Out of Scope)

- Items with `status === "pending"` or `status === "processing"`
- Real workflow IDs from backend (UUIDs)
- DBOS workflows running: upload → scan → inference
- Would require backend API endpoint to cancel (not implemented)

### Critical Decision Point: POST /inf Submission

```text
User clicks "CLASSIFY"
  ↓
[QUEUED] ← CANCELLABLE ✅
  │ • In frontend memory only
  │ • temp ID: "temp-1234567890-0.5678"
  │ • Queue position: 1-10
  │ • Can be removed without backend impact
  ↓
POST /inf submitted ← POINT OF NO RETURN ⚠️
  ↓
[PENDING/PROCESSING] ← NOT CANCELLABLE ❌
  │ • DBOS workflows created
  │ • Blob upload started
  │ • Defender scanning initiated
  │ • ML inference queued/running
  │ • Requires backend support to cancel
  ↓
[COMPLETED/FAILED] ← TERMINAL STATES
```

### Current Image Cache UI

**File:** `frontend/src/components/body/image_cache/ImageCache.tsx`

Each cached image displays:

- 📷 **Image icon** (blue)
- 🔤 **Image label** (UUID or "Capture #")
- 🔄 **Processing spinner** (if status="processing" or "pending")
- 🏷️ **Queue position chip** (if status="queued", shows "#1", "#2", etc.)
- ✅ **Checkmark** (if results available)
- ❌ **Close icon** (delete from cache - right side)

**Current Close Icon Behavior (Line 210-226):**

- Removes image from cache array (`removeImage()`)
- Does NOT clean up associated workflow (bug)
- Available for ALL images regardless of status

---

## Solution Design

### Scope: Cancel Queued Items Only (Phase 1)

**IN SCOPE:**
✅ Cancel items with `status === "queued"` (frontend queue)
✅ Remove from `WorkflowQueueManager.queue[]`
✅ Remove workflow from `useWorkflowStore`
✅ Update queue positions for remaining items
✅ Visual feedback with cancel icon
✅ Tooltip explanation
✅ No backend changes needed

**OUT OF SCOPE (Future Phase 2):**
❌ Cancel items with `status === "pending"` or `"processing"` (would require backend API)
❌ Batch cancellation (covered in separate plan)
❌ Cancel via keyboard shortcuts

### UI/UX Design

**Action Icon Behavior by Status:**

| Status | Icon | Color | Action | Tooltip |
|--------|------|-------|--------|---------|
| `queued` | `CancelIcon` | Warning (orange) | Cancel queued inference | "Cancel queued inference" |
| `pending` | `CloseIcon` (disabled) | Gray | None (disabled) | "Cannot cancel - processing started" |
| `processing` | `CloseIcon` (disabled) | Gray | None (disabled) | "Cannot cancel - processing started" |
| `completed` | `CloseIcon` | Primary (blue) | Remove from cache | "Remove from cache" |
| `failed` | `CloseIcon` | Primary (blue) | Remove from cache | "Remove from cache" |
| No workflow | `CloseIcon` | Primary (blue) | Remove from cache | "Remove from cache" |

**Visual Example:**

```text
┌─────────────────────────────────────────┐
│ CAPTURES                    [DELETE ALL] │
├─────────────────────────────────────────┤
│ 📷 Image-001        #1        [⊗ Cancel]│ ← Queued (orange cancel icon)
│ 📷 Image-002        #2        [⊗ Cancel]│ ← Queued (orange cancel icon)
│ 📷 Image-003        🔄        [✕ Gray]  │ ← Processing (disabled gray X)
│ 📷 Image-004        ✅        [✕ Close] │ ← Completed (blue close icon)
│ 📷 Image-005                  [✕ Close] │ ← No workflow (blue close icon)
└─────────────────────────────────────────┘
```

### User Experience Flow

#### Scenario 1: Cancel Queued Item

1. User clicks CLASSIFY → Image enters queue with position #3
2. User sees orange cancel icon with "#3" chip
3. User clicks cancel icon
4. Confirmation? **No** (instant cancellation for queued items)
5. Item removed from queue
6. Remaining items #4, #5 → renumbered to #3, #4
7. Toast notification: "Queued inference cancelled" (3 seconds)

#### Scenario 2: Try to Cancel Processing Item

1. Item is status="processing" (spinner showing)
2. Close icon is grayed out and disabled
3. User hovers → Tooltip: "Cannot cancel - processing started"
4. Click does nothing
5. User can still remove from cache after completion

#### Scenario 3: Delete Completed Image

1. Item is status="completed" (checkmark showing)
2. User clicks blue close icon
3. Image removed from cache
4. Associated workflow cleaned up (fixed bug)

---

## Implementation Details

### 1. Frontend Changes

#### File 1: `WorkflowQueueManager.ts`

**Location:** `frontend/src/services/WorkflowQueueManager.ts`

**Add Method:** `cancelQueued(workflowId: string): boolean`

```typescript
/**
 * Cancel a queued item (not yet submitted to backend)
 * @param workflowId - The temporary workflow ID (e.g., "temp-1234567890-0.5678")
 * @returns true if cancelled, false if not found or already submitted
 */
cancelQueued(workflowId: string): boolean {
  // Safety check: Only cancel items with temp IDs
  if (!workflowId.startsWith("temp-")) {
    console.warn(`Cannot cancel non-queued workflow: ${workflowId}`);
    return false;
  }

  // Find item in queue
  const index = this.queue.findIndex((item) => item.tempId === workflowId);

  if (index === -1) {
    // Not in queue - either already submitted or never existed
    console.warn(`Workflow ${workflowId} not found in queue`);
    return false;
  }

  // Remove from queue
  const removed = this.queue.splice(index, 1)[0];
  console.log(`Cancelled queued item: ${removed.imageId} at position ${removed.queuePosition}`);

  // Update queue positions for remaining items
  this.updateQueuePositions();

  // Update workflow store for all remaining queued items
  this.queue.forEach((item, idx) => {
    this.config.workflowStore.updateWorkflowStatus(
      item.tempId,
      "queued",
      null,
      idx + 1 // 1-based queue position
    );
  });

  // Remove workflow from store
  this.config.workflowStore.removeWorkflow(workflowId);

  return true;
}

/**
 * Update queue positions after item removal
 * @private
 */
private updateQueuePositions(): void {
  this.queue.forEach((item, index) => {
    item.queuePosition = index + 1; // 1-based
  });
}
```

**Lines to modify:** Add after `clear()` method (currently line 461)

---

#### File 2: `ImageCache.tsx`

**Location:** `frontend/src/components/body/image_cache/ImageCache.tsx`

**Changes Required:**

##### 2a. Add Import (Line 15-18)

```typescript
import CloseIcon from "@mui/icons-material/Close";
import DeleteIcon from "@mui/icons-material/Delete";
import ImageIcon from "@mui/icons-material/Image";
import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import CancelIcon from "@mui/icons-material/Cancel"; // NEW
```

##### 2b. Add Props Interface (Line 30-36)

```typescript
interface ImageCacheProps {
  // ... existing props
  onCancelQueued: (workflowId: string) => void; // NEW
}
```

##### 2c. Destructure New Prop (Line 38)

```typescript
const ImageCache: React.FC<ImageCacheProps> = ({
  // ... existing props
  onCancelQueued, // NEW
}) => {
```

##### 2d. Update Action Icon Logic (Replace Lines 199-227)

```typescript
{/* Action Icon Cell - Right Side */}
<TableCell
  align="right"
  sx={{
    padding: "4px 8px",
    width: "40px",
  }}
>
  {(() => {
    const workflow = getWorkflowByImageIndex(item.index);
    const isQueued = workflow?.status === "queued";
    const isProcessing = workflow?.status === "pending" || workflow?.status === "processing";

    // QUEUED: Show cancel icon (orange)
    if (isQueued) {
      return (
        <IconButton
          onClick={() => {
            if (workflow?.workflow_id) {
              onCancelQueued(workflow.workflow_id);
            }
          }}
          sx={{ padding: 0 }}
          aria-label={t("imageCache.cancelQueuedTooltip")}
        >
          <CancelIcon
            sx={{
              color: "#ff9800", // Orange warning color
              fontSize: "1.8vh",
            }}
            titleAccess={t("imageCache.cancelQueuedTooltip")}
          />
        </IconButton>
      );
    }

    // PROCESSING: Show disabled gray X
    if (isProcessing) {
      return (
        <IconButton
          disabled
          sx={{ padding: 0 }}
          aria-label={t("imageCache.cannotCancelTooltip")}
        >
          <CloseIcon
            sx={{
              color: "rgba(0, 0, 0, 0.26)", // Disabled gray
              fontSize: "1.8vh",
            }}
            titleAccess={t("imageCache.cannotCancelTooltip")}
          />
        </IconButton>
      );
    }

    // COMPLETED/FAILED/NO WORKFLOW: Show blue close icon
    return (
      <IconButton
        onClick={() => {
          removeImage(item.index);
        }}
        sx={{ padding: 0 }}
        aria-label={t("imageCache.removeImageTooltip")}
      >
        <CloseIcon
          style={{
            color: colours.CFIA_Background_Blue,
            fontSize: "1.8vh",
          }}
          titleAccess={t("imageCache.removeImageTooltip")}
        />
      </IconButton>
    );
  })()}
</TableCell>
```

---

#### File 3: `Body.tsx`

**Location:** `frontend/src/components/body/Body.tsx`

**Changes Required:**

##### 3a. Add Handler Function (Around Line 415)

```typescript
/**
 * Cancel a queued inference item
 * @param workflowId - Temporary workflow ID (e.g., "temp-1234567890-0.5678")
 */
const handleCancelQueued = useCallback(
  (workflowId: string) => {
    const success = queueManagerRef.current.cancelQueued(workflowId);

    if (success) {
      addWarning(t("queue.cancelled"), 3000);
    } else {
      addError(t("queue.cancelFailed"), 5000);
    }
  },
  [addWarning, addError, t]
);
```

##### 3b. Pass to ImageCache Component (Around Line 560)

```typescript
<ImageCache
  // ... existing props
  onCancelQueued={handleCancelQueued} // NEW
/>
```

---

#### File 4: `useImageStore.ts`

**Location:** `frontend/src/stores/useImageStore.ts`

**Bug Fix:** Clean up workflow when removing image

**Modify `removeImage` method (Lines 56-84):**

```typescript
removeImage: (index: number) => {
  // Find workflow associated with this image BEFORE removing
  const workflow = useWorkflowStore.getState().getWorkflowByImageIndex(index);

  // Remove image from cache
  const newImages = state.images.filter((item) => item.index !== index);

  // Calculate next index
  let nextIndex = state.currentIndex;
  if (newImages.length === 0) {
    nextIndex = -1;
  } else if (index === state.currentIndex) {
    const itemsBefore = state.images.filter((item) => item.index < index);
    if (itemsBefore.length > 0) {
      nextIndex = itemsBefore[itemsBefore.length - 1].index;
    } else {
      const itemsAfter = state.images.filter((item) => item.index > index);
      if (itemsAfter.length > 0) {
        nextIndex = itemsAfter[0].index;
      } else {
        nextIndex = -1;
      }
    }
  }

  // Update state
  set({ images: newImages, currentIndex: nextIndex });

  // Clean up associated workflow (BUG FIX)
  if (workflow?.workflow_id) {
    useWorkflowStore.getState().removeWorkflow(workflow.workflow_id);
  }

  return nextIndex;
},
```

---

#### File 5: Translation Files

**Location:** `frontend/src/locales/en/main.ts`

**Add to `imageCache` section:**

```typescript
imageCache: {
  title: "CAPTURES",
  captureLabel: "Capture {{index}}",
  cancelQueuedTooltip: "Cancel queued inference",         // NEW
  cannotCancelTooltip: "Cannot cancel - processing started", // NEW
  removeImageTooltip: "Remove from cache",               // NEW
}
```

**Add to `queue` section:**

```typescript
queue: {
  full: "Queue is full. Please wait for current items to process.",
  cancelled: "Queued inference cancelled",               // NEW
  cancelFailed: "Failed to cancel - item may have already started processing", // NEW
}
```

**Location:** `frontend/src/locales/fr/main.ts`

```typescript
imageCache: {
  title: "CAPTURES",
  captureLabel: "Capture {{index}}",
  cancelQueuedTooltip: "Annuler l'inférence en attente",
  cannotCancelTooltip: "Impossible d'annuler - traitement commencé",
  removeImageTooltip: "Retirer du cache",
}

queue: {
  full: "La file d'attente est pleine. Veuillez attendre que les éléments actuels soient traités.",
  cancelled: "Inférence en attente annulée",
  cancelFailed: "Échec de l'annulation - l'élément a peut-être déjà commencé le traitement",
}
```

---

### 2. Type Definitions

**No changes needed** - `WorkflowStatus` already includes `"cancelled"` state (though we're not using it for this feature, just removing the workflow entirely)

---

## Edge Cases & Error Handling

### Edge Case 1: Race Condition - Cancelling During Submission

**Scenario:** User clicks cancel on item #1 while it's being submitted to `/inf`

**Handling:**

```typescript
cancelQueued(workflowId: string): boolean {
  // Check if still using temp ID
  if (!workflowId.startsWith("temp-")) {
    console.warn("Cannot cancel - already submitted");
    return false; // Already submitted, has real UUID now
  }

  // Check if still in queue
  const index = this.queue.findIndex(item => item.tempId === workflowId);
  if (index === -1) {
    console.warn("Cannot cancel - not in queue");
    return false; // Already removed from queue
  }

  // Safe to cancel
  // ...
}
```

**Result:** If submission already started, `cancelQueued()` returns false and shows error toast

---

### Edge Case 2: Queue Position Updates

**Scenario:** Queue has items at positions #1, #2, #3. User cancels #2.

**Expected Result:** #3 becomes #2

**Implementation:**

```typescript
// After removing item at index 1 (position #2)
this.queue.forEach((item, idx) => {
  item.queuePosition = idx + 1; // Renumber: 0→1, 1→2, 2→3
  this.config.workflowStore.updateWorkflowStatus(
    item.tempId,
    "queued",
    null,
    idx + 1
  );
});
```

**Result:** Queue positions automatically renumber sequentially

---

### Edge Case 3: Cancel While processNext() is Running

**Scenario:** `processNext()` is dequeuing item #1 when user cancels item #1

**Potential Issue:** Item might be removed from queue but submission still proceeds

**Mitigation:**

- `cancelQueued()` checks if item is in queue (index !== -1)
- If already dequeued by `processNext()`, not in queue, returns false
- User sees "Failed to cancel - item may have already started processing"
- This is acceptable behavior (small race window)

**Future Enhancement (Optional):**

- Add `submitting` status during POST request
- Disable cancel icon while status="submitting"
- Use AbortController to cancel fetch if needed

---

### Edge Case 4: Remove Image vs Cancel Queue

**Scenario:** User removes image from cache (clicks close icon on completed item) but workflow is still in store

**Current Bug:** Workflow persists in store after image removed

**Fix:** Modified `removeImage()` to call `removeWorkflow()` (see File 4 above)

**Result:** Workflow properly cleaned up when image removed

---

## Testing Plan

### Unit Tests

**File:** `frontend/src/services/WorkflowQueueManager.test.ts` (new)

```typescript
describe("WorkflowQueueManager.cancelQueued", () => {
  it("should cancel queued item and update positions", () => {
    // Setup: Queue 3 items
    manager.enqueue(0, "img-001");
    manager.enqueue(1, "img-002");
    manager.enqueue(2, "img-003");

    // Get temp ID of item #2
    const tempId = manager.queue[1].tempId;

    // Cancel item #2
    const result = manager.cancelQueued(tempId);

    // Verify
    expect(result).toBe(true);
    expect(manager.queue.length).toBe(2);
    expect(manager.queue[0].queuePosition).toBe(1);
    expect(manager.queue[1].queuePosition).toBe(2); // Was #3, now #2
  });

  it("should return false for non-temp workflow ID", () => {
    const result = manager.cancelQueued("real-uuid-123");
    expect(result).toBe(false);
  });

  it("should return false for workflow not in queue", () => {
    const result = manager.cancelQueued("temp-999-999");
    expect(result).toBe(false);
  });
});
```

**File:** `frontend/src/components/body/image_cache/ImageCache.test.tsx`

```typescript
describe("ImageCache cancel icon", () => {
  it("shows cancel icon for queued items", () => {
    // Setup: Image with queued workflow
    render(<ImageCache {...propsWithQueuedItem} />);

    // Find cancel icon
    const cancelIcon = screen.getByLabelText("Cancel queued inference");
    expect(cancelIcon).toBeInTheDocument();
  });

  it("calls onCancelQueued when cancel clicked", () => {
    const mockCancel = jest.fn();
    render(<ImageCache {...props} onCancelQueued={mockCancel} />);

    // Click cancel icon
    const cancelIcon = screen.getByLabelText("Cancel queued inference");
    fireEvent.click(cancelIcon);

    // Verify callback
    expect(mockCancel).toHaveBeenCalledWith("temp-123-456");
  });

  it("shows disabled close icon for processing items", () => {
    render(<ImageCache {...propsWithProcessingItem} />);

    // Find disabled icon
    const closeIcon = screen.getByLabelText("Cannot cancel - processing started");
    expect(closeIcon.closest("button")).toBeDisabled();
  });
});
```

---

### Integration Tests

**Manual Test Scenarios:**

#### Test 1: Cancel Single Queued Item

1. Add 3 images to cache
2. Click CLASSIFY on all 3 → Queue shows #1, #2, #3
3. Click cancel icon on item #2
4. Verify:
   - ✓ Item #2 removed from queue
   - ✓ Item #3 renumbered to #2
   - ✓ Toast shows "Queued inference cancelled"
   - ✓ Queue continues processing #1

#### Test 2: Cancel First in Queue

1. Queue 3 items → #1 is processing, #2 and #3 queued
2. Click cancel on #2
3. Verify:
   - ✓ #2 removed
   - ✓ #3 becomes #2
   - ✓ When #1 completes, #2 (formerly #3) starts processing

#### Test 3: Cannot Cancel Processing Item

1. Queue 2 items → #1 starts processing (spinner shows)
2. Try to click close icon on #1
3. Verify:
   - ✓ Icon is grayed out and disabled
   - ✓ Tooltip shows "Cannot cancel - processing started"
   - ✓ Click does nothing
   - ✓ Processing continues normally

#### Test 4: Remove Completed Image (Regression Test)

1. Complete inference on image
2. Click close icon (blue X)
3. Verify:
   - ✓ Image removed from cache
   - ✓ Workflow removed from store (bug fix)
   - ✓ No errors in console

#### Test 5: Race Condition

1. Queue 1 item → It starts processing immediately
2. Quickly try to cancel before status updates to "pending"
3. Verify:
   - ✓ Either cancels successfully (if still in queue)
   - ✓ Or shows "Failed to cancel" toast (if already dequeued)
   - ✓ No crashes or errors

#### Test 6: Cancel All Then Add More

1. Queue 5 items → #1, #2, #3, #4, #5
2. Cancel #2, #3, #4 → Leaves #1, #5 (renumbered to #1, #2)
3. Add 3 more items
4. Verify:
   - ✓ New items numbered #3, #4, #5
   - ✓ Processing continues in correct order

---

### Accessibility Tests

**Keyboard Navigation:**

- ✓ Tab to cancel icon button
- ✓ Enter/Space to activate cancel
- ✓ Screen reader announces action ("Cancel queued inference")

**Color Contrast:**

- ✓ Orange cancel icon passes WCAG AA (4.5:1 contrast ratio)
- ✓ Gray disabled icon clearly distinguishable
- ✓ Tooltips readable

**Focus Management:**

- ✓ Focus remains on cache after cancellation
- ✓ No focus trap issues

---

## Performance Considerations

### Impact Analysis

**Minimal Performance Impact:**

- Cancel operation is O(n) where n = queue size (max 10)
- Queue position updates are also O(n)
- No network requests involved (purely frontend operation)
- No re-renders of unaffected components

**Potential Optimization (Not Required):**

- Use Map instead of Array for queue if frequent cancellations expected
- Debounce position updates if batch cancellation added in future

---

## Rollout Plan

### Phase 1: Single Item Cancellation (This Plan)

**Timeline:** 1-2 days

**Backend:** None required ✅

**Frontend:**

- [ ] Update `WorkflowQueueManager.ts` (add `cancelQueued()`)
- [ ] Update `ImageCache.tsx` (add cancel icon logic)
- [ ] Update `Body.tsx` (add handler)
- [ ] Fix `useImageStore.ts` (workflow cleanup bug)
- [ ] Add translations (EN + FR)
- [ ] Write unit tests
- [ ] Manual testing
- [ ] Deploy to staging
- [ ] User acceptance testing
- [ ] Deploy to production

### Phase 2: Backend Workflow Cancellation (Future)

**Timeline:** TBD (requires backend changes)

**Scope:**

- [ ] Add `DELETE /workflow/{workflow_id}` endpoint
- [ ] Cancel DBOS workflows
- [ ] Clean up blob storage
- [ ] Handle Defender scanning in progress
- [ ] Update UI to support cancelling "pending"/"processing" items

**Dependencies:**

- [ ] Backend team availability
- [ ] DBOS workflow cancellation research
- [ ] Azure Blob storage cleanup strategy

---

## Success Criteria

After implementation, verify:

### Functional

- [ ] Users can cancel queued items (status="queued")
- [ ] Queue positions update correctly after cancellation
- [ ] Processing items show disabled icon
- [ ] Completed items can still be removed from cache
- [ ] Toast notifications provide clear feedback

### Visual

- [ ] Cancel icon is orange and clearly distinguishable
- [ ] Disabled icon is grayed out
- [ ] Tooltips are helpful and accurate
- [ ] Layout remains consistent with current design

### Technical

- [ ] No memory leaks (workflows properly cleaned up)
- [ ] No race condition crashes
- [ ] Queue state remains consistent
- [ ] All tests pass

### User Experience

- [ ] Intuitive behavior (no confirmation needed for cancel)
- [ ] Immediate feedback (instant removal + toast)
- [ ] Error messages are helpful
- [ ] Keyboard accessible

---

## Risks & Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Race condition during submission | Medium | Low | Return false from cancelQueued(), show error toast |
| User confusion (cancel vs remove) | Low | Medium | Use different icons (cancel=orange, remove=blue), clear tooltips |
| Queue desync (positions wrong) | Low | High | Thorough testing, add queue validation in dev mode |
| Workflow not cleaned up | Low | Medium | Fixed by updating removeImage() to call removeWorkflow() |
| Translation missing | Low | Low | Add to both EN and FR simultaneously |

---

## Related Documentation

**See Also:**

- Batch Upload Cancel Plan: `frontend/docs/BATCH_UPLOAD_CANCEL_IMPLEMENTATION_PLAN.md`
- Workflow Architecture: `CLAUDE.md` (DBOS Workflow Pattern section)
- Queue Management: Code in `frontend/src/services/WorkflowQueueManager.ts`
- State Management: `frontend/src/stores/useWorkflowStore.ts`

---

## Appendix A: File Change Summary

| File | Lines Changed | Type | Complexity |
|------|--------------|------|-----------|
| `WorkflowQueueManager.ts` | +45 | New methods | Medium |
| `ImageCache.tsx` | ~60 | Modify logic | Medium |
| `Body.tsx` | +12 | New handler | Low |
| `useImageStore.ts` | +4 | Bug fix | Low |
| `locales/en/main.ts` | +5 | Translations | Low |
| `locales/fr/main.ts` | +5 | Translations | Low |
| **Total** | **~131 lines** | | |

---

## Appendix B: Queue State Diagram

```text
┌─────────────────────────────────────────────────────────────┐
│                    QUEUE STATE MACHINE                       │
└─────────────────────────────────────────────────────────────┘

  User clicks CLASSIFY
         │
         ↓
    ┌──────────┐
    │  QUEUED  │ ← Can Cancel (Orange X icon)
    │  temp-*  │   Remove from queue array
    │  Pos 1-10│   Update positions
    └──────────┘   Clean up store
         │
         │ processNext() dequeues
         │
         ↓
    POST /inf submitted
         │
         ↓
    ┌──────────┐
    │ PENDING  │ ← Cannot Cancel (Gray disabled icon)
    │ UUID-*   │   Backend workflow running
    │ Polling  │   Requires API endpoint
    └──────────┘
         │
         ↓
    ┌──────────┐
    │PROCESSING│ ← Cannot Cancel (Gray disabled icon)
    │ Active   │   ML inference running
    │ Polling  │
    └──────────┘
         │
         ↓
    ┌──────────┐
    │COMPLETED │ ← Can Remove (Blue X icon)
    │   or     │   Delete from cache
    │  FAILED  │   Clean up store
    └──────────┘
```

---

## Appendix C: Developer Notes

### Why Only Cancel Queued Items?

**Technical Reason:**

- Queued items exist only in frontend memory (JavaScript array)
- No backend state created yet
- Safe to remove without side effects

**Backend Complexity:**

- "Pending"/"Processing" items have DBOS workflows running
- Blob storage uploads may be in progress
- Microsoft Defender scanning may be active
- ML inference might be queued in remote service
- Cancellation would require coordinated cleanup across multiple systems

**User Impact:**

- Queued items represent ~80% of cancellation use cases
- Processing items are usually only active for 30-60 seconds
- Most users want to cancel before processing starts

### Future Enhancements

**Priority 1 (This Plan):**

- ✅ Cancel queued items only

**Priority 2 (Phase 2):**

- Add backend cancellation endpoint
- Cancel pending/processing workflows
- Clean up partial blob uploads

**Priority 3 (Nice to Have):**

- Batch cancellation (cancel multiple items)
- Undo cancellation (restore to queue)
- Drag-and-drop queue reordering
- Keyboard shortcuts (ESC to cancel selected item)

---

## Questions & Answers

**Q: Why no confirmation dialog for cancel?**
A: Queued items haven't started processing yet, so cancellation is low-risk. User can easily re-add to queue if cancelled by mistake. Confirmation would add friction.

**Q: What happens if queue is processing and user cancels all queued items?**
A: Active workflow continues processing. Once complete, queue is empty so no new items start. This is expected behavior.

**Q: Can we cancel by clicking the queue position chip instead of separate icon?**
A: Possible UX alternative. Current design uses dedicated cancel icon for clarity and consistency with other action icons.

**Q: Should cancelled items go to a "recycle bin"?**
A: Not needed - items are still in cache (not deleted), just removed from queue. User can re-classify if desired.

**Q: What about cancelling the active workflow (#1 processing)?**
A: Out of scope for Phase 1. Requires backend support. See Phase 2 plan.

---

## Conclusion

This implementation provides a surgical solution for cancelling queued inference items without requiring backend changes. It addresses the most common user frustration (accidentally queueing the wrong image) while maintaining system stability and avoiding complex backend coordination.

The scope is intentionally limited to what can be done safely in the frontend, with a clear path forward for Phase 2 (backend workflow cancellation) if user feedback indicates it's needed.

**Estimated Implementation Time:** 1-2 days (including testing)

**Risk Level:** Low (no backend changes, well-isolated feature)

**User Impact:** High (frequently requested feature, improves workflow efficiency)
