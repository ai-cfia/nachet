import { describe, it, expect, beforeEach } from "vitest";
import { act } from "@testing-library/react";
import { useNotificationStore } from "../useNotificationStore";

describe("useNotificationStore", () => {
  beforeEach(() => {
    // Reset store to initial state
    act(() => {
      useNotificationStore.setState({
        errors: [],
        toasts: [],
      });
    });
  });

  describe("Initial State", () => {
    it("should have empty errors and toasts arrays", () => {
      const { errors, toasts } = useNotificationStore.getState();
      expect(errors).toEqual([]);
      expect(toasts).toEqual([]);
    });
  });

  describe("addError", () => {
    it("should add error with generated UUID", () => {
      act(() => {
        useNotificationStore.getState().addError("Test error message");
      });

      const { errors } = useNotificationStore.getState();
      expect(errors).toHaveLength(1);
      expect(errors[0].message).toBe("Test error message");
      expect(errors[0].type).toBe("error");
      expect(errors[0].read).toBe(false);
      expect(errors[0].id).toMatch(
        /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
      );
    });

    it("should add error with source", () => {
      act(() => {
        useNotificationStore.getState().addError("Error message", "inference");
      });

      const { errors } = useNotificationStore.getState();
      expect(errors[0].source).toBe("inference");
    });

    it("should add error without source", () => {
      act(() => {
        useNotificationStore.getState().addError("Error message");
      });

      const { errors } = useNotificationStore.getState();
      expect(errors[0].source).toBeUndefined();
    });

    it("should include timestamp", () => {
      const beforeTime = Date.now();

      act(() => {
        useNotificationStore.getState().addError("Error message");
      });

      const afterTime = Date.now();
      const { errors } = useNotificationStore.getState();

      expect(errors[0].timestamp).toBeGreaterThanOrEqual(beforeTime);
      expect(errors[0].timestamp).toBeLessThanOrEqual(afterTime);
    });

    it("should limit errors to 100 entries", () => {
      act(() => {
        // Add 105 errors
        for (let i = 0; i < 105; i++) {
          useNotificationStore.getState().addError(`Error ${i}`);
        }
      });

      const { errors } = useNotificationStore.getState();
      expect(errors).toHaveLength(100);
      // Should keep most recent 100 (removed first 5)
      expect(errors[0].message).toBe("Error 5");
      expect(errors[99].message).toBe("Error 104");
    });

    it("should generate unique IDs for each error", () => {
      act(() => {
        useNotificationStore.getState().addError("Error 1");
        useNotificationStore.getState().addError("Error 2");
        useNotificationStore.getState().addError("Error 3");
      });

      const { errors } = useNotificationStore.getState();
      const ids = errors.map((e) => e.id);
      const uniqueIds = new Set(ids);

      expect(uniqueIds.size).toBe(3);
    });
  });

  describe("Toast Creation", () => {
    it("should add warning toast with default 10s duration", () => {
      act(() => {
        useNotificationStore.getState().addWarning("Warning message");
      });

      const { toasts } = useNotificationStore.getState();
      expect(toasts).toHaveLength(1);
      expect(toasts[0].type).toBe("warning");
      expect(toasts[0].message).toBe("Warning message");
      expect(toasts[0].duration).toBe(10000);
      expect(toasts[0].id).toMatch(/^[0-9a-f-]+$/i);
    });

    it("should add warning toast with custom duration", () => {
      act(() => {
        useNotificationStore.getState().addWarning("Warning message", 5000);
      });

      const { toasts } = useNotificationStore.getState();
      expect(toasts[0].duration).toBe(5000);
    });

    it("should add info toast with default 5s duration", () => {
      act(() => {
        useNotificationStore.getState().addInfo("Info message");
      });

      const { toasts } = useNotificationStore.getState();
      expect(toasts[0].type).toBe("info");
      expect(toasts[0].message).toBe("Info message");
      expect(toasts[0].duration).toBe(5000);
    });

    it("should add info toast with custom duration", () => {
      act(() => {
        useNotificationStore.getState().addInfo("Info message", 3000);
      });

      const { toasts } = useNotificationStore.getState();
      expect(toasts[0].duration).toBe(3000);
    });

    it("should add success toast with default 5s duration", () => {
      act(() => {
        useNotificationStore.getState().addSuccess("Success message");
      });

      const { toasts } = useNotificationStore.getState();
      expect(toasts[0].type).toBe("success");
      expect(toasts[0].message).toBe("Success message");
      expect(toasts[0].duration).toBe(5000);
    });

    it("should add success toast with custom duration", () => {
      act(() => {
        useNotificationStore.getState().addSuccess("Success message", 7000);
      });

      const { toasts } = useNotificationStore.getState();
      expect(toasts[0].duration).toBe(7000);
    });

    it("should allow multiple toasts", () => {
      act(() => {
        useNotificationStore.getState().addWarning("Warning");
        useNotificationStore.getState().addInfo("Info");
        useNotificationStore.getState().addSuccess("Success");
      });

      const { toasts } = useNotificationStore.getState();
      expect(toasts).toHaveLength(3);
      expect(toasts.map((t) => t.type)).toEqual(["warning", "info", "success"]);
    });
  });

  describe("Error Management", () => {
    beforeEach(() => {
      act(() => {
        useNotificationStore.getState().addError("Error 1", "source1");
        useNotificationStore.getState().addError("Error 2", "source2");
        useNotificationStore.getState().addError("Error 3", "source3");
      });
    });

    it("should dismiss error by ID", () => {
      const { errors } = useNotificationStore.getState();
      const targetId = errors[1].id;

      act(() => {
        useNotificationStore.getState().dismissError(targetId);
      });

      const updatedErrors = useNotificationStore.getState().errors;
      expect(updatedErrors).toHaveLength(2);
      expect(updatedErrors.find((e) => e.id === targetId)).toBeUndefined();
    });

    it("should handle dismissing non-existent error", () => {
      act(() => {
        useNotificationStore.getState().dismissError("non-existent-id");
      });

      expect(useNotificationStore.getState().errors).toHaveLength(3);
    });

    it("should clear all errors", () => {
      act(() => {
        useNotificationStore.getState().clearAllErrors();
      });

      expect(useNotificationStore.getState().errors).toEqual([]);
    });

    it("should mark error as read", () => {
      const { errors } = useNotificationStore.getState();
      const targetId = errors[0].id;

      expect(errors[0].read).toBe(false);

      act(() => {
        useNotificationStore.getState().markErrorAsRead(targetId);
      });

      const updatedError = useNotificationStore
        .getState()
        .errors.find((e) => e.id === targetId);
      expect(updatedError?.read).toBe(true);
    });

    it("should mark all errors as read", () => {
      act(() => {
        useNotificationStore.getState().markAllErrorsAsRead();
      });

      const { errors } = useNotificationStore.getState();
      expect(errors.every((e) => e.read)).toBe(true);
    });

    it("should not affect other errors when marking one as read", () => {
      const { errors } = useNotificationStore.getState();
      const targetId = errors[1].id;

      act(() => {
        useNotificationStore.getState().markErrorAsRead(targetId);
      });

      const updatedErrors = useNotificationStore.getState().errors;
      expect(updatedErrors[0].read).toBe(false);
      expect(updatedErrors[1].read).toBe(true);
      expect(updatedErrors[2].read).toBe(false);
    });
  });

  describe("Toast Management", () => {
    it("should remove toast by ID", () => {
      act(() => {
        useNotificationStore.getState().addWarning("Toast 1");
        useNotificationStore.getState().addInfo("Toast 2");
        useNotificationStore.getState().addSuccess("Toast 3");
      });

      const { toasts } = useNotificationStore.getState();
      const targetId = toasts[1].id;

      act(() => {
        useNotificationStore.getState().removeToast(targetId);
      });

      const updatedToasts = useNotificationStore.getState().toasts;
      expect(updatedToasts).toHaveLength(2);
      expect(updatedToasts.find((t) => t.id === targetId)).toBeUndefined();
    });

    it("should handle removing non-existent toast", () => {
      act(() => {
        useNotificationStore.getState().addWarning("Toast");
      });

      act(() => {
        useNotificationStore.getState().removeToast("non-existent-id");
      });

      expect(useNotificationStore.getState().toasts).toHaveLength(1);
    });
  });

  describe("Query Methods", () => {
    it("should get unread error count", () => {
      act(() => {
        useNotificationStore.getState().addError("Error 1");
        useNotificationStore.getState().addError("Error 2");
        useNotificationStore.getState().addError("Error 3");
      });

      expect(useNotificationStore.getState().getUnreadErrorCount()).toBe(3);

      const { errors } = useNotificationStore.getState();
      act(() => {
        useNotificationStore.getState().markErrorAsRead(errors[0].id);
      });

      expect(useNotificationStore.getState().getUnreadErrorCount()).toBe(2);
    });

    it("should return 0 for unread count when no errors", () => {
      expect(useNotificationStore.getState().getUnreadErrorCount()).toBe(0);
    });

    it("should check if has unread errors", () => {
      expect(useNotificationStore.getState().hasUnreadErrors()).toBe(false);

      act(() => {
        useNotificationStore.getState().addError("Error");
      });

      expect(useNotificationStore.getState().hasUnreadErrors()).toBe(true);

      act(() => {
        useNotificationStore.getState().markAllErrorsAsRead();
      });

      expect(useNotificationStore.getState().hasUnreadErrors()).toBe(false);
    });
  });

  describe("Edge Cases", () => {
    it("should handle marking non-existent error as read", () => {
      act(() => {
        useNotificationStore.getState().addError("Error");
      });

      act(() => {
        useNotificationStore.getState().markErrorAsRead("non-existent");
      });

      // Should not throw and error count should remain
      expect(useNotificationStore.getState().errors).toHaveLength(1);
    });

    it("should handle UUID generation edge cases", () => {
      // Generate multiple UUIDs and verify they're valid v4 UUIDs
      const ids: string[] = [];

      act(() => {
        for (let i = 0; i < 10; i++) {
          useNotificationStore.getState().addError(`Error ${i}`);
        }
      });

      const { errors } = useNotificationStore.getState();
      errors.forEach((error) => {
        expect(error.id).toMatch(
          /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
        );
        ids.push(error.id);
      });

      // All IDs should be unique
      expect(new Set(ids).size).toBe(10);
    });

    it("should handle concurrent error additions", () => {
      act(() => {
        for (let i = 0; i < 50; i++) {
          useNotificationStore.getState().addError(`Error ${i}`);
        }
      });

      const { errors } = useNotificationStore.getState();
      expect(errors).toHaveLength(50);
      expect(errors[0].message).toBe("Error 0");
      expect(errors[49].message).toBe("Error 49");
    });
  });
});
