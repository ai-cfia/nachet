# Notification System Testing Guide

**Created:** 2025-11-02
**Status:** Ready for Testing
**Related:** NOTIFICATION_SYSTEM_PLAN.md

## Overview

This document provides comprehensive testing procedures for the notification system implementation. The system replaces 21 browser `alert()` calls with a modern hybrid notification system featuring:

- **Transient toasts** (top-center, auto-dismiss)
- **Persistent error log modal** (user-reviewed)
- **Badge indicator** (unread error count)
- **Full internationalization** (English/French)

---

## Phase 5: Testing & Validation

- [ ] **Phase 5 Complete**

### 5.1 Build Verification

- [ ] **Task 5.1 Complete**

**Commands:**

```bash
cd frontend
npm run format        # Auto-format all code
npm run lint          # ESLint check
npm run build         # TypeScript + Vite build
```

**Expected Results:**

- [ ] Prettier formatting passed (no changes needed)
- [ ] ESLint passed with max-warnings 0
- [ ] TypeScript compilation passed (no errors)
- [ ] Vite build successful

**If Build Fails:**

1. Check console output for specific errors
2. Fix TypeScript type errors
3. Fix ESLint warnings
4. Re-run build commands

---

### 5.2 Manual Testing Checklist

- [ ] **Task 5.2 Complete**

#### A. Error Notifications (Modal Log)

**Test Cases:**

- [ ] **Test 1: Auth Sign-In Required Error**
  - Action: Click CLASSIFY without being signed in
  - Expected: Error appears in notification log modal
  - Badge: Shows count "1"

- [ ] **Test 2: Inference Fetch Failed Error**
  - Action: Trigger inference with backend unavailable
  - Expected: Error appears in log with timestamp
  - Badge: Increments count

- [ ] **Test 3: Badge Shows Unread Count**
  - Action: Generate 3 errors without opening modal
  - Expected: Badge shows "3"
  - Verify: Badge is red with white text

- [ ] **Test 4: Open Modal (LOG Button)**
  - Action: Click "LOG" button in controls
  - Expected: Modal opens with error list
  - Badge: Clears to "0" (errors marked as read)

- [ ] **Test 5: Timestamp Display**
  - Action: View errors in modal
  - Expected: Shows actual timestamp (e.g., "11/2/2025, 2:30:45 PM")
  - Verify: Timestamp updates with browser locale

- [ ] **Test 6: Individual Dismiss**
  - Action: Click X button on individual error
  - Expected: Error removed from list
  - List: Updates immediately

- [ ] **Test 7: Clear All Button**
  - Action: Click "Clear All" button in modal header
  - Expected: All errors removed
  - State: Empty state displays

- [ ] **Test 8: Empty State**
  - Action: Clear all errors
  - Expected: Shows icon + "No errors to display"
  - Button: "Clear All" button hidden

- [ ] **Test 9: Modal Close**
  - Action: Click X button or "Close" button
  - Expected: Modal closes
  - Badge: Stays at 0 (already read)

