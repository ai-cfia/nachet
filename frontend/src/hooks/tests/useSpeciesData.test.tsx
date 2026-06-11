import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useSpeciesData } from "../useSpeciesData";
import { useSpeciesStore } from "@stores/useSpeciesStore";
import { requestClassList } from "@common/api";
import { acquireAccessToken, isAppAuthenticated } from "@common/auth";
import { useMsal, useIsAuthenticated } from "@azure/msal-react";
import { InteractionStatus } from "@azure/msal-browser";

// Mock dependencies
vi.mock("@stores/useSpeciesStore");
vi.mock("@common/api");
vi.mock("@common/auth");
vi.mock("@azure/msal-react");

describe("useSpeciesData", () => {
  let mockSetSpeciesData: any;
  let mockSetLoading: any;
  let mockSetError: any;
  let mockMsalInstance: any;
  const mockSpeciesData = [
    { id: 1, name: "Species 1" },
    { id: 2, name: "Species 2" },
  ];

  beforeEach(() => {
    vi.clearAllMocks();

    mockSetSpeciesData = vi.fn();
    mockSetLoading = vi.fn();
    mockSetError = vi.fn();
    mockMsalInstance = {} as any;

    (useSpeciesStore as any).mockReturnValue({
      speciesData: null,
      isLoading: false,
      error: null,
      setSpeciesData: mockSetSpeciesData,
      setLoading: mockSetLoading,
      setError: mockSetError,
    });

    (useMsal as any).mockReturnValue({
      instance: mockMsalInstance,
      inProgress: InteractionStatus.None,
    });

    (useIsAuthenticated as any).mockReturnValue(true);
    (isAppAuthenticated as any).mockImplementation(
      (isMsalAuthenticated: boolean) => isMsalAuthenticated,
    );
    (acquireAccessToken as any).mockResolvedValue("test-token");
    (requestClassList as any).mockResolvedValue(mockSpeciesData);

    vi.spyOn(console, "error").mockImplementation(() => {});
  });

  it("should fetch and set species data when authenticated", async () => {
    renderHook(() => useSpeciesData("http://test-backend.com", "test-scope"));

    await waitFor(() => {
      expect(mockSetLoading).toHaveBeenCalledWith(true);
      expect(mockSetError).toHaveBeenCalledWith(null);
    });

    await waitFor(() => {
      expect(requestClassList).toHaveBeenCalledWith({
        backendUrl: "http://test-backend.com",
        accessToken: "test-token",
      });
    });

    await waitFor(() => {
      expect(mockSetSpeciesData).toHaveBeenCalledWith(mockSpeciesData);
      expect(mockSetLoading).toHaveBeenCalledWith(false);
    });
  });

  it("should not fetch when backendUrl is empty", () => {
    renderHook(() => useSpeciesData("", "test-scope"));
    expect(requestClassList).not.toHaveBeenCalled();
  });

  it("should not fetch when not authenticated", () => {
    (useIsAuthenticated as any).mockReturnValue(false);
    renderHook(() => useSpeciesData("http://test-backend.com", "test-scope"));
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

    renderHook(() => useSpeciesData("http://test-backend.com", "test-scope"));
    expect(requestClassList).not.toHaveBeenCalled();
  });

  it("should not fetch when interaction is in progress", () => {
    (useMsal as any).mockReturnValue({
      instance: mockMsalInstance,
      inProgress: InteractionStatus.Login,
    });

    renderHook(() => useSpeciesData("http://test-backend.com", "test-scope"));
    expect(requestClassList).not.toHaveBeenCalled();
  });

  it("should handle errors", async () => {
    const mockError = new Error("Failed to fetch species");
    (requestClassList as any).mockRejectedValue(mockError);

    renderHook(() => useSpeciesData("http://test-backend.com", "test-scope"));

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
      useSpeciesData("http://test-backend.com", "test-scope"),
    );

    expect(result.current.speciesData).toEqual(mockSpeciesData);
    expect(result.current.isLoading).toBe(true);
    expect(result.current.error).toBe("Test error");
  });
});
