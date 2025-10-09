# Error Boundary Documentation

## Overview

The `ErrorBoundary` component is a React class component that catches JavaScript errors anywhere in the child component tree, logs those errors, and displays a fallback UI instead of crashing the entire application.

**Location**: `frontend/src/components/body/error_boundary/ErrorBoundary.tsx`

## Why Class Component in a Functional Codebase?

### React Limitation

**Error Boundaries MUST be class components.** This is a React architectural limitation, not a design choice.

From the React documentation:
> Error boundaries are React components that catch JavaScript errors anywhere in their child component tree. There is currently no way to write an error boundary as a functional component with hooks.

The required lifecycle methods are **only available in class components**:

- `static getDerivedStateFromError(error)` - Updates state to render fallback UI
- `componentDidCatch(error, errorInfo)` - Logs error information

### The One Accepted Exception

In a fully functional pattern-based React application, the ErrorBoundary is the **one legitimate exception** where a class component is required and accepted. This is a well-known pattern in the React ecosystem.

## Current Implementation

### ✅ What's Working Well

1. **Proper Lifecycle Methods**
   - Correctly implements `getDerivedStateFromError` (lines 26-32)
   - Correctly implements `componentDidCatch` (lines 34-46)

2. **Centralized Logging Integration**
   - Integrates with the `errorLogger` service
   - Logs errors with context (component stack, correlation ID)
   - Sends error data to backend `/api/logs` endpoint

3. **Correlation ID Tracking**
   - Includes correlation ID in error metadata (line 39)
   - Displays correlation ID to users for support requests (line 126)
   - Good for debugging across distributed frontend/backend systems

4. **User-Friendly Fallback UI**
   - Clear error message with Material-UI components
   - Professional design with Paper elevation and proper spacing
   - Action buttons: "Try Again" and "Go to Home"

5. **Development Mode Debugging**
   - Shows full error stack trace only when `NODE_ENV === "development"`
   - Hides technical details from production users

6. **Flexible API**
   - Accepts custom `fallback` prop for different UI contexts
   - Children passthrough when no error

7. **Proper App Integration**
   - Used at root level in `main.tsx:78` to catch all React errors
   - Wraps the entire `<App>` component

### Error Handling Flow

```text
User Action
    ↓
React Component Error
    ↓
getDerivedStateFromError() - Set hasError state
    ↓
componentDidCatch() - Log to errorLogger
    ↓
errorLogger.logError() - Send to backend
    ↓
Backend /api/logs - Store with correlation ID
    ↓
Render Fallback UI - Show user-friendly message
```

## Architecture & Integration

### ErrorLogger Integration

The ErrorBoundary uses the singleton `errorLogger` instance from `src/logging/ErrorLogger.ts`:

```typescript
errorLogger.logError("React Error Boundary caught an error", error, {
  componentStack: errorInfo.componentStack,
  errorBoundary: true,
  correlationId: errorLogger.getCorrelationId(),
});
```

**Key Points:**

- ErrorLogger maintains a single `correlationId` per session
- `getCorrelationId()` generates a new ID only if one doesn't exist
- Same correlation ID is used across multiple errors in a session
- Session ID and correlation ID are sent to backend in headers

### Props Interface

```typescript
interface Props {
  children: ReactNode;       // Components to wrap and protect
  fallback?: ReactNode;      // Optional custom fallback UI
}
```

### State Interface

```typescript
interface State {
  hasError: boolean;         // Whether an error occurred
  error: Error | null;       // The error object
  errorInfo: ErrorInfo | null; // React error info with component stack
}
```

## Known Limitations & Recommendations

### 1. Reset Mechanism Doesn't Remount Children ⚠️

**Issue**: The `handleReset()` method (lines 48-56) only resets the ErrorBoundary's state but doesn't remount the child components.

**Impact**: If the error persists in the component state, clicking "Try Again" will immediately trigger the same error again.

**Recommendation**: Implement key-based reset to force remount:

```typescript
interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  resetKey: number;  // Add this
}

handleReset = (): void => {
  this.setState({
    hasError: false,
    error: null,
    errorInfo: null,
    resetKey: this.state.resetKey + 1,  // Increment to force remount
  });
};

render(): ReactNode {
  if (this.state.hasError) {
    // ... fallback UI
  }

  // Key forces remount when changed
  return <div key={this.state.resetKey}>{this.props.children}</div>;
}
```

