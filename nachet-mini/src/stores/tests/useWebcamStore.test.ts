import { describe, it, expect, beforeEach } from "vitest";
import { useWebcamStore } from "../useWebcamStore";

const initialState = {
  devices: [] as MediaDeviceInfo[],
  activeDeviceId: undefined,
};

describe("useWebcamStore", () => {
  beforeEach(() => {
    useWebcamStore.setState(initialState);
  });

  it("has correct initial state", () => {
    const { devices, activeDeviceId } = useWebcamStore.getState();
    expect(devices).toEqual([]);
    expect(activeDeviceId).toBeUndefined();
  });

  describe("setDevices", () => {
    it("sets devices list", () => {
      const mockDevices = [
        { deviceId: "cam1", label: "Camera 1" },
      ] as MediaDeviceInfo[];
      useWebcamStore.getState().setDevices(mockDevices);
      expect(useWebcamStore.getState().devices).toEqual(mockDevices);
    });

    it("replaces previous devices entirely", () => {
      const first = [{ deviceId: "cam1" }] as MediaDeviceInfo[];
      const second = [
        { deviceId: "cam2" },
        { deviceId: "cam3" },
      ] as MediaDeviceInfo[];
      useWebcamStore.getState().setDevices(first);
      useWebcamStore.getState().setDevices(second);
      expect(useWebcamStore.getState().devices).toEqual(second);
    });

    it("accepts empty array to clear devices", () => {
      useWebcamStore
        .getState()
        .setDevices([{ deviceId: "cam1" }] as MediaDeviceInfo[]);
      useWebcamStore.getState().setDevices([]);
      expect(useWebcamStore.getState().devices).toEqual([]);
    });
  });

  describe("setActiveDeviceId", () => {
    it("sets active device id", () => {
      useWebcamStore.getState().setActiveDeviceId("device-abc");
      expect(useWebcamStore.getState().activeDeviceId).toBe("device-abc");
    });

    it("can be updated to a different id", () => {
      useWebcamStore.getState().setActiveDeviceId("device-1");
      useWebcamStore.getState().setActiveDeviceId("device-2");
      expect(useWebcamStore.getState().activeDeviceId).toBe("device-2");
    });

    it("accepts undefined to clear selection", () => {
      useWebcamStore.getState().setActiveDeviceId("device-1");
      useWebcamStore.getState().setActiveDeviceId(undefined);
      expect(useWebcamStore.getState().activeDeviceId).toBeUndefined();
    });
  });
});
