import { create } from "zustand";

interface Notification {
  id: string; // UUID
  type: "error" | "warning" | "info";
  message: string;
  timestamp: number;
  read: boolean;
  source?: string; // e.g., "inference", "auth", "storage"
}

interface Toast {
  id: string;
  type: "warning" | "info" | "success";
  message: string;
  duration: number; // 5000 or 10000 ms
}

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

// Generate UUID v4
const generateUUID = (): string => {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === "x" ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
};

export const useNotificationStore = create<NotificationState>()((set, get) => ({
  errors: [],
  toasts: [],

  addError: (message: string, source?: string) => {
    const newError: Notification = {
      id: generateUUID(),
      type: "error",
      message,
      timestamp: Date.now(),
      read: false,
      source,
    };

    set((state) => {
      // Keep only the last 100 errors to prevent memory bloat
      const updatedErrors = [...state.errors, newError];
      if (updatedErrors.length > 100) {
        updatedErrors.shift();
      }
      return { errors: updatedErrors };
    });
  },

  addWarning: (message: string, duration = 10000) => {
    const newToast: Toast = {
      id: generateUUID(),
      type: "warning",
      message,
      duration,
    };

    set((state) => ({
      toasts: [...state.toasts, newToast],
    }));
  },

  addInfo: (message: string, duration = 5000) => {
    const newToast: Toast = {
      id: generateUUID(),
      type: "info",
      message,
      duration,
    };

    set((state) => ({
      toasts: [...state.toasts, newToast],
    }));
  },

  addSuccess: (message: string, duration = 5000) => {
    const newToast: Toast = {
      id: generateUUID(),
      type: "success",
      message,
      duration,
    };

    set((state) => ({
      toasts: [...state.toasts, newToast],
    }));
  },

  dismissError: (id: string) => {
    set((state) => ({
      errors: state.errors.filter((error) => error.id !== id),
    }));
  },

  clearAllErrors: () => {
    set({ errors: [] });
  },

  markErrorAsRead: (id: string) => {
    set((state) => ({
      errors: state.errors.map((error) =>
        error.id === id ? { ...error, read: true } : error,
      ),
    }));
  },

  markAllErrorsAsRead: () => {
    set((state) => ({
      errors: state.errors.map((error) => ({ ...error, read: true })),
    }));
  },

  removeToast: (id: string) => {
    set((state) => ({
      toasts: state.toasts.filter((toast) => toast.id !== id),
    }));
  },

  getUnreadErrorCount: () => {
    return get().errors.filter((error) => !error.read).length;
  },

  hasUnreadErrors: () => {
    return get().errors.some((error) => !error.read);
  },
}));
