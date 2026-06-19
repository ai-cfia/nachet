import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useDeviceData } from "../useDeviceData";
import { useDeviceStore } from "@stores/useDeviceStore";
import { fetchDevices } from "@common/api";
import { useNachetAuth } from "../../auth";

// Mock dependencies
vi.mock("@stores/useDeviceStore");
vi.mock("@common/api");
vi.mock("../../auth");

describe("useDeviceData", () => {
  let mockSetDevicesData: any;
  let mockSetLoading: any;
  let mockSetError: any;
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

    // Mock the store
    (useDeviceStore as any).mockReturnValue({
      devicesData: null,
      isLoading: false,
      error: null,
      setDevicesData: mockSetDevicesData,
      setLoading: mockSetLoading,
      setError: mockSetError,
    });

    (useNachetAuth as any).mockReturnValue({
      isAuthenticated: true,
      isLoading: false,
    });

    // Mock fetchDevices
    (fetchDevices as any).mockResolvedValue(mockDevicesData);

    // Mock console
    vi.spyOn(console, "error").mockImplementation(() => {});
  });

  it("should fetch and set device data when authenticated", async () => {
    renderHook(() => useDeviceData("http://test-backend.com"));

    await waitFor(() => {
      expect(mockSetLoading).toHaveBeenCalledWith(true);
    });

    await waitFor(() => {
      expect(fetchDevices).toHaveBeenCalledWith({
        backendUrl: "http://test-backend.com",
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
    renderHook(() => useDeviceData(""));

    expect(fetchDevices).not.toHaveBeenCalled();
  });

  it("should not fetch when not authenticated", () => {
    (useNachetAuth as any).mockReturnValue({
      isAuthenticated: false,
      isLoading: false,
    });

    renderHook(() => useDeviceData("http://test-backend.com"));

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

    renderHook(() => useDeviceData("http://test-backend.com"));

    expect(fetchDevices).not.toHaveBeenCalled();
  });

  it("should not fetch while auth is loading", () => {
    (useNachetAuth as any).mockReturnValue({
      isAuthenticated: true,
      isLoading: true,
    });

    renderHook(() => useDeviceData("http://test-backend.com"));

    expect(fetchDevices).not.toHaveBeenCalled();
  });

  it("should handle errors", async () => {
    const mockError = new Error("Failed to fetch devices");
    (fetchDevices as any).mockRejectedValue(mockError);

    renderHook(() => useDeviceData("http://test-backend.com"));

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

    renderHook(() => useDeviceData("http://test-backend.com"));

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
      useDeviceData("http://test-backend.com"),
    );

    expect(result.current.devicesData).toEqual(mockDevicesData);
    expect(result.current.isLoading).toBe(true);
    expect(result.current.error).toBe("Test error");
  });
});
