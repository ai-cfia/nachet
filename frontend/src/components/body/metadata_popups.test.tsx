import { act, fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import "@testing-library/jest-dom/vitest";
import ImageMetadataPopup from "./image_metadata_popup/ImageMetadataPopup";
import SampleMetadataPopup from "./sample_metadata_popup/SampleMetadataPopup";
import { useImageStore } from "@stores/useImageStore";
import { useDeviceStore } from "@stores/useDeviceStore";
import { useModalStore } from "@stores/useModalStore";

vi.mock("react-i18next", () => ({
  useTranslation: () => ({ t: (key: string) => key }),
}));

vi.mock("@components/common", () => ({
  DeviceSelectionFields: () => null,
  PopupActionButtons: () => null,
  SampleMetadataFields: ({
    trayCode,
    onTrayCodeChange,
  }: {
    trayCode: string;
    onTrayCodeChange: (value: string) => void;
  }) => (
    <input
      aria-label="tray-code"
      value={trayCode}
      onChange={(event) => onTrayCodeChange(event.target.value)}
    />
  ),
}));

beforeEach(() => {
  useModalStore.setState({
    isImageMetadataOpen: false,
    imageMetadataImageIndex: null,
    imageMetadataMode: "edit",
    isSampleMetadataOpen: false,
  });
  useImageStore.setState({
    images: [
      {
        index: 1,
        imageName: "first",
        src: "data:image/png;base64,AA==",
        imageDims: [10, 10],
        workflowIds: [],
        activeWorkflowId: null,
        trayCode: "tray-one",
      },
      {
        index: 2,
        imageName: "second",
        src: "data:image/png;base64,AA==",
        imageDims: [10, 10],
        workflowIds: [],
        activeWorkflowId: null,
        trayCode: "tray-two",
      },
    ],
  });
  useDeviceStore.setState({
    deviceSelection: {
      selectedBrandId: "",
      selectedModelId: "",
      selectedLensId: "",
    },
    sampleMetadata: {
      trayCode: "saved-tray",
      magnification: 1,
      sampleIdPrefix: "sample",
      sampleDescription: "description",
    },
  });
});

describe("Image metadata editing sessions", () => {
  it("loads the selected image and changes fields when another image is selected", () => {
    useModalStore.getState().openImageMetadataPopup(1);
    render(<ImageMetadataPopup devicesData={null} />);
    expect(screen.getByLabelText("tray-code")).toHaveValue("tray-one");

    act(() => useModalStore.getState().openImageMetadataPopup(2));
    expect(screen.getByLabelText("tray-code")).toHaveValue("tray-two");
  });

  it("keeps a draft through image-store updates", () => {
    useModalStore.getState().openImageMetadataPopup(1);
    render(<ImageMetadataPopup devicesData={null} />);
    fireEvent.change(screen.getByLabelText("tray-code"), {
      target: { value: "draft" },
    });

    act(() =>
      useImageStore.getState().updateImageMetadata(1, { trayCode: "external" }),
    );
    expect(screen.getByLabelText("tray-code")).toHaveValue("draft");
  });

  it("reloads saved values when the same image is reopened", () => {
    useModalStore.getState().openImageMetadataPopup(1);
    render(<ImageMetadataPopup devicesData={null} />);
    fireEvent.change(screen.getByLabelText("tray-code"), {
      target: { value: "draft" },
    });

    act(() => useModalStore.getState().closeImageMetadataPopup());
    act(() => useModalStore.getState().openImageMetadataPopup(1));
    expect(screen.getByLabelText("tray-code")).toHaveValue("tray-one");
  });
});

describe("Sample metadata editing sessions", () => {
  it("loads persisted metadata on open", () => {
    useModalStore.getState().openSampleMetadataPopup();
    render(<SampleMetadataPopup devicesData={null} />);
    expect(screen.getByLabelText("tray-code")).toHaveValue("saved-tray");
  });

  it("keeps a draft until close, then reloads the latest persisted metadata", () => {
    useModalStore.getState().openSampleMetadataPopup();
    render(<SampleMetadataPopup devicesData={null} />);
    fireEvent.change(screen.getByLabelText("tray-code"), {
      target: { value: "draft" },
    });

    act(() =>
      useDeviceStore.getState().setSampleMetadata({
        ...useDeviceStore.getState().sampleMetadata,
        trayCode: "updated-tray",
      }),
    );
    expect(screen.getByLabelText("tray-code")).toHaveValue("draft");

    act(() => useModalStore.getState().closeSampleMetadataPopup());
    act(() => useModalStore.getState().openSampleMetadataPopup());
    expect(screen.getByLabelText("tray-code")).toHaveValue("updated-tray");
  });
});
