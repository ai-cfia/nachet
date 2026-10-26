import { act, render } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import Body from "./body";
import { useFolderStore } from "@stores/useFolderStore";
import { useImageStore } from "@stores/useImageStore";
import { useWorkflowStore } from "@stores/useWorkflowStore";
import { WorkflowQueueManager } from "../../services/WorkflowQueueManager";
import type { ApiInferenceData } from "@common/types";

vi.mock("react-i18next", () => {
  const t = (key: string) => key;
  return { useTranslation: () => ({ t }) };
});
vi.mock("@auth", () => ({
  useNachetAuth: () => ({
    isAuthenticated: true,
    isLoading: false,
    activeAccount: { userId: "user" },
    accounts: [],
  }),
}));
vi.mock("@hooks", () => ({
  useBackendUrl: () => "https://example.test",
  useDecoderTiff: () => null,
  useDeviceData: () => ({ devicesData: null }),
  useWebcamDevices: () => undefined,
  useModelMetadata: () => ({ metadata: [], selectedModel: "pipeline" }),
}));
vi.mock("@components/common/ToastNotification", () => ({
  ToastNotification: () => null,
}));
vi.mock("@components/body", () =>
  Object.fromEntries(
    [
      "DirectoryPopup",
      "BatchUploadPopup",
      "AuthPopup",
      "UploadPopup",
      "CreativeCommonsPopup",
      "SaveCapturePopup",
      "ModelPopup",
      "SwitchDevicePopup",
      "SampleMetadataPopup",
      "ImageMetadataPopup",
      "ClassificationResults",
      "ImageCache",
      "StorageDirectory",
      "MicroscopeFeed",
      "RegistrationStatusPopup",
      "NotificationLogPopup",
    ].map((name) => [name, () => null]),
  ),
);
vi.mock("@common", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@common")>()),
  checkUserRegistration: vi.fn().mockResolvedValue({ isRegistered: true }),
  readAzureStorageDir: vi.fn().mockResolvedValue({ directories: [] }),
  getLabelOccurrence: vi.fn(() => ({})),
}));

beforeEach(() => {
  vi.useFakeTimers();
  useFolderStore.getState().setCurDir({
    folderId: "folder",
    folderName: "user",
    folderPrefix: "user",
    description: "",
    pictureCount: 1,
  });
  useImageStore.setState({
    images: [
      {
        index: 1,
        imageId: "image",
        src: "data:image/png;base64,AA==",
        imageDims: [10, 10],
        workflowIds: [],
        activeWorkflowId: null,
      },
    ],
    currentIndex: 1,
  });
  useWorkflowStore.getState().clearAllWorkflows();
});

afterEach(() => {
  vi.clearAllTimers();
  vi.useRealTimers();
  vi.restoreAllMocks();
});

describe("Completed workflow cleanup", () => {
  it("keeps the one-second store cleanup when Body unmounts", async () => {
    const configure = vi.spyOn(WorkflowQueueManager.prototype, "configure");
    const { unmount } = render(
      <Body
        windowSize={{ width: 1000, height: 1000 }}
        creativeCommonsPopupOpen={false}
        setCreativeCommonsPopupOpen={vi.fn()}
        handleCreativeCommonsAgreement={vi.fn()}
      />,
    );
    await act(() => Promise.resolve());

    const config = configure.mock.calls[configure.mock.calls.length - 1][0];
    const results: ApiInferenceData = {
      filename: "image.png",
      imageId: "image",
      inferenceId: "inference",
      boxes: [],
      labelOccurrence: {},
      totalBoxes: 0,
      models: [],
    };
    act(() => {
      useWorkflowStore
        .getState()
        .addWorkflow("workflow", "image", 1, "pipeline", "Pipeline");
      config.onComplete("workflow", 1, results, "pipeline", "Pipeline");
    });
    expect(useWorkflowStore.getState().getWorkflow("workflow")).toBeDefined();

    unmount();
    act(() => vi.advanceTimersByTime(999));
    expect(useWorkflowStore.getState().getWorkflow("workflow")).toBeDefined();
    act(() => vi.advanceTimersByTime(1));
    expect(useWorkflowStore.getState().getWorkflow("workflow")).toBeUndefined();
  });
});
