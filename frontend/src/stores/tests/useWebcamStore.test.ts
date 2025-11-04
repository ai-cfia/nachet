import { describe, it, expect, beforeEach } from "vitest";
import { act } from "@testing-library/react";
import { useWebcamStore } from "../useWebcamStore";

describe("useWebcamStore", () => {
  const mockDevice1: MediaDeviceInfo = {
    deviceId: "device-1",
    groupId: "group-1",
    kind: "videoinput",
    label: "USB Camera 1",
    toJSON: () => ({}),
  };

  const mockDevice2: MediaDeviceInfo = {
    deviceId: "device-2",
    groupId: "group-2",
    kind: "videoinput",
    label: "Integrated Webcam",
    toJSON: () => ({}),
  };

  const mockDevice3: MediaDeviceInfo = {
    deviceId: "device-3",
    groupId: "group-3",
    kind: "videoinput",
    label: "External Camera",
    toJSON: () => ({}),
  };

  beforeEach(() => {
    // Reset store to initial state
    act(() => {
      useWebcamStore.setState({
        devices: [],
        activeDeviceId: undefined,
      });
    });
  });

  describe("Initial State", () => {
    it("should have empty devices array", () => {
      expect(useWebcamStore.getState().devices).toEqual([]);
    });

    it("should have undefined activeDeviceId", () => {
      expect(useWebcamStore.getState().activeDeviceId).toBeUndefined();
    });
  });

  describe("setDevices", () => {
    it("should set devices", () => {
      const devices = [mockDevice1, mockDevice2];

      act(() => {
        useWebcamStore.getState().setDevices(devices);
      });

      expect(useWebcamStore.getState().devices).toEqual(devices);
    });

    it("should update devices", () => {
      act(() => {
        useWebcamStore.getState().setDevices([mockDevice1]);
        useWebcamStore.getState().setDevices([mockDevice2, mockDevice3]);
      });

      const state = useWebcamStore.getState();
      expect(state.devices).toEqual([mockDevice2, mockDevice3]);
      expect(state.devices).toHaveLength(2);
    });

    it("should handle empty devices array", () => {
      act(() => {
        useWebcamStore.getState().setDevices([mockDevice1, mockDevice2]);
        useWebcamStore.getState().setDevices([]);
      });

      expect(useWebcamStore.getState().devices).toEqual([]);
    });

    it("should handle single device", () => {
      act(() => {
        useWebcamStore.getState().setDevices([mockDevice1]);
      });

      const state = useWebcamStore.getState();
      expect(state.devices).toHaveLength(1);
      expect(state.devices[0].deviceId).toBe("device-1");
    });

    it("should handle multiple devices", () => {
      const devices = [mockDevice1, mockDevice2, mockDevice3];

      act(() => {
        useWebcamStore.getState().setDevices(devices);
      });

      const state = useWebcamStore.getState();
      expect(state.devices).toHaveLength(3);
      expect(state.devices[0].label).toBe("USB Camera 1");
      expect(state.devices[1].label).toBe("Integrated Webcam");
      expect(state.devices[2].label).toBe("External Camera");
    });

    it("should not affect activeDeviceId", () => {
      act(() => {
        useWebcamStore.getState().setActiveDeviceId("device-1");
        useWebcamStore.getState().setDevices([mockDevice2, mockDevice3]);
      });

      const state = useWebcamStore.getState();
      expect(state.devices).toHaveLength(2);
      expect(state.activeDeviceId).toBe("device-1");
    });
  });

  describe("setActiveDeviceId", () => {
    it("should set active device ID", () => {
      act(() => {
        useWebcamStore.getState().setActiveDeviceId("device-1");
      });

      expect(useWebcamStore.getState().activeDeviceId).toBe("device-1");
    });

    it("should update active device ID", () => {
      act(() => {
        useWebcamStore.getState().setActiveDeviceId("device-1");
        useWebcamStore.getState().setActiveDeviceId("device-2");
      });

      expect(useWebcamStore.getState().activeDeviceId).toBe("device-2");
    });

    it("should set to undefined", () => {
      act(() => {
        useWebcamStore.getState().setActiveDeviceId("device-1");
        useWebcamStore.getState().setActiveDeviceId(undefined);
      });

      expect(useWebcamStore.getState().activeDeviceId).toBeUndefined();
    });

    it("should handle empty string", () => {
      act(() => {
        useWebcamStore.getState().setActiveDeviceId("");
      });

      expect(useWebcamStore.getState().activeDeviceId).toBe("");
    });

    it("should not affect devices", () => {
      const devices = [mockDevice1, mockDevice2];

      act(() => {
        useWebcamStore.getState().setDevices(devices);
        useWebcamStore.getState().setActiveDeviceId("device-2");
      });

      const state = useWebcamStore.getState();
      expect(state.activeDeviceId).toBe("device-2");
      expect(state.devices).toEqual(devices);
    });
  });

  describe("Device Selection Workflow", () => {
    it("should handle device discovery and selection", () => {
      const devices = [mockDevice1, mockDevice2, mockDevice3];

      // Enumerate devices
      act(() => {
        useWebcamStore.getState().setDevices(devices);
      });

      expect(useWebcamStore.getState().devices).toHaveLength(3);

      // Select device
      act(() => {
        useWebcamStore.getState().setActiveDeviceId(devices[1].deviceId);
      });

      const state = useWebcamStore.getState();
      expect(state.activeDeviceId).toBe("device-2");
      expect(state.devices).toEqual(devices);
    });

    it("should handle device switching", () => {
      const devices = [mockDevice1, mockDevice2];

      act(() => {
        useWebcamStore.getState().setDevices(devices);
        useWebcamStore.getState().setActiveDeviceId("device-1");
      });

      expect(useWebcamStore.getState().activeDeviceId).toBe("device-1");

      act(() => {
        useWebcamStore.getState().setActiveDeviceId("device-2");
      });

      expect(useWebcamStore.getState().activeDeviceId).toBe("device-2");
    });

    it("should handle device disconnection", () => {
      const devices = [mockDevice1, mockDevice2, mockDevice3];

      act(() => {
        useWebcamStore.getState().setDevices(devices);
        useWebcamStore.getState().setActiveDeviceId("device-2");
      });

      // Device disconnected
      act(() => {
        useWebcamStore.getState().setDevices([mockDevice1, mockDevice3]);
      });

      const state = useWebcamStore.getState();
      expect(state.devices).toHaveLength(2);
      expect(state.activeDeviceId).toBe("device-2"); // Preserved even if device disconnected
    });
  });

  describe("State Independence", () => {
    it("should manage devices and activeDeviceId independently", () => {
      act(() => {
        useWebcamStore.getState().setActiveDeviceId("device-1");
        useWebcamStore.getState().setDevices([mockDevice2]);
      });

      const state = useWebcamStore.getState();
      expect(state.activeDeviceId).toBe("device-1");
      expect(state.devices).toEqual([mockDevice2]);
    });

    it("should allow activeDeviceId without devices", () => {
      act(() => {
        useWebcamStore.getState().setActiveDeviceId("device-1");
      });

      const state = useWebcamStore.getState();
      expect(state.activeDeviceId).toBe("device-1");
      expect(state.devices).toEqual([]);
    });

    it("should allow devices without activeDeviceId", () => {
      act(() => {
        useWebcamStore.getState().setDevices([mockDevice1, mockDevice2]);
      });

      const state = useWebcamStore.getState();
      expect(state.devices).toHaveLength(2);
      expect(state.activeDeviceId).toBeUndefined();
    });
  });

  describe("Edge Cases", () => {
    it("should handle device with empty label", () => {
      const deviceWithEmptyLabel: MediaDeviceInfo = {
        deviceId: "device-x",
        groupId: "group-x",
        kind: "videoinput",
        label: "",
        toJSON: () => ({}),
      };

      act(() => {
        useWebcamStore.getState().setDevices([deviceWithEmptyLabel]);
      });

      const state = useWebcamStore.getState();
      expect(state.devices[0].label).toBe("");
    });

    it("should handle duplicate deviceIds", () => {
      const duplicateDevices: MediaDeviceInfo[] = [
        {
          deviceId: "device-1",
          groupId: "group-1",
          kind: "videoinput",
          label: "Camera 1",
          toJSON: () => ({}),
        },
        {
          deviceId: "device-1",
          groupId: "group-2",
          kind: "videoinput",
          label: "Camera 1 Clone",
          toJSON: () => ({}),
        },
      ];

      act(() => {
        useWebcamStore.getState().setDevices(duplicateDevices);
      });

      const state = useWebcamStore.getState();
      expect(state.devices).toHaveLength(2);
      expect(state.devices[0].deviceId).toBe("device-1");
      expect(state.devices[1].deviceId).toBe("device-1");
    });

    it("should handle rapid state changes", () => {
      act(() => {
        useWebcamStore.getState().setDevices([mockDevice1]);
        useWebcamStore.getState().setActiveDeviceId("device-1");
        useWebcamStore.getState().setDevices([mockDevice1, mockDevice2]);
        useWebcamStore.getState().setActiveDeviceId("device-2");
        useWebcamStore.getState().setDevices([mockDevice2, mockDevice3]);
      });

      const state = useWebcamStore.getState();
      expect(state.activeDeviceId).toBe("device-2");
      expect(state.devices).toEqual([mockDevice2, mockDevice3]);
    });

    it("should preserve device object references", () => {
      const devices = [mockDevice1, mockDevice2];

      act(() => {
        useWebcamStore.getState().setDevices(devices);
      });

      expect(useWebcamStore.getState().devices).toBe(devices);
    });
  });
});
