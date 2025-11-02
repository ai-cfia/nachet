# Notification System Reference

**Created:** 2025-11-02
**Status:** Production Ready
**Version:** 1.0

## Overview

The Nachet notification system is a modern, hybrid approach to user notifications that replaces browser `alert()` calls with a sophisticated toast + error log system. It provides non-intrusive feedback while maintaining a persistent record of errors for user review.

---

## Architecture

### System Components

```text
┌─────────────────────────────────────────────────────────┐
│                   Notification System                    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ┌──────────────┐         ┌─────────────────────────┐  │
│  │              │         │                         │  │
│  │  Zustand     │◄────────│  Component Calls        │  │
│  │  Store       │         │  addError()             │  │
│  │              │         │  addWarning()           │  │
│  └──────┬───────┘         │  addInfo()              │  │
│         │                 │  addSuccess()           │  │
│         │                 └─────────────────────────┘  │
│         │                                              │
│    ┌────┴─────┐                                        │
│    │          │                                        │
│    ▼          ▼                                        │
│  ┌──────────────┐       ┌─────────────────────────┐  │
│  │              │       │                         │  │
│  │  Toast       │       │  Error Log Modal        │  │
│  │  Component   │       │  + Badge                │  │
│  │              │       │                         │  │
│  └──────────────┘       └─────────────────────────┘  │
│   Top-Center              On Demand                   │
│   Auto-Dismiss            Persistent                  │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### Component Hierarchy

1. **Store Layer** - `useNotificationStore.ts`
   - Zustand state management
   - Session-only storage (no localStorage)
   - Separate collections for errors and toasts

2. **UI Layer**
   - **ToastNotification.tsx** - Transient warnings/info
   - **NotificationLogPopup** - Persistent error log
   - **LOG Button** - Access point with badge indicator

3. **Integration Layer**
   - Modal state in `useModalStore`
   - Translation support via `react-i18next`
   - Material-UI components

---

## Data Flow

### Adding a Notification

```typescript
// 1. Component triggers notification
const { addError } = useNotificationStore();
addError(t("auth.signInRequired"), "auth");

// 2. Store creates notification object
{
  id: "uuid-v4-generated",
  type: "error",
  message: "You must be signed in...",
  timestamp: 1699000000000,
  read: false,
  source: "auth"
}

// 3. Store adds to appropriate collection
- Errors → errors[] array (max 100)
- Warnings/Info/Success → toasts[] array

// 4. UI components react to state changes
- ToastNotification renders new toast
- Badge updates unread count
```

### Reading Notifications

```typescript
// 1. User clicks LOG button
onClick={() => {
  openNotificationLog();    // Opens modal
  markAllErrorsAsRead();    // Marks errors as read
}}

// 2. Modal displays errors
{errors.map(error => (
  <ListItem>
    <ErrorIcon />
    {error.message}
    {formatTimestamp(error.timestamp)}
    <DismissButton />
  </ListItem>
))}

// 3. Badge clears (all marked as read)
getUnreadErrorCount() → 0
```

---

## Store API

### `useNotificationStore`

**Location:** `frontend/src/stores/useNotificationStore.ts`

#### State Interface

```typescript
interface NotificationState {
  // Error log (persistent in session)
  errors: Notification[];

  // Transient toasts
  toasts: Toast[];

  // Actions
  addError: (message: string, source?: string) => void;
  addWarning: (message: string, duration?: number) => void;
  addInfo: (message: string, duration?: number) => void;
  addSuccess: (message: string, duration?: number) => void;

  dismissError: (id: string) => void;
  clearAllErrors: () => void;
  markErrorAsRead: (id: string) => void;
  markAllErrorsAsRead: () => void;

  removeToast: (id: string) => void;

  // Queries
  getUnreadErrorCount: () => number;
  hasUnreadErrors: () => boolean;
}
```

#### Data Types

```typescript
interface Notification {
  id: string; // UUID v4
  type: "error" | "warning" | "info";
  message: string; // Translated user message
  timestamp: number; // Date.now() in milliseconds
  read: boolean; // User has viewed in modal
  source?: string; // e.g., "auth", "inference", "storage"
}

interface Toast {
  id: string; // UUID v4
  type: "warning" | "info" | "success";
  message: string; // Translated user message
  duration: number; // Auto-dismiss time (ms)
}
```

#### Methods

**Adding Notifications:**

```typescript
// Add error (goes to modal log)
addError(message: string, source?: string)
// Example: addError(t("auth.signInRequired"), "auth")

