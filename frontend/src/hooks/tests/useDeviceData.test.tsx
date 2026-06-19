import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useDeviceData } from "../useDeviceData";
import { useDeviceStore } from "@stores/useDeviceStore";
import { fetchDevices } from "@common/api";
import { acquireAccessToken } from "@common/auth";
import { useMsal, useIsAuthenticated } from "@azure/msal-react";
import { InteractionStatus } from "@azure/msal-browser";

// Mock dependencies
vi.mock("@stores/useDeviceStore");
vi.mock("@common/api");
vi.mock("@common/auth");
vi.mock("@azure/msal-react");

describe("useDeviceData", () => {
  let mockSetDevicesData: any;
  let mockSetLoading: any;
  let mockSetError: any;
  let mockMsalInstance: any;
  const mockDevicesData = {
    devices: [
      { id: "device-1", name: "Device 1" },
      { id: "device-2", name: "Device 2" },
    ],
  };

  beforeEach(() => {
    vi.clearAllMocks();

    mockSetDevicesData = vi.fn();
    mockSetLoading = vi.fn();
    mockSetError = vi.fn();
    mockMsalInstance = {} as any;

    // Mock the store
    (useDeviceStore as any).mockReturnValue({
      devicesData: null,
      isLoading: false,
      error: null,
      setDevicesData: mockSetDevicesData,
      setLoading: mockSetLoading,
      setError: mockSetError,
    });

    // Mock useMsal
    (useMsal as any).mockReturnValue({
      instance: mockMsalInstance,
      inProgress: InteractionStatus.None,
    });

    // Mock useIsAuthenticated
    (useIsAuthenticated as any).mockReturnValue(true);

    // Mock auth
    (acquireAccessToken as any).mockResolvedValue("test-token");

    // Mock fetchDevices
    (fetchDevices as any).mockResolvedValue(mockDevicesData);

    // Mock console
    vi.spyOn(console, "error").mockImplementation(() => {});
  });

  it("should fetch and set device data when authenticated", async () => {
    renderHook(() => useDeviceData("http://test-backend.com", "test-scope"));

    await waitFor(() => {
      expect(mockSetLoading).toHaveBeenCalledWith(true);
    });

    await waitFor(() => {
      expect(acquireAccessToken).toHaveBeenCalledWith(mockMsalInstance, [
        "test-scope",
      ]);
    });

    await waitFor(() => {
      expect(fetchDevices).toHaveBeenCalledWith({
        backendUrl: "http://test-backend.com",
        accessToken: "test-token",
      });
    });

    await waitFor(() => {
      expect(mockSetDevicesData).toHaveBeenCalledWith(mockDevicesData);
    });

    await waitFor(() => {
      expect(mockSetLoading).toHaveBeenCalledWith(false);
    });
  });

  it("should not fetch when backendUrl is empty", () => {
    renderHook(() => useDeviceData("", "test-scope"));

    expect(fetchDevices).not.toHaveBeenCalled();
  });

  it("should not fetch when not authenticated", () => {
    (useIsAuthenticated as any).mockReturnValue(false);

    renderHook(() => useDeviceData("http://test-backend.com", "test-scope"));

    expect(fetchDevices).not.toHaveBeenCalled();
  });

  it("should not fetch when data already exists", () => {
    (useDeviceStore as any).mockReturnValue({
      devicesData: mockDevicesData,
      isLoading: false,
      error: null,
      setDevicesData: mockSetDevicesData,
      setLoading: mockSetLoading,
      setError: mockSetError,
    });

    renderHook(() => useDeviceData("http://test-backend.com", "test-scope"));

    expect(fetchDevices).not.toHaveBeenCalled();
  });

  it("should not fetch when interaction is in progress", () => {
    (useMsal as any).mockReturnValue({
      instance: mockMsalInstance,
      inProgress: InteractionStatus.Login,
    });

    renderHook(() => useDeviceData("http://test-backend.com", "test-scope"));

    expect(fetchDevices).not.toHaveBeenCalled();
  });

  it("should handle errors", async () => {
    const mockError = new Error("Failed to fetch devices");
    (fetchDevices as any).mockRejectedValue(mockError);

    renderHook(() => useDeviceData("http://test-backend.com", "test-scope"));

    await waitFor(() => {
      expect(mockSetError).toHaveBeenCalledWith("Failed to fetch devices");
    });

    await waitFor(() => {
      expect(console.error).toHaveBeenCalledWith(
        "Error fetching device data:",
        mockError,
      );
    });

    await waitFor(() => {
      expect(mockSetLoading).toHaveBeenCalledWith(false);
    });
  });

  it("should handle non-Error rejection", async () => {
    (fetchDevices as any).mockRejectedValue("String error");

    renderHook(() => useDeviceData("http://test-backend.com", "test-scope"));

    await waitFor(() => {
      expect(mockSetError).toHaveBeenCalledWith("Unknown error occurred");
    });

    await waitFor(() => {
      expect(mockSetLoading).toHaveBeenCalledWith(false);
    });
  });

  it("should return devicesData, isLoading, and error from store", () => {
    (useDeviceStore as any).mockReturnValue({
      devicesData: mockDevicesData,
      isLoading: true,
      error: "Test error",
      setDevicesData: mockSetDevicesData,
      setLoading: mockSetLoading,
      setError: mockSetError,
    });

    const { result } = renderHook(() =>
      useDeviceData("http://test-backend.com", "test-scope"),
    );

    expect(result.current.devicesData).toEqual(mockDevicesData);
    expect(result.current.isLoading).toBe(true);
    expect(result.current.error).toBe("Test error");
  });
});
