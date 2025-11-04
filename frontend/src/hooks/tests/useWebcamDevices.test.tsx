import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { useWebcamDevices } from "../useWebcamDevices";
import { useWebcamStore } from "@stores/useWebcamStore";

// Mock the store
vi.mock("@stores/useWebcamStore");

describe("useWebcamDevices", () => {
  let mockSetDevices: any;
  let mockSetActiveDeviceId: any;
  let mockEnumerateDevices: any;

  beforeEach(() => {
    vi.clearAllMocks();

    mockSetDevices = vi.fn();
    mockSetActiveDeviceId = vi.fn();

    // Mock the store hook
    (useWebcamStore as any).mockReturnValue({
      devices: [],
      activeDeviceId: "",
      setDevices: mockSetDevices,
      setActiveDeviceId: mockSetActiveDeviceId,
    });

    // Mock navigator.mediaDevices
    mockEnumerateDevices = vi.fn();
    global.navigator = {
      mediaDevices: {
        enumerateDevices: mockEnumerateDevices,
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
      },
    } as any;
  });

  it("should enumerate and set video devices", async () => {
    const mockDevices = [
      { deviceId: "device1", kind: "videoinput", label: "Camera 1" },
      { deviceId: "device2", kind: "videoinput", label: "Camera 2" },
      { deviceId: "device3", kind: "audioinput", label: "Mic 1" },
    ];

    mockEnumerateDevices.mockResolvedValue(mockDevices);

    renderHook(() => useWebcamDevices());

    await waitFor(() => {
      expect(mockEnumerateDevices).toHaveBeenCalled();
    });

    await waitFor(() => {
      expect(mockSetDevices).toHaveBeenCalledWith([
        { deviceId: "device1", kind: "videoinput", label: "Camera 1" },
        { deviceId: "device2", kind: "videoinput", label: "Camera 2" },
      ]);
    });

    await waitFor(() => {
      expect(mockSetActiveDeviceId).toHaveBeenCalledWith("device1");
    });
  });

  it("should not set active device if already set", async () => {
    (useWebcamStore as any).mockReturnValue({
      devices: [],
      activeDeviceId: "existing-device",
      setDevices: mockSetDevices,
      setActiveDeviceId: mockSetActiveDeviceId,
    });

    const mockDevices = [
      { deviceId: "device1", kind: "videoinput", label: "Camera 1" },
    ];

    mockEnumerateDevices.mockResolvedValue(mockDevices);

    renderHook(() => useWebcamDevices());

    await waitFor(() => {
      expect(mockSetDevices).toHaveBeenCalled();
    });

    // Should not set active device if one is already set
    expect(mockSetActiveDeviceId).not.toHaveBeenCalled();
  });

  it("should handle no video devices", async () => {
    const mockDevices = [
      { deviceId: "device1", kind: "audioinput", label: "Mic 1" },
    ];

    mockEnumerateDevices.mockResolvedValue(mockDevices);

    renderHook(() => useWebcamDevices());

    await waitFor(() => {
      expect(mockSetDevices).toHaveBeenCalledWith([]);
    });
  });

  it("should handle errors with alert", async () => {
    const mockError = new Error("Device enumeration failed");
    mockEnumerateDevices.mockRejectedValue(mockError);

    const alertSpy = vi.spyOn(window, "alert").mockImplementation(() => {});

    renderHook(() => useWebcamDevices());

    await waitFor(() => {
      expect(alertSpy).toHaveBeenCalledWith(mockError);
    });

    alertSpy.mockRestore();
  });

  it("should set up device change listener", () => {
    const mockDevices = [
      { deviceId: "device1", kind: "videoinput", label: "Camera 1" },
    ];

    mockEnumerateDevices.mockResolvedValue(mockDevices);

    const { unmount } = renderHook(() => useWebcamDevices());

    expect(global.navigator.mediaDevices.addEventListener).toHaveBeenCalledWith(
      "devicechange",
      expect.any(Function),
    );

    unmount();

    expect(global.navigator.mediaDevices.removeEventListener).toHaveBeenCalledWith(
      "devicechange",
      expect.any(Function),
    );
  });

  it("should return devices and activeDeviceId", () => {
    const mockDevices = [
      { deviceId: "device1", kind: "videoinput", label: "Camera 1" },
    ];

    (useWebcamStore as any).mockReturnValue({
      devices: mockDevices,
      activeDeviceId: "device1",
      setDevices: mockSetDevices,
      setActiveDeviceId: mockSetActiveDeviceId,
    });

    mockEnumerateDevices.mockResolvedValue(mockDevices);

    const { result } = renderHook(() => useWebcamDevices());

    expect(result.current.devices).toEqual(mockDevices);
    expect(result.current.activeDeviceId).toBe("device1");
  });

  it("should not run if navigator.mediaDevices is not available", () => {
    global.navigator = {} as any;

    renderHook(() => useWebcamDevices());

    expect(mockEnumerateDevices).not.toHaveBeenCalled();
  });

  it("should not run if enumerateDevices is not a function", () => {
    global.navigator = {
      mediaDevices: {
        enumerateDevices: null as any,
      },
    } as any;

    renderHook(() => useWebcamDevices());

    expect(mockEnumerateDevices).not.toHaveBeenCalled();
  });
});