// Add warning toast (8-10s auto-dismiss)
addWarning(message: string, duration = 10000)
// Example: addWarning(t("queue.full"), 10000)

// Add info toast (5s auto-dismiss)
addInfo(message: string, duration = 5000)
// Example: addInfo(t("operation.complete"), 5000)

// Add success toast (5s auto-dismiss)
addSuccess(message: string, duration = 5000)
// Example: addSuccess(t("save.success"), 5000)
```

**Managing Errors:**

```typescript
// Dismiss single error by ID
dismissError(id: string)

// Clear all errors
clearAllErrors()

// Mark single error as read
markErrorAsRead(id: string)

// Mark all errors as read (called when modal opens)
markAllErrorsAsRead()
```

**Querying State:**

```typescript
// Get count of unread errors (for badge)
const count = getUnreadErrorCount();

// Check if any unread errors exist
const hasUnread = hasUnreadErrors();
```

---

## Usage Patterns

### Pattern 1: Error Notification

**Use Case:** Critical errors requiring user attention

```typescript
import { useNotificationStore } from "@stores/useNotificationStore";
import { useTranslation } from "react-i18next";

const MyComponent = () => {
  const { addError } = useNotificationStore();
  const { t } = useTranslation("errors");

  const handleOperation = async () => {
    try {
      await someRiskyOperation();
    } catch (error) {
      // Add error to persistent log
      addError(t("operation.failed"), "myComponent");
      console.error(error);
    }
  };
};
```

**Result:**

- Error appears in LOG modal
- Badge increments unread count
- User must open modal to view
- Error persists until dismissed or session ends

---

### Pattern 2: Warning Toast

**Use Case:** Non-critical warnings (validation, state issues)

```typescript
import { useNotificationStore } from "@stores/useNotificationStore";
import { useTranslation } from "react-i18next";

const MyComponent = () => {
  const { addWarning } = useNotificationStore();
  const { t } = useTranslation("validation");

  const handleSubmit = () => {
    if (!isValid) {
      // Show warning toast (8 seconds)
      addWarning(t("form.invalid"), 8000);
      return;
    }
    // Continue...
  };
};
```

**Result:**

- Toast appears at top-center
- Auto-dismisses after 8 seconds
- User can manually dismiss
- Does NOT go to error log
- Does NOT affect badge

---

### Pattern 3: Info/Success Toast

**Use Case:** Informational messages, success confirmations

```typescript
import { useNotificationStore } from "@stores/useNotificationStore";
import { useTranslation } from "react-i18next";

const MyComponent = () => {
  const { addInfo, addSuccess } = useNotificationStore();
  const { t } = useTranslation("messages");

  const handleSave = async () => {
    addInfo(t("saving"), 5000);

    await saveData();

    addSuccess(t("saved"), 5000);
  };
};
```

**Result:**

- Toast appears at top-center
- Auto-dismisses after 5 seconds
- Blue (info) or green (success) styling
- Does NOT go to error log

---

### Pattern 4: Authentication Errors

**Use Case:** Common pattern in the codebase

```typescript
import { useNotificationStore } from "@stores/useNotificationStore";
import { useTranslation } from "react-i18next";
import { useMsal, useIsAuthenticated } from "@azure/msal-react";
import { InteractionStatus } from "@azure/msal-browser";

const MyComponent = () => {
  const { addError, addWarning } = useNotificationStore();
  const { t } = useTranslation("errors");
  const isAuthenticated = useIsAuthenticated();
  const { inProgress } = useMsal();

  const handleAction = () => {
    // Check authentication
    if (!isAuthenticated) {
      addError(t("auth.signInRequired"), "auth");
      return;
    }

    // Check if auth in progress
    if (inProgress !== InteractionStatus.None) {
      addWarning(t("auth.inProgress"), 8000);
      return;
    }

    // Continue with authenticated action...
  };
};
```

---

## UI Components

### ToastNotification Component

**Location:** `frontend/src/components/common/ToastNotification.tsx`

**Purpose:** Display transient toast notifications

**Features:**

- Positioned at top-center of viewport
- Stacks vertically (multiple toasts)
- Auto-dismiss based on duration
- Manual dismiss with X button
- Material-UI Snackbar + Alert

**Styling:**

- Warning: Yellow/amber (`severity="warning"`)
- Info: Blue (`severity="info"`)
- Success: Green (`severity="success"`)
- Z-index: 9999 (above modals)

**Auto-Integration:**

- Rendered at root level in `body.tsx`
- Always visible (controlled by store state)
- No props required

---

### NotificationLogPopup Component

**Location:** `frontend/src/components/body/notification_log_popup/`

**Purpose:** Display persistent error log in modal

**Structure:**

```text
NotificationLogPopupContainer.tsx  (Logic)
  ├─ Connects to useNotificationStore
  ├─ Connects to useModalStore
  ├─ Connects to useTranslation
  ├─ Handles timestamp formatting
  └─ Passes props to View

