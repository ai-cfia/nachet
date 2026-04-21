// @vitest-environment jsdom
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { useWebcamDevices } from "../useWebcamDevices";
import { useWebcamStore } from "@stores/useWebcamStore";

const makeDevice = (
  overrides: Partial<MediaDeviceInfo> = {},
): MediaDeviceInfo =>
  ({
    deviceId: "device-1",
    groupId: "group-1",
    kind: "videoinput",
    label: "Camera",
    toJSON: () => ({}),
    ...overrides,
  }) as MediaDeviceInfo;

const makeMediaDevices = (
  overrides: Partial<typeof navigator.mediaDevices> = {},
) => ({
  getUserMedia: vi.fn().mockResolvedValue({
    getTracks: () => [{ stop: vi.fn() }],
  }),
  enumerateDevices: vi.fn().mockResolvedValue([]),
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  ...overrides,
});

describe("useWebcamDevices", () => {
  beforeEach(() => {
    useWebcamStore.setState({ devices: [], activeDeviceId: undefined });
    Object.defineProperty(global.navigator, "mediaDevices", {
      value: makeMediaDevices(),
      writable: true,
      configurable: true,
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns devices and activeDeviceId from the store", async () => {
    const { result } = renderHook(() => useWebcamDevices());
    await waitFor(() => {
      expect(result.current.devices).toBeDefined();
    });
    expect(result.current.activeDeviceId).toBeUndefined();
  });

  it("populates devices with videoinput devices after getUserMedia succeeds", async () => {
    const cam1 = makeDevice({ deviceId: "cam-1" });
    const cam2 = makeDevice({ deviceId: "cam-2" });
    const audio = makeDevice({ deviceId: "mic-1", kind: "audioinput" });
    Object.defineProperty(global.navigator, "mediaDevices", {
      value: makeMediaDevices({
        enumerateDevices: vi.fn().mockResolvedValue([cam1, cam2, audio]),
      }),
      writable: true,
      configurable: true,
    });

    renderHook(() => useWebcamDevices());

    await waitFor(() => {
      expect(useWebcamStore.getState().devices).toHaveLength(2);
    });
    expect(useWebcamStore.getState().devices.map((d) => d.deviceId)).toEqual([
      "cam-1",
      "cam-2",
    ]);
  });

  it("defaults activeDeviceId to the second camera (rear camera on mobile)", async () => {
    const cam1 = makeDevice({ deviceId: "cam-front" });
    const cam2 = makeDevice({ deviceId: "cam-rear" });
    Object.defineProperty(global.navigator, "mediaDevices", {
      value: makeMediaDevices({
        enumerateDevices: vi.fn().mockResolvedValue([cam1, cam2]),
      }),
      writable: true,
      configurable: true,
    });

    renderHook(() => useWebcamDevices());

    await waitFor(() => {
      expect(useWebcamStore.getState().activeDeviceId).toBe("cam-rear");
    });
  });

  it("falls back to the first camera when only one device is available", async () => {
    const cam1 = makeDevice({ deviceId: "cam-only" });
    Object.defineProperty(global.navigator, "mediaDevices", {
      value: makeMediaDevices({
        enumerateDevices: vi.fn().mockResolvedValue([cam1]),
      }),
      writable: true,
      configurable: true,
    });

    renderHook(() => useWebcamDevices());

    await waitFor(() => {
      expect(useWebcamStore.getState().activeDeviceId).toBe("cam-only");
    });
  });

  it("does not override activeDeviceId when one is already set", async () => {
    useWebcamStore.setState({ activeDeviceId: "existing-cam" });
    const cam1 = makeDevice({ deviceId: "cam-1" });
    const cam2 = makeDevice({ deviceId: "cam-2" });
    Object.defineProperty(global.navigator, "mediaDevices", {
      value: makeMediaDevices({
        enumerateDevices: vi.fn().mockResolvedValue([cam1, cam2]),
      }),
      writable: true,
      configurable: true,
    });

    renderHook(() => useWebcamDevices());

    await waitFor(() => {
      expect(useWebcamStore.getState().devices).toHaveLength(2);
    });
    expect(useWebcamStore.getState().activeDeviceId).toBe("existing-cam");
  });

  it("leaves devices empty when no video devices are available", async () => {
    const audio = makeDevice({ deviceId: "mic-1", kind: "audioinput" });
    Object.defineProperty(global.navigator, "mediaDevices", {
      value: makeMediaDevices({
        enumerateDevices: vi.fn().mockResolvedValue([audio]),
      }),
      writable: true,
      configurable: true,
    });

    renderHook(() => useWebcamDevices());

    await waitFor(() => {
      // give the async flow time to settle
      expect(navigator.mediaDevices.enumerateDevices).toHaveBeenCalled();
    });
    expect(useWebcamStore.getState().devices).toHaveLength(0);
    expect(useWebcamStore.getState().activeDeviceId).toBeUndefined();
  });

  it("does not set devices when getUserMedia is denied", async () => {
    Object.defineProperty(global.navigator, "mediaDevices", {
      value: makeMediaDevices({
        getUserMedia: vi.fn().mockRejectedValue(new Error("Permission denied")),
        enumerateDevices: vi.fn(),
      }),
      writable: true,
      configurable: true,
    });
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    renderHook(() => useWebcamDevices());

    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalled();
    });
    expect(useWebcamStore.getState().devices).toHaveLength(0);
    expect(navigator.mediaDevices.enumerateDevices).not.toHaveBeenCalled();
    consoleSpy.mockRestore();
  });

  it("does not crash when enumerateDevices rejects", async () => {
    Object.defineProperty(global.navigator, "mediaDevices", {
      value: makeMediaDevices({
        enumerateDevices: vi
          .fn()
          .mockRejectedValue(new Error("enumerate failed")),
      }),
      writable: true,
      configurable: true,
    });
    const consoleSpy = vi.spyOn(console, "error").mockImplementation(() => {});

    renderHook(() => useWebcamDevices());

    await waitFor(() => {
      expect(consoleSpy).toHaveBeenCalled();
    });
    expect(useWebcamStore.getState().devices).toHaveLength(0);
    consoleSpy.mockRestore();
  });

  it("does not crash when navigator.mediaDevices is absent", async () => {
    Object.defineProperty(global.navigator, "mediaDevices", {
      value: undefined,
      writable: true,
      configurable: true,
    });

    expect(() => renderHook(() => useWebcamDevices())).not.toThrow();
    expect(useWebcamStore.getState().devices).toHaveLength(0);
  });

  it("registers a devicechange listener on mount", () => {
    renderHook(() => useWebcamDevices());
    expect(navigator.mediaDevices.addEventListener).toHaveBeenCalledWith(
      "devicechange",
      expect.any(Function),
    );
  });

  it("removes the devicechange listener on unmount", () => {
    const { unmount } = renderHook(() => useWebcamDevices());
    unmount();
    expect(navigator.mediaDevices.removeEventListener).toHaveBeenCalledWith(
      "devicechange",
      expect.any(Function),
    );
  });

  it("re-enumerates devices when devicechange fires", async () => {
    const cam1 = makeDevice({ deviceId: "cam-1" });
    const mediaDevices = makeMediaDevices({
      enumerateDevices: vi.fn().mockResolvedValue([cam1]),
    });
    Object.defineProperty(global.navigator, "mediaDevices", {
      value: mediaDevices,
      writable: true,
      configurable: true,
    });

    renderHook(() => useWebcamDevices());

    await waitFor(() => {
      expect(useWebcamStore.getState().devices).toHaveLength(1);
    });

    const cam2 = makeDevice({ deviceId: "cam-2" });
    mediaDevices.enumerateDevices.mockResolvedValue([cam1, cam2]);
    const [[, deviceChangeHandler]] = (
      mediaDevices.addEventListener as ReturnType<typeof vi.fn>
    ).mock.calls;

    await act(async () => {
      await deviceChangeHandler();
    });

    await waitFor(() => {
      expect(useWebcamStore.getState().devices).toHaveLength(2);
    });
  });
});
