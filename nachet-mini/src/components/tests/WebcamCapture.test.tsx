import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { render, cleanup } from "@testing-library/react";
import { page } from "vitest/browser";
import { createRef } from "react";
import { useWebcamDevices } from "@hooks/useWebcamDevices";
import { useIsPortrait } from "@hooks/useIsPortrait";
import type Webcam from "react-webcam";
import WebcamCapture from "../WebcamCapture";

type MockWebcamProps = {
  style?: Record<string, string>;
  mirrored?: boolean;
  width?: string;
  height?: string;
  forceScreenshotSourceSize?: boolean;
  screenshotFormat?: string;
  screenshotQuality?: number;
  videoConstraints?: {
    width: number;
    height: number;
    deviceId?: { exact: string };
    facingMode?: string;
  };
  onUserMediaError?: (err: string | DOMException) => void;
};

const webcamMock = vi.hoisted(() => ({
  lastProps: null as MockWebcamProps | null,
}));

vi.mock("@hooks/useWebcamDevices", () => ({ useWebcamDevices: vi.fn() }));
vi.mock("@hooks/useIsPortrait", () => ({ useIsPortrait: vi.fn() }));
vi.mock("react-webcam", async () => {
  const React = await import("react");

  const MockWebcam = React.forwardRef(function MockWebcam(
    props: MockWebcamProps,
    ref: React.ForwardedRef<{ getScreenshot: () => string | null }>,
  ) {
    webcamMock.lastProps = props;
    React.useImperativeHandle(ref, () => ({
      getScreenshot: () => "mock-screenshot",
    }));

    return React.createElement("video", {
      "data-testid": "webcam-video",
      style: props.style,
    });
  });

  return { __esModule: true, default: MockWebcam };
});

const makeDevice = (id: string): MediaDeviceInfo =>
  ({
    deviceId: id,
    kind: "videoinput" as MediaDeviceKind,
    label: `Camera ${id}`,
    groupId: "",
    toJSON: () => ({}),
  }) as MediaDeviceInfo;

const getLastWebcamProps = () => {
  expect(webcamMock.lastProps).not.toBeNull();
  return webcamMock.lastProps as MockWebcamProps;
};

describe("WebcamCapture", () => {
  let webcamRef: React.RefObject<Webcam | null>;
  const onUserMediaError = vi.fn();

  beforeEach(() => {
    webcamRef = createRef<Webcam | null>();
    webcamMock.lastProps = null;
    vi.mocked(useWebcamDevices).mockReturnValue({
      devices: [],
      activeDeviceId: undefined,
    });
    vi.mocked(useIsPortrait).mockReturnValue(false);
    onUserMediaError.mockClear();
  });

  afterEach(cleanup);

  describe("no camera", () => {
    it('shows "No camera detected" when devices list is empty', async () => {
      render(
        <WebcamCapture
          webcamRef={webcamRef}
          onUserMediaError={onUserMediaError}
        />,
      );
      await expect
        .element(page.getByText("No camera detected"))
        .toBeVisible();
    });

    it("does not render the webcam component when no devices are available", async () => {
      render(
        <WebcamCapture
          webcamRef={webcamRef}
          onUserMediaError={onUserMediaError}
        />,
      );
      expect(webcamMock.lastProps).toBeNull();
      expect(await page.getByTestId("webcam-video").all()).toHaveLength(0);
    });
  });

  describe("camera available", () => {
    beforeEach(() => {
      vi.mocked(useWebcamDevices).mockReturnValue({
        devices: [makeDevice("cam-1")],
        activeDeviceId: "cam-1",
      });
    });

    it("renders the webcam component and assigns the ref", async () => {
      render(
        <WebcamCapture
          webcamRef={webcamRef}
          onUserMediaError={onUserMediaError}
        />,
      );
      await expect.element(page.getByTestId("webcam-video")).toBeVisible();
      expect(webcamRef.current).not.toBeNull();
    });

    it("passes the expected base webcam props", () => {
      render(
        <WebcamCapture
          webcamRef={webcamRef}
          onUserMediaError={onUserMediaError}
        />,
      );

      const props = getLastWebcamProps();
      expect(props.mirrored).toBe(false);
      expect(props.width).toBe("100%");
      expect(props.height).toBe("100%");
      expect(props.forceScreenshotSourceSize).toBe(true);
      expect(props.screenshotFormat).toBe("image/png");
      expect(props.screenshotQuality).toBe(1);
      expect(props.onUserMediaError).toBe(onUserMediaError);
    });

    it("uses the active device id in the webcam constraints", () => {
      vi.mocked(useWebcamDevices).mockReturnValue({
        devices: [makeDevice("cam-1"), makeDevice("cam-2")],
        activeDeviceId: "cam-2",
      });
      render(
        <WebcamCapture
          webcamRef={webcamRef}
          onUserMediaError={onUserMediaError}
        />,
      );

      expect(getLastWebcamProps().videoConstraints).toEqual({
        width: 1920,
        height: 1080,
        deviceId: { exact: "cam-2" },
      });
    });

    it('falls back to "environment" facing mode when no active device id is set', () => {
      vi.mocked(useWebcamDevices).mockReturnValue({
        devices: [makeDevice("cam-1")],
        activeDeviceId: undefined,
      });
      render(
        <WebcamCapture
          webcamRef={webcamRef}
          onUserMediaError={onUserMediaError}
        />,
      );

      expect(getLastWebcamProps().videoConstraints).toEqual({
        width: 1920,
        height: 1080,
        facingMode: "environment",
      });
    });

    it("forwards media errors to the provided callback", () => {
      render(
        <WebcamCapture
          webcamRef={webcamRef}
          onUserMediaError={onUserMediaError}
        />,
      );

      const error = new DOMException("Permission denied");
      getLastWebcamProps().onUserMediaError?.(error);
      expect(onUserMediaError).toHaveBeenCalledWith(error);
    });
  });

  describe("portrait mode", () => {
    beforeEach(() => {
      vi.mocked(useWebcamDevices).mockReturnValue({
        devices: [makeDevice("cam-1")],
        activeDeviceId: "cam-1",
      });
    });

    it("passes rotated portrait styles to the webcam", () => {
      vi.mocked(useIsPortrait).mockReturnValue(true);
      render(
        <WebcamCapture
          webcamRef={webcamRef}
          onUserMediaError={onUserMediaError}
        />,
      );

      expect(getLastWebcamProps().style).toMatchObject({
        objectFit: "contain",
        display: "block",
        transform: "rotate(-90deg)",
        maxWidth: "100%",
        maxHeight: "100%",
      });
    });

    it("does not add a rotation transform in landscape orientation", () => {
      vi.mocked(useIsPortrait).mockReturnValue(false);
      render(
        <WebcamCapture
          webcamRef={webcamRef}
          onUserMediaError={onUserMediaError}
        />,
      );

      expect(getLastWebcamProps().style).toEqual({
        objectFit: "contain",
        display: "block",
      });
    });
  });
});