NotificationLogPopupView.tsx  (UI)
  ├─ Material-UI Dialog
  ├─ Header with title + Clear All + Close
  ├─ Scrollable error list (max-height: 60vh)
  ├─ Empty state (icon + message)
  └─ Footer with Close button
```

**Features:**

- Modal dialog (maxWidth: md, fullWidth)
- Scrollable list for 10+ errors
- Empty state when no errors
- Individual dismiss buttons
- Clear All button (when errors exist)
- Actual timestamps (locale-aware)

**Translations:**

- Title: "Error Log" / "Journal des erreurs"
- Empty: "No errors to display" / "Aucune erreur à afficher"
- Clear All: "Clear All" / "Tout effacer"
- Close: "Close" / "Fermer"

---

### LOG Button with Badge

**Location:** `frontend/src/components/body/microscope_feed/MicroscopeFeedControlsView.tsx`

**Purpose:** Access point to error log with visual indicator

**Implementation:**

```typescript
const { getUnreadErrorCount } = useNotificationStore();
const { openNotificationLog } = useModalStore();
const unreadCount = getUnreadErrorCount();

<ButtonMicroscopeFeed
  label={t("microscopeFeed.controls.notificationsLabel")}
  icon={
    <Badge badgeContent={unreadCount} color="error">
      <NotificationsIcon color="inherit" style={iconStyle} />
    </Badge>
  }
  onClick={() => {
    openNotificationLog();
    markAllErrorsAsRead();
  }}
/>
```

**Badge Behavior:**

- Shows count of unread errors
- Red background (`color="error"`)
- Hidden when count is 0
- Clears when modal opened (auto-marks as read)
- Updates in real-time

**Button Labels:**

- English: "LOG"
- French: "JOURNAL"

---

## Configuration

### Default Settings

**Error Log:**

- Max errors: 100 (FIFO when exceeded)
- Storage: Session-only (clears on reload)
- Read state: Managed per error

**Toasts:**

- Default warning duration: 10000ms (10s)
- Default info duration: 5000ms (5s)
- Default success duration: 5000ms (5s)
- Position: Top-center
- Stacking: Vertical (unlimited, practical limit ~5)

### Customization

**Changing Toast Duration:**

```typescript
// Short warning (5 seconds)
addWarning(t("message"), 5000);

// Long warning (15 seconds)
addWarning(t("message"), 15000);

// Default (10 seconds)
addWarning(t("message"));
```

**Changing Toast Position:**

Edit `ToastNotification.tsx`:

```typescript
// Current: Top-center
sx={{
  position: "fixed",
  top: 20,
  left: "50%",
  transform: "translateX(-50%)",
}}

// Alternative: Bottom-right
sx={{
  position: "fixed",
  bottom: 20,
  right: 20,
}}
```

**Changing Max Error Limit:**

Edit `useNotificationStore.ts`:

```typescript
addError: (message: string, source?: string) => {
  // ...
  const updatedErrors = [...state.errors, newError];
  if (updatedErrors.length > 100) {
    // Change this value
    updatedErrors.shift();
  }
  // ...
};
```

---

## Migration Guide

### Replacing Old `alert()` Calls

**Before:**

```typescript
alert(t("auth.signInRequired"));
```

**After (Error):**

```typescript
import { useNotificationStore } from "@stores/useNotificationStore";

const { addError } = useNotificationStore();
addError(t("auth.signInRequired"), "auth");
```

**Before:**

```typescript
alert(t("queue.full"));
```

**After (Warning):**

```typescript
import { useNotificationStore } from "@stores/useNotificationStore";

const { addWarning } = useNotificationStore();
addWarning(t("queue.full"), 10000);
```

### Decision Tree: Error vs Warning

```text
Is this a critical error that requires user action?
├─ YES → Use addError()
│   - Authentication failures
│   - Data fetch failures
│   - Operation failures
│   - Save/delete errors
│
└─ NO → Use addWarning() or addInfo()
    - Validation warnings
    - State warnings (auth in progress)
    - Queue full
    - Informational messages