**Alternative**: Navigate away before resetting:

```typescript
handleReset = (): void => {
  window.location.href = "/";  // Navigate to reset state
};
```

### 2. Correlation ID Display Accuracy ⚠️

**Issue**: Line 126 displays `errorLogger.getCorrelationId()` which might not be the exact ID that was logged with this specific error.

**Why**: The ErrorLogger is a singleton with a single `correlationId` property that persists across the session. If multiple errors occur, they all share the same correlation ID.

**Current Behavior**:

- First error: `getCorrelationId()` generates new ID → logged with that ID → displayed correctly ✅
- Subsequent errors: Reuses existing ID → logged with same ID → displayed correctly ✅
- After API call that sets a different correlation ID: Might show different ID than what was logged ❌

**Recommendation**: Store the correlation ID in component state when error occurs:

```typescript
interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
  errorCorrelationId: string | null;  // Add this
}

componentDidCatch(error: Error, errorInfo: ErrorInfo): void {
  const correlationId = errorLogger.getCorrelationId();

  errorLogger.logError("React Error Boundary caught an error", error, {
    componentStack: errorInfo.componentStack,
    errorBoundary: true,
    correlationId,
  });

  this.setState({
    error,
    errorInfo,
    errorCorrelationId: correlationId,  // Store it
  });
}

// In render():
<Typography variant="caption" color="textSecondary" mt={2} display="block">
  Error ID: {this.state.errorCorrelationId}
</Typography>
```

### 3. Missing Test Coverage ⚠️

**Issue**: No test file found for ErrorBoundary component.

**Recommendation**: Create `ErrorBoundary.test.tsx` with the following test cases:

- Renders children when no error occurs
- Catches errors and displays fallback UI
- Logs errors to errorLogger service
- Shows error details only in development mode
- Reset functionality clears error state
- "Go to Home" button navigates correctly
- Custom fallback prop works correctly
- Includes correlation ID in error metadata

See "Testing Recommendations" section below for implementation details.

## Best Practices

### 1. Placement in Component Tree

**Root Level** (Current implementation ✅):

```typescript
// main.tsx
<ErrorBoundary>
  <App />
</ErrorBoundary>
```

This catches all React errors in the application.

**Component Level** (Optional for granular control):

```typescript
// Complex feature component
<ErrorBoundary fallback={<FeatureFallback />}>
  <ComplexFeatureComponent />
</ErrorBoundary>
```

This allows specific features to fail without crashing the entire app.

### 2. Custom Fallback UI

For specific contexts, provide custom fallback:

```typescript
<ErrorBoundary fallback={
  <Alert severity="error">
    Unable to load dashboard. Please refresh the page.
  </Alert>
}>
  <Dashboard />
</ErrorBoundary>
```

### 3. Error Recovery Strategies

**Navigation-based recovery**:

```typescript
<Button onClick={() => window.location.href = '/'}>
  Return to Home
</Button>
```

**Reload-based recovery**:

```typescript
<Button onClick={() => window.location.reload()}>
  Reload Page
</Button>
```

## What Error Boundaries Do NOT Catch

Error boundaries **do not** catch errors in:

1. **Event handlers** - Use try-catch blocks

   ```typescript
   const handleClick = async () => {
     try {
       await riskyOperation();
     } catch (error) {
       errorLogger.logError('Button click failed', error);
     }
   };
   ```

2. **Asynchronous code** - Use promise `.catch()` or try-catch with async/await

   ```typescript
   useEffect(() => {
     fetchData().catch(error => {
       errorLogger.logError('Data fetch failed', error);
     });
   }, []);
   ```

3. **Server-side rendering** - N/A for this SPA application

4. **Errors in the error boundary itself** - Use parent error boundary

## Testing Recommendations

### Test File Structure

Create `frontend/src/components/body/error_boundary/ErrorBoundary.test.tsx`:

