import { describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import useBackendUrl from "../useBackendUrl";

describe("useBackendUrl", () => {
  const OLD_ENV = process.env;

  beforeEach(() => {
    vi.resetModules(); // Most important - it clears the cache
    process.env = { ...OLD_ENV }; // Make a copy
  });

  afterAll(() => {
    process.env = OLD_ENV; // Restore old environment
  });

  it("should return the backend url", async () => {
    process.env.VITE_BACKEND_URL = "http://localhost:9000";
    const { result } = renderHook(() => useBackendUrl());
    await waitFor(() => {
      expect(result.current).toBe("http://localhost:9000");
    });
  });

  it("it should return an empty string if the backend url is not set", async () => {
    const consoleError = console.error;
    console.error = vi.fn();
    process.env.VITE_BACKEND_URL = "";
    const { result } = renderHook(() => useBackendUrl());
    await waitFor(() => {
      expect(result.current).toBe("");
      expect(console.error).toHaveBeenCalled();
    });
    console.error = consoleError;
  });

  it("it should have console.error if the backend url is not set", async () => {
    const consoleError = console.error;
    console.error = vi.fn();
    process.env.VITE_BACKEND_URL = "";
    renderHook(() => useBackendUrl());
    await waitFor(() => {
      expect(console.error).toHaveBeenCalled();
    });
    console.error = consoleError;
  });
});
