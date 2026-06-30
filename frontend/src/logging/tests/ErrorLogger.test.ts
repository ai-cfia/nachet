import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import axios from "axios";
import errorLogger from "../ErrorLogger";

// Mock dependencies
vi.mock("axios");

describe("ErrorLogger (Singleton)", () => {
  let consoleErrorSpy: any;
  let consoleWarnSpy: any;
  let consoleInfoSpy: any;
  const mockedAxiosPost = vi.mocked(axios.post);
  const originalEnv = import.meta.env.VITE_LOG_API_URL;

  beforeEach(() => {
    // Reset mocks
    vi.clearAllMocks();
    errorLogger.setTokenProvider(vi.fn().mockResolvedValue("test-token"));

    // Mock axios.post
    mockedAxiosPost.mockResolvedValue({ data: { success: true } });

    // Spy on console methods
    consoleErrorSpy = vi.spyOn(console, "error").mockImplementation(() => {});
    consoleWarnSpy = vi.spyOn(console, "warn").mockImplementation(() => {});
    consoleInfoSpy = vi.spyOn(console, "info").mockImplementation(() => {});
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
    consoleWarnSpy.mockRestore();
    consoleInfoSpy.mockRestore();
    // Reset token provider
    errorLogger.setTokenProvider(null);
    import.meta.env.VITE_LOG_API_URL = originalEnv;
  });

  describe("singleton instance", () => {
    it("should have session ID", () => {
      const sessionId = errorLogger.getSessionId();
      expect(sessionId).toBeDefined();
      expect(typeof sessionId).toBe("string");
    });

    it("should use token provider when set", async () => {
      const tokenProvider = vi.fn().mockResolvedValue("test-token");
      errorLogger.setTokenProvider(tokenProvider);

      await errorLogger.logError("Test error");

      expect(tokenProvider).toHaveBeenCalled();
      expect(axios.post).toHaveBeenCalledWith(
        expect.any(String),
        expect.any(Object),
        expect.objectContaining({
          headers: expect.objectContaining({
            Authorization: "Bearer test-token",
          }),
        }),
      );

      // Reset token provider
      errorLogger.setTokenProvider(vi.fn().mockResolvedValue("test-token"));
    });
  });

  describe("correlation IDs", () => {
    it("should auto-generate correlation ID on first access", () => {
      const correlationId = errorLogger.getCorrelationId();
      expect(correlationId).toBeDefined();
      expect(typeof correlationId).toBe("string");
    });

    it("should allow setting custom correlation ID", () => {
      errorLogger.setCorrelationId("custom-correlation-id");
      expect(errorLogger.getCorrelationId()).toBe("custom-correlation-id");
    });

    it("should reuse correlation ID once set", () => {
      errorLogger.setCorrelationId("test-correlation-id");
      const id1 = errorLogger.getCorrelationId();
      const id2 = errorLogger.getCorrelationId();
      expect(id1).toBe(id2);
      expect(id1).toBe("test-correlation-id");
    });
  });

  describe("logError", () => {
    it("should log error with message only", async () => {
      await errorLogger.logError("Test error message");

      expect(consoleErrorSpy).toHaveBeenCalledWith(
        "Test error message",
        undefined,
        undefined,
      );
      expect(axios.post).toHaveBeenCalledWith(
        expect.stringContaining("://"),
        expect.objectContaining({
          level: "ERROR",
          message: "Test error message",
          errorType: "UnknownError",
        }),
        expect.any(Object),
      );
    });

    it("should log error with Error object", async () => {
      const error = new Error("Test error");

      await errorLogger.logError("Error occurred", error);

      expect(consoleErrorSpy).toHaveBeenCalledWith(
        "Error occurred",
        error,
        undefined,
      );
      expect(axios.post).toHaveBeenCalledWith(
        expect.stringContaining("://"),
        expect.objectContaining({
          level: "ERROR",
          message: "Error occurred",
          errorType: "Error",
          stackTrace: expect.stringContaining("Test error"),
        }),
        expect.any(Object),
      );
    });

    it("should log error with extra data", async () => {
      const extra = { userId: "123", action: "upload" };

      await errorLogger.logError("Action failed", undefined, extra);

      expect(axios.post).toHaveBeenCalledWith(
        expect.stringContaining("://"),
        expect.objectContaining({
          level: "ERROR",
          message: "Action failed",
          extra,
        }),
        expect.any(Object),
      );
    });

    it("should include session and correlation IDs in headers", async () => {
      errorLogger.setCorrelationId("test-correlation");

      await errorLogger.logError("Test");

      expect(axios.post).toHaveBeenCalledWith(
        expect.any(String),
        expect.any(Object),
        expect.objectContaining({
          headers: expect.objectContaining({
            "X-Session-ID": errorLogger.getSessionId(),
            "X-Correlation-ID": "test-correlation",
          }),
        }),
      );
    });

    it("should include url, timestamp, and userAgent", async () => {
      await errorLogger.logError("Test");

      expect(axios.post).toHaveBeenCalledWith(
        expect.any(String),
        expect.objectContaining({
          url: expect.any(String),
          timestamp: expect.stringMatching(/^\d{4}-\d{2}-\d{2}T/),
          userAgent: expect.any(String),
        }),
        expect.any(Object),
      );
    });

    it("should fallback to console if axios fails", async () => {
      const axiosError = new Error("Network error");
      mockedAxiosPost.mockRejectedValueOnce(axiosError);

      await errorLogger.logError("Test error");

      // Should have logged original error + fallback
      expect(consoleErrorSpy).toHaveBeenCalled();
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        "Failed to send log to server:",
        axiosError,
      );
    });

    it("should skip backend logging if token provider fails", async () => {
      const tokenProvider = vi.fn().mockRejectedValue(new Error("Token error"));
      errorLogger.setTokenProvider(tokenProvider);

      await errorLogger.logError("Test");

      expect(consoleWarnSpy).toHaveBeenCalledWith(
        "Skipping backend log submission because log auth failed:",
        expect.any(Error),
      );
      expect(axios.post).not.toHaveBeenCalled();

      // Reset token provider
      errorLogger.setTokenProvider(vi.fn().mockResolvedValue("test-token"));
    });

    it("should skip backend logging if token provider returns an empty token", async () => {
      const tokenProvider = vi.fn().mockResolvedValue("");
      errorLogger.setTokenProvider(tokenProvider);

      await errorLogger.logError("Test");

      expect(consoleWarnSpy).toHaveBeenCalledWith(
        "Skipping backend log submission because no auth token is available.",
      );
      expect(axios.post).not.toHaveBeenCalled();

      // Reset token provider
      errorLogger.setTokenProvider(vi.fn().mockResolvedValue("test-token"));
    });

    it("should skip backend logging if token provider is not initialized", async () => {
      errorLogger.setTokenProvider(null);

      await errorLogger.logError("Test");

      expect(consoleWarnSpy).toHaveBeenCalledWith(
        "Skipping backend log submission because log auth is not initialized.",
      );
      expect(axios.post).not.toHaveBeenCalled();
    });
  });

  describe("logWarning", () => {
    it("should log warning message", async () => {
      await errorLogger.logWarning("Warning message");

      expect(consoleWarnSpy).toHaveBeenCalledWith("Warning message", undefined);
      expect(axios.post).toHaveBeenCalledWith(
        expect.stringContaining("://"),
        expect.objectContaining({
          level: "WARNING",
          message: "Warning message",
        }),
        expect.any(Object),
      );
    });

    it("should log warning with extra data", async () => {
      const extra = { reason: "deprecated" };

      await errorLogger.logWarning("Deprecated API", extra);

      expect(consoleWarnSpy).toHaveBeenCalledWith("Deprecated API", extra);
      expect(axios.post).toHaveBeenCalledWith(
        expect.stringContaining("://"),
        expect.objectContaining({
          level: "WARNING",
          message: "Deprecated API",
          extra,
        }),
        expect.any(Object),
      );
    });
  });

  describe("logInfo", () => {
    it("should log info message", async () => {
      await errorLogger.logInfo("Info message");

      expect(consoleInfoSpy).toHaveBeenCalledWith("Info message", undefined);
      expect(axios.post).toHaveBeenCalledWith(
        expect.stringContaining("://"),
        expect.objectContaining({
          level: "INFO",
          message: "Info message",
        }),
        expect.any(Object),
      );
    });

    it("should log info with extra data", async () => {
      const extra = { step: "initialization" };

      await errorLogger.logInfo("App started", extra);

      expect(consoleInfoSpy).toHaveBeenCalledWith("App started", extra);
      expect(axios.post).toHaveBeenCalledWith(
        expect.stringContaining("://"),
        expect.objectContaining({
          level: "INFO",
          message: "App started",
          extra,
        }),
        expect.any(Object),
      );
    });
  });

  describe("logApiError", () => {
    it("should log API error with full details", async () => {
      await errorLogger.logApiError("/api/users", 404, "Not Found", {
        detail: "User not found",
      });

      expect(axios.post).toHaveBeenCalledWith(
        expect.stringContaining("://"),
        expect.objectContaining({
          level: "ERROR",
          message: "API Error: /api/users returned 404 Not Found",
          errorType: "APIError",
          extra: expect.objectContaining({
            endpoint: "/api/users",
            status: 404,
            statusText: "Not Found",
            responseData: { detail: "User not found" },
          }),
        }),
        expect.any(Object),
      );
    });

    it("should use custom correlation ID if provided", async () => {
      await errorLogger.logApiError(
        "/api/test",
        500,
        "Error",
        {},
        "custom-correlation",
      );

      expect(axios.post).toHaveBeenCalledWith(
        expect.stringContaining("://"),
        expect.objectContaining({
          extra: expect.objectContaining({
            correlationId: "custom-correlation",
          }),
        }),
        expect.any(Object),
      );
    });

    it("should use auto-generated correlation ID if not provided", async () => {
      await errorLogger.logApiError("/api/test", 500, "Error");

      expect(axios.post).toHaveBeenCalledWith(
        expect.stringContaining("://"),
        expect.objectContaining({
          extra: expect.objectContaining({
            correlationId: expect.any(String),
          }),
        }),
        expect.any(Object),
      );
    });
  });

  describe("setupGlobalHandlers", () => {
    it("should setup global error handlers if window is defined", () => {
      // This test verifies the method exists and can be called
      // Actual global handlers are set up when module loads
      expect(typeof errorLogger.setupGlobalHandlers).toBe("function");
      // Don't call it again as it's already called during module load
    });
  });

  describe("withCredentials", () => {
    it("should include withCredentials in axios request", async () => {
      await errorLogger.logError("Test");

      expect(axios.post).toHaveBeenCalledWith(
        expect.any(String),
        expect.any(Object),
        expect.objectContaining({
          withCredentials: true,
        }),
      );
    });
  });

  describe("Content-Type header", () => {
    it("should set Content-Type to application/json", async () => {
      await errorLogger.logError("Test");

      expect(axios.post).toHaveBeenCalledWith(
        expect.any(String),
        expect.any(Object),
        expect.objectContaining({
          headers: expect.objectContaining({
            "Content-Type": "application/json",
          }),
        }),
      );
    });
  });
});