```

### Source Parameter Guidelines

Use descriptive source strings for categorization:

- `"auth"` - Authentication errors
- `"inference"` - ML inference errors
- `"storage"` - Azure storage errors
- `"directory"` - Directory/folder errors
- `"registration"` - User registration errors
- `"save"` - Save operation errors
- `"validation"` - Validation errors
- `null` or omit - Generic/uncategorized

---

## Best Practices

### DO ✅

1. **Always translate messages:**

   ```typescript
   addError(t("errors.key"), "source"); // Good
   ```

2. **Use appropriate notification type:**

   ```typescript
   addError(...)    // Critical failures
   addWarning(...)  // Non-critical issues
   addInfo(...)     // Informational
   addSuccess(...)  // Confirmations
   ```

3. **Provide source context:**

   ```typescript
   addError(t("error"), "auth"); // Good - categorized
   ```

4. **Set reasonable durations:**

   ```typescript
   addWarning(t("message"), 8000); // 8s for short message
   addWarning(t("long"), 15000); // 15s for longer message
   ```

5. **Log errors to console:**

   ```typescript
   .catch(error => {
     addError(t("failed"), "api");
     console.error(error);  // Good - helps debugging
   });
   ```

### DON'T ❌

1. **Don't use hardcoded English:**

   ```typescript
   addError("You must sign in"); // Bad - not translated
   ```

2. **Don't mix notification types:**

   ```typescript
   addError(t("success")); // Bad - success shouldn't be error
   ```

3. **Don't overuse errors:**

   ```typescript
   if (!valid) {
     addError(t("invalid")); // Bad - use addWarning() instead
   }
   ```

4. **Don't set very long durations:**

   ```typescript
   addWarning(t("msg"), 60000); // Bad - 60s is too long
   ```

5. **Don't suppress console errors:**

   ```typescript
   .catch(error => {
     addError(t("failed"));
     // Bad - should log error for debugging
   });
   ```

---

## Troubleshooting

### Issue: Toasts Not Appearing

**Possible Causes:**

1. ToastNotification component not rendered
2. Store not imported correctly
3. Z-index conflict

**Solution:**

```typescript
// 1. Check body.tsx has ToastNotification
return (
  <>
    <ToastNotification />
    {/* ... rest of app */}
  </>
);

// 2. Verify import
import { useNotificationStore } from "@stores/useNotificationStore";

// 3. Check z-index in ToastNotification.tsx
sx={{ zIndex: 9999 }}  // Should be higher than modals
```

---

### Issue: Modal Not Opening

**Possible Causes:**

1. Modal state not connected
2. Modal component not registered
3. Modal not conditionally rendered

**Solution:**

```typescript
// 1. Check modal state in useModalStore
notificationLogOpen: boolean;
openNotificationLog: () => void;
closeNotificationLog: () => void;

// 2. Check body/index.ts exports
export { NotificationLogPopup } from "./notification_log_popup/...";

// 3. Check body.tsx conditional render
{notificationLogOpen && <NotificationLogPopup />}
```

---

### Issue: Badge Not Updating

**Possible Causes:**

1. Not marking errors as read
2. Store selector not reactive
3. Component not re-rendering

**Solution:**

```typescript
// 1. Ensure markAllErrorsAsRead() called on modal open
onClick={() => {
  openNotificationLog();
  markAllErrorsAsRead();  // Important!
}}

// 2. Use store hook in component
const { getUnreadErrorCount } = useNotificationStore();
const count = getUnreadErrorCount();  // Reactive

// 3. Use count directly in JSX
<Badge badgeContent={count} />  // Will re-render on change
```

---

### Issue: Translations Not Working

**Possible Causes:**

1. Translation keys missing
2. Wrong namespace
3. useTranslation not called

**Solution:**

```typescript
// 1. Check translation files
// frontend/src/locales/en/popups.ts
notifications: {
  title: "Error Log",
  // ...
}

// 2. Use correct namespace
const { t } = useTranslation("popups");
t("notifications.title");  // Good

// 3. Check container passes translations
<NotificationLogPopupView
  translations={{
    title: t("notifications.title"),
    // ...
  }}
/>
```

---

## Performance Considerations

### Memory Management

**Error Log Limit:**

- Max 100 errors enforced automatically
- FIFO removal when limit exceeded
- Session-only storage (clears on reload)

**Toast Cleanup:**

- Auto-removed after duration + animation
- Manual dismiss removes immediately
- No accumulation in store

### Re-render Optimization

**Zustand Selectors:**

```typescript
// Bad - re-renders on any store change
const store = useNotificationStore();

// Good - only re-renders when errors change
const errors = useNotificationStore((state) => state.errors);

