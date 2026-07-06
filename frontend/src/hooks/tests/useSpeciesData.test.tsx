import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useSpeciesData } from "../useSpeciesData";
import { useSpeciesStore } from "@stores/useSpeciesStore";
import { requestClassList } from "@common/api";
import { useNachetAuth } from "@auth";

// Mock dependencies
vi.mock("@stores/useSpeciesStore");
vi.mock("@common/api");
vi.mock("@auth");

describe("useSpeciesData", () => {
  let mockSetSpeciesData: any;
  let mockSetLoading: any;
  let mockSetError: any;
  const mockSpeciesData = [
    { id: 1, name: "Species 1" },
    { id: 2, name: "Species 2" },
  ];

  beforeEach(() => {
    vi.clearAllMocks();

    mockSetSpeciesData = vi.fn();
    mockSetLoading = vi.fn();
    mockSetError = vi.fn();

    (useSpeciesStore as any).mockReturnValue({
      speciesData: null,
      isLoading: false,
      error: null,
      setSpeciesData: mockSetSpeciesData,
      setLoading: mockSetLoading,
      setError: mockSetError,
    });

    (useNachetAuth as any).mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
    });
    (requestClassList as any).mockResolvedValue(mockSpeciesData);

    vi.spyOn(console, "error").mockImplementation(() => {});
  });

  it("should fetch and set species data when authenticated", async () => {
    renderHook(() => useSpeciesData("http://test-backend.com"));

    await waitFor(() => {
      expect(mockSetLoading).toHaveBeenCalledWith(true);
      expect(mockSetError).toHaveBeenCalledWith(null);
    });

    await waitFor(() => {
      expect(requestClassList).toHaveBeenCalledWith({
        backendUrl: "http://test-backend.com",
      });
    });

    await waitFor(() => {
      expect(mockSetSpeciesData).toHaveBeenCalledWith(mockSpeciesData);
      expect(mockSetLoading).toHaveBeenCalledWith(false);
    });
  });

  it("should not fetch when backendUrl is empty", () => {
    renderHook(() => useSpeciesData(""));
    expect(requestClassList).not.toHaveBeenCalled();
  });

  it("should not fetch when not authenticated", () => {
    (useNachetAuth as any).mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
    });
    renderHook(() => useSpeciesData("http://test-backend.com"));
    expect(requestClassList).not.toHaveBeenCalled();
  });

  it("should not fetch when data already exists", () => {
    (useSpeciesStore as any).mockReturnValue({
      speciesData: mockSpeciesData,
      isLoading: false,
      error: null,
      setSpeciesData: mockSetSpeciesData,
      setLoading: mockSetLoading,
      setError: mockSetError,
    });

    renderHook(() => useSpeciesData("http://test-backend.com"));
    expect(requestClassList).not.toHaveBeenCalled();
  });

  it("should not fetch while auth is loading", () => {
    (useNachetAuth as any).mockReturnValue({
      isAuthenticated: true,
      isLoading: true,
    });

    renderHook(() => useSpeciesData("http://test-backend.com"));
    expect(requestClassList).not.toHaveBeenCalled();
  });

  it("should handle errors", async () => {
    const mockError = new Error("Failed to fetch species");
    (requestClassList as any).mockRejectedValue(mockError);

    renderHook(() => useSpeciesData("http://test-backend.com"));

    await waitFor(() => {
      expect(mockSetError).toHaveBeenCalledWith("Failed to fetch species");
      expect(console.error).toHaveBeenCalled();
      expect(mockSetLoading).toHaveBeenCalledWith(false);
    });
  });

  it("should return speciesData, isLoading, and error from store", () => {
    (useSpeciesStore as any).mockReturnValue({
      speciesData: mockSpeciesData,
      isLoading: true,
      error: "Test error",
      setSpeciesData: mockSetSpeciesData,
      setLoading: mockSetLoading,
      setError: mockSetError,
    });

    const { result } = renderHook(() =>
      useSpeciesData("http://test-backend.com"),
    );

    expect(result.current.speciesData).toEqual(mockSpeciesData);
    expect(result.current.isLoading).toBe(true);
    expect(result.current.error).toBe("Test error");
  });
});
