import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useModelMetadata } from "../useModelMetadata";
import { useModelStore } from "@stores/useModelStore";
import { fetchModelMetadata } from "@common";

// Mock dependencies
vi.mock("@stores/useModelStore");
vi.mock("@common");

describe("useModelMetadata", () => {
  let mockSetMetadata: any;
  let mockSetSelectedModel: any;
  let mockSetLoading: any;
  const mockMetadata = [
    { pipelineId: "pipeline-1", name: "Model 1", default: false },
    { pipelineId: "pipeline-2", name: "Model 2", default: true },
    { pipelineId: "pipeline-3", name: "Model 3", default: false },
  ];

  beforeEach(() => {
    vi.clearAllMocks();

    mockSetMetadata = vi.fn();
    mockSetSelectedModel = vi.fn();
    mockSetLoading = vi.fn();

    // Mock the store
    (useModelStore as any).mockReturnValue({
      metadata: null,
      selectedModel: null,
      setMetadata: mockSetMetadata,
      setSelectedModel: mockSetSelectedModel,
      setLoading: mockSetLoading,
    });

    // Mock fetchModelMetadata
    (fetchModelMetadata as any).mockResolvedValue(mockMetadata);

    // Mock console methods
    vi.spyOn(console, "error").mockImplementation(() => {});
    vi.spyOn(window, "alert").mockImplementation(() => {});
  });

  it("should fetch and set model metadata when authenticated", async () => {
    renderHook(() =>
      useModelMetadata({
        backendUrl: "http://test-backend.com",
        isAuthenticated: true,
        authLoading: false,
      }),
    );

    await waitFor(() => {
      expect(mockSetLoading).toHaveBeenCalledWith(true);
    });

    await waitFor(() => {
      expect(fetchModelMetadata).toHaveBeenCalledWith({
        backendUrl: "http://test-backend.com",
      });
    });

    await waitFor(() => {
      expect(mockSetMetadata).toHaveBeenCalledWith(mockMetadata);
    });

    await waitFor(() => {
      expect(mockSetSelectedModel).toHaveBeenCalledWith("pipeline-2");
    });

    await waitFor(() => {
      expect(mockSetLoading).toHaveBeenCalledWith(false);
    });
  });

  it("should not fetch when not authenticated", () => {
    renderHook(() =>
      useModelMetadata({
        backendUrl: "http://test-backend.com",
        isAuthenticated: false,
        authLoading: false,
      }),
    );

    expect(fetchModelMetadata).not.toHaveBeenCalled();
  });

  it("should not fetch while auth is loading", () => {
    renderHook(() =>
      useModelMetadata({
        backendUrl: "http://test-backend.com",
        isAuthenticated: true,
        authLoading: true,
      }),
    );

    expect(fetchModelMetadata).not.toHaveBeenCalled();
  });

  it("should handle no default model", async () => {
    const metadataWithoutDefault = [
      { pipelineId: "pipeline-1", name: "Model 1", default: false },
      { pipelineId: "pipeline-2", name: "Model 2", default: false },
    ];

    (fetchModelMetadata as any).mockResolvedValue(metadataWithoutDefault);

    renderHook(() =>
      useModelMetadata({
        backendUrl: "http://test-backend.com",
        isAuthenticated: true,
        authLoading: false,
      }),
    );

    await waitFor(() => {
      expect(mockSetMetadata).toHaveBeenCalledWith(metadataWithoutDefault);
    });

    // Should not set selected model if no default
    expect(mockSetSelectedModel).not.toHaveBeenCalled();
  });

  it("should handle errors and show alert", async () => {
    const mockError = new Error("Failed to fetch metadata");
    (fetchModelMetadata as any).mockRejectedValue(mockError);

    renderHook(() =>
      useModelMetadata({
        backendUrl: "http://test-backend.com",
        isAuthenticated: true,
        authLoading: false,
      }),
    );

    await waitFor(() => {
      expect(console.error).toHaveBeenCalledWith(
        "Error fetching model metadata:",
        "Failed to fetch metadata",
      );
    });

    await waitFor(() => {
      expect(window.alert).toHaveBeenCalledWith(
        "Error fetching model metadata, see console for details",
      );
    });

    await waitFor(() => {
      expect(mockSetLoading).toHaveBeenCalledWith(false);
    });
  });

  it("should handle non-Error rejection", async () => {
    (fetchModelMetadata as any).mockRejectedValue("String error");

    renderHook(() =>
      useModelMetadata({
        backendUrl: "http://test-backend.com",
        isAuthenticated: true,
        authLoading: false,
      }),
    );

    await waitFor(() => {
      expect(console.error).toHaveBeenCalledWith(
        "Error fetching model metadata:",
        "String error",
      );
    });

    await waitFor(() => {
      expect(mockSetLoading).toHaveBeenCalledWith(false);
    });
  });

  it("should return metadata and selectedModel from store", () => {
    (useModelStore as any).mockReturnValue({
      metadata: mockMetadata,
      selectedModel: "pipeline-2",
      setMetadata: mockSetMetadata,
      setSelectedModel: mockSetSelectedModel,
      setLoading: mockSetLoading,
    });

    const { result } = renderHook(() =>
      useModelMetadata({
        backendUrl: "http://test-backend.com",
        isAuthenticated: true,
        authLoading: false,
      }),
    );

    expect(result.current.metadata).toEqual(mockMetadata);
    expect(result.current.selectedModel).toBe("pipeline-2");
  });

  it("should refetch when dependencies change", async () => {
    const { rerender } = renderHook(
      ({ backendUrl }) =>
        useModelMetadata({
          backendUrl,
          isAuthenticated: true,
          authLoading: false,
        }),
      {
        initialProps: { backendUrl: "http://test-backend-1.com" },
      },
    );

    await waitFor(() => {
      expect(fetchModelMetadata).toHaveBeenCalledTimes(1);
    });

    // Change backendUrl
    rerender({ backendUrl: "http://test-backend-2.com" });

    await waitFor(() => {
      expect(fetchModelMetadata).toHaveBeenCalledTimes(2);
    });
  });
});