```typescript
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import ErrorBoundary from './ErrorBoundary';
import { errorLogger } from '../../../logging';

// Mock errorLogger
vi.mock('../../../logging', () => ({
  errorLogger: {
    logError: vi.fn(),
    getCorrelationId: vi.fn(() => 'test-correlation-id'),
  },
}));

// Component that throws error
const ThrowError = ({ shouldThrow }: { shouldThrow: boolean }) => {
  if (shouldThrow) {
    throw new Error('Test error');
  }
  return <div>No error</div>;
};

describe('ErrorBoundary', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Suppress console.error in tests
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  it('renders children when no error occurs', () => {
    render(
      <ErrorBoundary>
        <div>Child content</div>
      </ErrorBoundary>
    );

    expect(screen.getByText('Child content')).toBeInTheDocument();
  });

  it('catches errors and displays fallback UI', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
    expect(screen.getByText(/An unexpected error has occurred/)).toBeInTheDocument();
  });

  it('logs errors to errorLogger service', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(errorLogger.logError).toHaveBeenCalledWith(
      'React Error Boundary caught an error',
      expect.any(Error),
      expect.objectContaining({
        componentStack: expect.any(String),
        errorBoundary: true,
        correlationId: 'test-correlation-id',
      })
    );
  });

  it('shows error details only in development mode', () => {
    const originalEnv = process.env.NODE_ENV;
    process.env.NODE_ENV = 'development';

    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText(/Error Details \(Development Only\)/)).toBeInTheDocument();

    process.env.NODE_ENV = originalEnv;
  });

  it('reset functionality clears error state', () => {
    const { rerender } = render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText('Something went wrong')).toBeInTheDocument();

    const tryAgainButton = screen.getByText('Try Again');
    fireEvent.click(tryAgainButton);

    // Note: This test will fail with current implementation due to
    // the reset limitation mentioned above
  });

  it('renders custom fallback when provided', () => {
    render(
      <ErrorBoundary fallback={<div>Custom error message</div>}>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText('Custom error message')).toBeInTheDocument();
    expect(screen.queryByText('Something went wrong')).not.toBeInTheDocument();
  });

  it('displays correlation ID for support', () => {
    render(
      <ErrorBoundary>
        <ThrowError shouldThrow={true} />
      </ErrorBoundary>
    );

    expect(screen.getByText(/Error ID: test-correlation-id/)).toBeInTheDocument();
  });
});
```

### Running Tests

```bash
cd frontend
npm run test ErrorBoundary.test.tsx
```

## Optional Improvements

### Priority: Medium

1. **Implement Key-Based Reset** (see Limitation #1 above)
   - Ensures clean component remount
   - Prevents recurring errors on reset
   - Estimated effort: 30 minutes

2. **Store Correlation ID in State** (see Limitation #2 above)
   - Guarantees displayed ID matches logged ID
   - Better for user support scenarios
   - Estimated effort: 15 minutes

3. **Add Test Coverage**
   - Ensures component reliability
   - Prevents regressions
   - Estimated effort: 2 hours

### Priority: Low

4. **Add Error Reporting Button**

   ```typescript
   <Button onClick={() => window.open(`mailto:support@cfia.ca?subject=Error Report ${correlationId}`)}>
     Report Issue
   </Button>
   ```

5. **Add Retry Counter**
   - Track number of reset attempts
   - Auto-navigate to home after 3 failed resets

6. **Enhanced Error Context**
   - Capture user ID if authenticated
   - Capture current route/page
   - Capture recent user actions

## Related Documentation

- [Test Logging Pipeline](./test_logging_pipeline.md) - How to test the logging system
- [ErrorLogger Service](../src/logging/ErrorLogger.ts) - Centralized error logging
- [React Error Boundaries (Official Docs)](https://react.dev/reference/react/Component#catching-rendering-errors-with-an-error-boundary)

## References

- Implementation: `frontend/src/components/body/error_boundary/ErrorBoundary.tsx`
- Usage: `frontend/src/main.tsx:78`
- Logger: `frontend/src/logging/ErrorLogger.ts`
- Backend endpoint: `backend/app/main.py` `/api/logs` route

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2025-10-09 | Initial documentation created | Claude Code |

---

**Note**: This is a living document. Update it when making changes to the ErrorBoundary implementation or discovering new patterns.