// Good - only re-renders when count changes
const count = useNotificationStore((state) => state.getUnreadErrorCount());
```

**Memoization:**

```typescript
// Timestamp formatting is memoized in container
const formatTimestamp = useMemo(() => {
  return (timestamp: number) => new Date(timestamp).toLocaleString();
}, []);
```

---

## Accessibility

### Keyboard Navigation

1. **Focus on LOG button:** Tab key
2. **Open modal:** Enter or Space
3. **Navigate modal:** Tab (cycles through interactive elements)
4. **Dismiss error:** Enter on dismiss button
5. **Close modal:** Escape key

### Screen Reader Support

**ARIA Labels:**

- Modal title: "Error Log"
- Close buttons: aria-label="close"
- Dismiss buttons: aria-label="dismiss"

**Live Regions:**

- Toasts use Alert component (role="alert")
- Auto-announced by screen readers
- Non-intrusive announcements

### Semantic HTML

- Dialog uses `<Dialog>` (role="dialog")
- List uses `<List>` and `<ListItem>`
- Buttons use `<Button>` with proper labels
- Icons include accessible text

---

## Testing

### Unit Tests

**Store Tests:**

```bash
# Test file: useNotificationStore.test.ts
- addError() adds to errors array
- addWarning() adds to toasts array
- dismissError() removes by ID
- clearAllErrors() empties array
- getUnreadErrorCount() returns correct count
- Max 100 errors enforced
```

**Component Tests:**

```bash
# Test file: ToastNotification.test.tsx
- Renders toast with message
- Auto-dismiss after duration
- Manual dismiss works
- Multiple toasts stack

# Test file: NotificationLogPopupView.test.tsx
- Renders error list
- Empty state when no errors
- Dismiss individual error
- Clear all errors
- Timestamp formatting
```

### Manual Testing

See **[NOTIFICATION_SYSTEM_TESTING.md](./NOTIFICATION_SYSTEM_TESTING.md)** for comprehensive testing guide with 50+ test cases.

**Quick Smoke Test:**

1. Generate error: Click CLASSIFY without auth → Check badge
2. Open modal: Click LOG → Verify errors display
3. Dismiss error: Click X → Verify removed
4. Generate warning: Fill form invalid → Check toast appears
5. Switch language: EN ↔ FR → Verify translations

---

## FAQ

### Q: Why separate errors from warnings?

**A:** Errors require user attention and review (persistent log), while warnings are transient information that auto-dismisses. This prevents important errors from being missed while keeping the UI uncluttered.

---

### Q: Why session-only storage?

**A:**

1. Simpler implementation (no sync with localStorage)
2. No storage bloat over time
3. Errors are contextual to current session
4. Aligns with workflow-based nature of app
5. Users start fresh each session

---

### Q: Can I change toast duration per message?

**A:** Yes, pass duration as second parameter:

```typescript
addWarning(t("short"), 5000); // 5 seconds
addWarning(t("medium"), 10000); // 10 seconds (default)
addWarning(t("long"), 15000); // 15 seconds
```

---

### Q: How do I add desktop notifications?

**A:** Desktop notifications (browser Notification API) are out of scope for v1.0. They would require:

1. User permission prompt
2. Different UX for browser notifications
3. Handling of notification clicks
4. Fallback for unsupported browsers

Consider implementing in future version if needed.

---

### Q: Can errors persist across sessions?

**A:** Not in v1.0 (session-only storage by design). To persist:

1. Add localStorage sync in store
2. Add migration/versioning for stored data
3. Add UI to clear old errors
4. Consider privacy implications

---

### Q: How do I categorize errors?

**A:** Use the `source` parameter:

```typescript
addError(t("error"), "inference"); // ML errors
addError(t("error"), "auth"); // Auth errors
addError(t("error"), "storage"); // Storage errors
```

Source is stored with error but not currently displayed in UI. Could be used for filtering in future.

---

### Q: What's the difference between `addInfo()` and `addSuccess()`?

**A:** Visual styling only:

- `addInfo()` → Blue toast, info icon (ℹ️)
- `addSuccess()` → Green toast, success icon (✓)

Both auto-dismiss after 5 seconds by default.

---

## Related Documentation

- **[NOTIFICATION_SYSTEM_TESTING.md](./NOTIFICATION_SYSTEM_TESTING.md)** - Testing guide (Phase 5)
- **[I18N_REFERENCE.md](./I18N_REFERENCE.md)** - Translation system
- **[TESTING.md](../TESTING.md)** - General testing procedures

---

**Version:** 1.0
**Last Updated:** 2025-11-02
**Status:** Production Ready
**Maintainer:** Development Team