- [ ] **Test 10: Errors Persist in Session**
  - Action: Add errors, navigate app (don't reload)
  - Expected: Errors remain in log
  - Verify: Badge count persists

- [ ] **Test 11: Errors Clear on Reload**
  - Action: Refresh browser (F5)
  - Expected: Error log empty
  - Badge: Shows 0

- [ ] **Test 12: Max 100 Errors Limit**
  - Action: Generate 101+ errors (script/automation)
  - Expected: Only last 100 kept
  - Verify: Oldest errors removed

---

#### B. Warning Notifications (Toasts)

**Test Cases:**

- [ ] **Test 13: Queue Full Warning**
  - Action: Trigger "queue is full" condition
  - Expected: Toast appears at top-center
  - Color: Yellow/amber background
  - Duration: Auto-dismiss after 10 seconds

- [ ] **Test 14: Auth In Progress Warning**
  - Action: Trigger during authentication flow
  - Expected: Toast appears at top-center
  - Color: Yellow/amber background
  - Duration: Auto-dismiss after 8 seconds

- [ ] **Test 15: Directory Not Selected Warning**
  - Action: Attempt operation without selecting directory
  - Expected: Toast appears with message
  - Duration: Auto-dismiss after 8 seconds

- [ ] **Test 16: Toast Auto-Dismiss**
  - Action: Trigger warning, wait 10 seconds
  - Expected: Toast disappears automatically
  - Verify: No manual action required

- [ ] **Test 17: Toast Manual Dismiss**
  - Action: Click X button on toast
  - Expected: Toast disappears immediately
  - Verify: Doesn't wait for auto-dismiss

- [ ] **Test 18: Multiple Toasts Stack**
  - Action: Trigger 3 warnings quickly
  - Expected: Toasts stack vertically (top-center)
  - Spacing: Consistent gap between toasts
  - Verify: All visible simultaneously

- [ ] **Test 19: Toast Styling (Warning)**
  - Expected: Yellow/amber Alert component
  - Icon: Warning icon (⚠️)
  - Text: Message clearly readable

---

#### C. Info/Success Notifications (Future)

**Test Cases:**

- [ ] **Test 20: Info Toast (if implemented)**
  - Action: Trigger info message
  - Expected: Blue toast, 5 second auto-dismiss
  - Icon: Info icon (ℹ️)

- [ ] **Test 21: Success Toast (if implemented)**
  - Action: Trigger success message
  - Expected: Green toast, 5 second auto-dismiss
  - Icon: Success icon (✓)

---

#### D. Badge Behavior

**Test Cases:**

- [ ] **Test 22: Badge Shows 0 Initially**
  - Action: Fresh session, no errors
  - Expected: Badge hidden or shows 0
  - Verify: No visual clutter

- [ ] **Test 23: Badge Increments**
  - Action: Generate 1 error
  - Expected: Badge shows "1"
  - Action: Generate 2 more errors
  - Expected: Badge shows "3"

- [ ] **Test 24: Badge Decrements on Dismiss**
  - Action: Badge shows "3", dismiss 1 error
  - Expected: Badge shows "2"
  - Verify: Real-time update

- [ ] **Test 25: Badge Clears on Open Modal**
  - Action: Badge shows "5", open modal
  - Expected: Badge immediately shows "0"
  - Reason: Errors marked as read

- [ ] **Test 26: Badge Real-Time Updates**
  - Action: Keep modal open, generate new error
  - Expected: Badge remains 0 (error already in view)
  - Close modal: Badge updates correctly

---

#### E. Internationalization (i18n)

**Test Cases:**

- [ ] **Test 27: English Button Label**
  - Language: English
  - Expected: Button shows "LOG"
  - Verify: All caps, matches other buttons

- [ ] **Test 28: French Button Label**
  - Action: Switch to French
  - Expected: Button shows "JOURNAL"
  - Verify: All caps, consistent style

- [ ] **Test 29: English Modal Texts**
  - Language: English
  - Expected:
    - Title: "Error Log"
    - Empty state: "No errors to display"
    - Clear All: "Clear All"
    - Close: "Close"

- [ ] **Test 30: French Modal Texts**
  - Language: French
  - Expected:
    - Title: "Journal des erreurs"
    - Empty state: "Aucune erreur à afficher"
    - Clear All: "Tout effacer"
    - Close: "Fermer"

- [ ] **Test 31: Error Messages Translate**
  - Action: Generate errors in both languages
  - Expected: Error text in correct language
  - Verify: Uses existing translation keys

- [ ] **Test 32: Toast Messages Translate**
  - Action: Trigger warnings in both languages
  - Expected: Toast text in correct language
  - Verify: Real-time language switching works

- [ ] **Test 33: Timestamp Locale**
  - Language: English
  - Expected: "11/2/2025, 2:30:45 PM" (US format)
  - Language: French
  - Expected: "02/11/2025 14:30:45" (FR format)

---

#### F. Accessibility

**Test Cases:**

- [ ] **Test 34: Keyboard Navigation to Button**
  - Action: Press Tab to navigate
  - Expected: LOG button receives focus
  - Visual: Focus ring visible

- [ ] **Test 35: Open Modal with Keyboard**
  - Action: Focus button, press Enter or Space
  - Expected: Modal opens
  - Focus: Moves into modal

- [ ] **Test 36: Navigate Within Modal**
  - Action: Press Tab inside modal
  - Expected: Focus cycles through:
    1. Clear All button
    2. Close (X) button
    3. Individual dismiss buttons
    4. Close button (footer)

- [ ] **Test 37: Dismiss Errors with Keyboard**
  - Action: Tab to dismiss button, press Enter
  - Expected: Error removed from list
  - Focus: Moves to next item

- [ ] **Test 38: Close Modal with Escape**
  - Action: Press Escape key
  - Expected: Modal closes
  - Focus: Returns to LOG button

- [ ] **Test 39: ARIA Labels**
  - Action: Inspect with screen reader
  - Expected: Buttons have aria-label
  - Verify: "close", "dismiss", etc.

- [ ] **Test 40: Screen Reader Announcements**
  - Tool: NVDA, JAWS, or VoiceOver
  - Expected: Toasts announced as "alert" role
  - Verify: Error log title read correctly

---

#### G. Edge Cases

**Test Cases:**

- [ ] **Test 41: Zero Errors (Empty State)**
  - Condition: No errors generated
  - Action: Open modal
  - Expected: Empty state with icon
  - Buttons: Only "Close" visible

- [ ] **Test 42: Single Error**
  - Condition: Exactly 1 error
  - Expected: Badge shows "1"
  - Modal: Shows 1 error item

- [ ] **Test 43: Many Errors (Scrolling)**
  - Condition: 10+ errors
  - Expected: Modal scrolls (max height 60vh)
  - Scrollbar: Visible, works correctly

- [ ] **Test 44: Max Errors (100+)**
  - Condition: Generate 150 errors
  - Expected: Only last 100 kept
  - Verify: No memory bloat

- [ ] **Test 45: Rapid Error Additions**
  - Action: Generate 10 errors in 1 second
  - Expected: All appear in log
  - Badge: Updates correctly
  - Performance: No lag

- [ ] **Test 46: Rapid Toast Triggers**
  - Action: Trigger 5 warnings quickly
  - Expected: All toasts stack properly
  - Verify: Auto-dismiss timers work independently

- [ ] **Test 47: Modal Open/Close Multiple Times**
  - Action: Open and close modal 10 times
  - Expected: No errors in console
  - State: Persists correctly

- [ ] **Test 48: Toast During Modal Open**
  - Action: Open modal, trigger warning
  - Expected: Toast appears above modal
  - Z-index: Toast (9999) > Modal

- [ ] **Test 49: Error During Toast Display**
  - Action: Toast visible, trigger error
  - Expected: Error goes to log
  - Badge: Increments (if unread)

- [ ] **Test 50: Network Error Handling**
  - Condition: Backend offline
  - Action: Trigger operations that call backend
  - Expected: Error notifications display
  - No: Browser alert() fallback

---

### 5.3 Component Unit Tests (Optional)

- [ ] **Task 5.3 Complete**

**Test Files to Create:**

1. **`useNotificationStore.test.ts`**
   - Test: `addError()` adds error to store
   - Test: `addWarning()` adds toast to store
   - Test: `dismissError()` removes error by ID
   - Test: `clearAllErrors()` empties error list
   - Test: `markAllErrorsAsRead()` sets read=true
   - Test: `getUnreadErrorCount()` returns correct count
   - Test: Max 100 errors enforced

2. **`ToastNotification.test.tsx`**
   - Test: Renders toast with correct message
   - Test: Auto-dismiss after duration
   - Test: Manual dismiss on click
   - Test: Multiple toasts stack correctly
   - Test: Correct severity styling

3. **`NotificationLogPopupView.test.tsx`**
   - Test: Renders error list correctly
   - Test: Empty state when no errors
   - Test: Dismiss individual error
   - Test: Clear all errors
   - Test: Timestamp formatted correctly
   - Test: Modal closes on button click

4. **`NotificationLogPopupContainer.test.tsx`**
   - Test: Connects to stores correctly
   - Test: Marks errors as read on open
   - Test: Translations applied
   - Test: Event handlers work

**Testing Framework:**

```bash
# Run tests
npm run test

# Run with coverage
npm run test:coverage

# Expected coverage (optional):
# - Stores: 80%+
# - Components: 70%+
```

---

## Test Execution Log

### Build Verification Results

**Date:** ******\_******
**Tester:** ******\_******

| Test             | Status            | Notes |
| ---------------- | ----------------- | ----- |
| Prettier format  | [ ] Pass [ ] Fail |       |
| ESLint           | [ ] Pass [ ] Fail |       |
| TypeScript build | [ ] Pass [ ] Fail |       |
| Vite build       | [ ] Pass [ ] Fail |       |

---

### Manual Test Results Summary

**Date:** ******\_******
**Tester:** ******\_******
**Browser:** ******\_******
**Language Tested:** [ ] EN [ ] FR [ ] Both

| Category                 | Tests Passed | Tests Failed | Notes |
| ------------------------ | ------------ | ------------ | ----- |
| Error Notifications (A)  | \_\_\_/12    |              |       |
| Warning Toasts (B)       | \_\_\_/7     |              |       |
| Info/Success (C)         | \_\_\_/2     |              |       |
| Badge Behavior (D)       | \_\_\_/5     |              |       |
| Internationalization (E) | \_\_\_/7     |              |       |
| Accessibility (F)        | \_\_\_/7     |              |       |
| Edge Cases (G)           | \_\_\_/10    |              |       |
| **TOTAL**                | \_\_\_/50    |              |       |

---

### Issues Found

**Issue 1:**

- **Test:** ******\_\_\_******
- **Severity:** [ ] Critical [ ] Major [ ] Minor
- **Description:** ******\_\_\_******
- **Steps to Reproduce:** ******\_\_\_******
- **Expected:** ******\_\_\_******
- **Actual:** ******\_\_\_******

**Issue 2:**

- **Test:** ******\_\_\_******
- **Severity:** [ ] Critical [ ] Major [ ] Minor
- **Description:** ******\_\_\_******
- **Steps to Reproduce:** ******\_\_\_******
- **Expected:** ******\_\_\_******
- **Actual:** ******\_\_\_******

- _(Add more as needed)_

---

## Sign-Off

### Testing Complete

- [ ] All build checks passed
- [ ] All critical tests passed (P0)
- [ ] All major tests passed or issues documented (P1)
- [ ] Minor issues documented (P2)
- [ ] Accessibility requirements met (WCAG 2.1 Level AA)
- [ ] Internationalization verified (EN + FR)
- [ ] Performance acceptable (no lag, no memory leaks)

**Tester Name:** ******\_\_\_******
**Date:** ******\_\_\_******
**Signature:** ******\_\_\_******

---

**Approval Required:** Yes
**Approved By:** ******\_\_\_******
**Date:** ******\_\_\_******

---

## Quick Reference

### Triggering Test Scenarios

**How to Generate Errors:**

1. **Auth Sign-In Required:**
   - Log out
   - Click CLASSIFY button

2. **Directory Not Selected:**
   - Ensure no directory selected
   - Try to perform inference

3. **Queue Full:**
   - Submit 11+ inference requests rapidly

4. **Inference Fetch Failed:**
   - Stop backend server
   - Trigger inference

5. **Storage Read Failed:**
   - Disconnect from Azure
   - Reload app

**How to Generate Warnings:**

1. **Auth In Progress:**
   - Trigger action during auth flow

2. **Validation Errors:**
   - Upload invalid image format
   - Enter invalid folder name

**How to Switch Languages:**

- UI: Language selector in header
- Browser: Change browser locale settings

---

## Notes for Testers

1. **Session Storage:** Error log clears on browser refresh (by design)
2. **Badge Count:** Should update in real-time as errors added/removed
3. **Toast Position:** Top-center (not bottom-right)
4. **Button Label:** "LOG" (English) / "JOURNAL" (French)
5. **Timestamp:** Actual date/time, not relative ("2 minutes ago")

**Known Limitations:**

- Toast max visible: ~3-5 (by design, they stack)
- Error log max: 100 items (older items auto-removed)
- No persistence across sessions (session-only storage)

---

**Testing Status:** Ready for Phase 5 Testing
**Last Updated:** 2025-11-02
