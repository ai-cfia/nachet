import { describe, it, expect, beforeEach, vi } from "vitest";
import { act } from "@testing-library/react";
import { useImageStore } from "../useImageStore";
import { useDeviceStore } from "../useDeviceStore";
import * as cacheutils from "@common/cacheutils";
import { createMockImageData } from "./testUtils";
import type { Images } from "@common/types";

// Mock the cacheutils module
vi.mock("@common/cacheutils", async () => {
  const actual =
    await vi.importActual<typeof import("@common/cacheutils")>(
      "@common/cacheutils",
    );
  return {
    ...actual,
    loadCaptureToCache: vi.fn(),
    nextCacheIndex: vi.fn(),
  };
});

// Mock the device store
vi.mock("../useDeviceStore", () => ({
  useDeviceStore: {
    getState: vi.fn(() => ({
      deviceSelection: {
        selectedBrandId: null,
        selectedModelId: null,
        selectedLensId: null,
      },
      sampleMetadata: {
        trayCode: "",
        magnification: 0,
        sampleIdPrefix: "",
        sampleDescription: "",
      },
    })),
  },
}));

describe("useImageStore", () => {
  beforeEach(() => {
    // Reset store to initial state
    act(() => {
      useImageStore.setState({
        images: [],
        currentIndex: 0,
      });
    });

    // Reset all mocks
    vi.clearAllMocks();
  });

  describe("Initial State", () => {
    it("should have empty images array and currentIndex 0", () => {
      const { images, currentIndex } = useImageStore.getState();
      expect(images).toEqual([]);
      expect(currentIndex).toBe(0);
    });
  });

  describe("addCapturedImage", () => {
    it("should add image to cache and update state", async () => {
      const mockImage = createMockImageData({ index: 0 });
      const mockNextIndex = 0;
      const mockNewImages = [mockImage];

      vi.mocked(cacheutils.nextCacheIndex).mockReturnValue(mockNextIndex);
      vi.mocked(cacheutils.loadCaptureToCache).mockResolvedValue(mockNewImages);

      await act(async () => {
        await useImageStore
          .getState()
          .addCapturedImage("data:image/png;base64,test");
      });

      expect(cacheutils.nextCacheIndex).toHaveBeenCalledWith(0, []);
      expect(cacheutils.loadCaptureToCache).toHaveBeenCalled();

      const { images, currentIndex } = useImageStore.getState();
      expect(images).toEqual(mockNewImages);
      expect(currentIndex).toBe(mockNextIndex);
    });

    it("should include device metadata when available", async () => {
      const mockDeviceState = {
        deviceSelection: {
          selectedBrandId: "brand-1",
          selectedModelId: "model-1",
          selectedLensId: "lens-1",
        },
        sampleMetadata: {
          trayCode: "TRAY-001",
          magnification: 40,
          sampleIdPrefix: "SAMPLE",
          sampleDescription: "Test sample",
        },
      };

      vi.mocked(useDeviceStore.getState).mockReturnValue(
        mockDeviceState as never,
      );
      vi.mocked(cacheutils.nextCacheIndex).mockReturnValue(0);
      vi.mocked(cacheutils.loadCaptureToCache).mockResolvedValue([
        createMockImageData(),
      ]);

      await act(async () => {
        await useImageStore
          .getState()
          .addCapturedImage("data:image/png;base64,test");
      });

      const loadCaptureCall = vi.mocked(cacheutils.loadCaptureToCache).mock
        .calls[0];
      const metadata = loadCaptureCall[3]; // 4th argument is metadata

      expect(metadata).toEqual({
        deviceBrandId: "brand-1",
        deviceModelId: "model-1",
        deviceLensId: "lens-1",
        trayCode: "TRAY-001",
        magnification: 40,
        sampleIdPrefix: "SAMPLE",
        imageDescription: "Test sample",
      });
    });

    it("should exclude empty metadata fields", async () => {
      const mockDeviceState = {
        deviceSelection: {
          selectedBrandId: "brand-1",
          selectedModelId: null,
          selectedLensId: null,
        },
        sampleMetadata: {
          trayCode: "",
          magnification: 0,
          sampleIdPrefix: "",
          sampleDescription: "",
        },
      };

      vi.mocked(useDeviceStore.getState).mockReturnValue(
        mockDeviceState as never,
      );
      vi.mocked(cacheutils.nextCacheIndex).mockReturnValue(0);
      vi.mocked(cacheutils.loadCaptureToCache).mockResolvedValue([
        createMockImageData(),
      ]);

      await act(async () => {
        await useImageStore
          .getState()
          .addCapturedImage("data:image/png;base64,test");
      });

      const loadCaptureCall = vi.mocked(cacheutils.loadCaptureToCache).mock
        .calls[0];
      const metadata = loadCaptureCall[3];

      expect(metadata).toEqual({
        deviceBrandId: "brand-1",
      });
    });
  });

  describe("Workflow Management", () => {
    beforeEach(() => {
      act(() => {
        useImageStore.setState({
          images: [
            createMockImageData({ index: 0, workflowIds: [] }),
            createMockImageData({ index: 1, workflowIds: [] }),
          ],
          currentIndex: 0,
        });
      });
    });

    it("should add workflow to image", () => {
      act(() => {
        useImageStore.getState().addWorkflowToImage(0, "workflow-123");
      });

      const { images } = useImageStore.getState();
      expect(images[0].workflowIds).toContain("workflow-123");
      expect(images[0].activeWorkflowId).toBe("workflow-123");
    });

    it("should add workflow without setting as active", () => {
      act(() => {
        useImageStore.getState().addWorkflowToImage(0, "workflow-123", false);
      });

      const { images } = useImageStore.getState();
      expect(images[0].workflowIds).toContain("workflow-123");
      expect(images[0].activeWorkflowId).toBeNull();
    });

    it("should add multiple workflows to same image", () => {
      act(() => {
        useImageStore.getState().addWorkflowToImage(0, "workflow-1");
        useImageStore.getState().addWorkflowToImage(0, "workflow-2");
        useImageStore.getState().addWorkflowToImage(0, "workflow-3");
      });

      const { images } = useImageStore.getState();
      expect(images[0].workflowIds).toEqual([
        "workflow-1",
        "workflow-2",
        "workflow-3",
      ]);
      expect(images[0].activeWorkflowId).toBe("workflow-3");
    });

    it("should set active workflow", () => {
      act(() => {
        useImageStore.setState({
          images: [
            createMockImageData({
              index: 0,
              workflowIds: ["workflow-1", "workflow-2"],
              activeWorkflowId: "workflow-1",
            }),
          ],
        });
      });

      act(() => {
        useImageStore.getState().setActiveWorkflow(0, "workflow-2");
      });

      const { images } = useImageStore.getState();
      expect(images[0].activeWorkflowId).toBe("workflow-2");
    });

    it("should not affect other images when adding workflow", () => {
      act(() => {
        useImageStore.getState().addWorkflowToImage(0, "workflow-123");
      });

      const { images } = useImageStore.getState();
      expect(images[1].workflowIds).toEqual([]);
    });
  });

  describe("Image Removal", () => {
    beforeEach(() => {
      act(() => {
        useImageStore.setState({
          images: [
            createMockImageData({ index: 0 }),
            createMockImageData({ index: 1 }),
            createMockImageData({ index: 2 }),
          ],
          currentIndex: 1,
        });
      });
    });

    it("should remove image by index", () => {
      let nextIndex: number;

      act(() => {
        nextIndex = useImageStore.getState().removeImage(1);
      });

      const { images } = useImageStore.getState();
      expect(images).toHaveLength(2);
      expect(images.find((img) => img.index === 1)).toBeUndefined();
      expect(nextIndex!).toBe(0); // Should default to first available
    });

    it("should update currentIndex when removing current image", () => {
      act(() => {
        useImageStore.getState().removeImage(1);
      });

      const { currentIndex } = useImageStore.getState();
      expect(currentIndex).toBe(0);
    });

    it("should keep currentIndex when removing other image", () => {
      act(() => {
        useImageStore.getState().removeImage(0);
      });

      const { currentIndex } = useImageStore.getState();
      expect(currentIndex).toBe(1); // Current was 1, should stay 1
    });

    it("should handle removing last image", () => {
      act(() => {
        useImageStore.getState().removeImage(0);
        useImageStore.getState().removeImage(1);
        useImageStore.getState().removeImage(2);
      });

      const { images, currentIndex } = useImageStore.getState();
      expect(images).toHaveLength(0);
      expect(currentIndex).toBe(0);
    });
  });

  describe("Image Management", () => {
    it("should clear all images", () => {
      act(() => {
        useImageStore.setState({
          images: [
            createMockImageData({ index: 0 }),
            createMockImageData({ index: 1 }),
          ],
          currentIndex: 1,
        });
      });

      act(() => {
        useImageStore.getState().clearImages();
      });

      const { images, currentIndex } = useImageStore.getState();
      expect(images).toEqual([]);
      expect(currentIndex).toBe(0);
    });

    it("should set images array", () => {
      const newImages: Images[] = [
        createMockImageData({ index: 0 }),
        createMockImageData({ index: 5 }),
      ];

      act(() => {
        useImageStore.getState().setImages(newImages);
      });

      const { images } = useImageStore.getState();
      expect(images).toEqual(newImages);
    });

    it("should set current index", () => {
      act(() => {
        useImageStore.getState().setCurrentIndex(5);
      });

      const { currentIndex } = useImageStore.getState();
      expect(currentIndex).toBe(5);
    });

    it("should get current image", () => {
      const testImages: Images[] = [
        createMockImageData({ index: 0 }),
        createMockImageData({ index: 1, imageName: "current.jpg" }),
        createMockImageData({ index: 2 }),
      ];

      act(() => {
        useImageStore.setState({
          images: testImages,
          currentIndex: 1,
        });
      });

      const currentImage = useImageStore.getState().getCurrentImage();
      expect(currentImage).toBeDefined();
      expect(currentImage?.index).toBe(1);
      expect(currentImage?.imageName).toBe("current.jpg");
    });

    it("should return undefined when no current image", () => {
      const currentImage = useImageStore.getState().getCurrentImage();
      expect(currentImage).toBeUndefined();
    });
  });

  describe("Image ID Management", () => {
    beforeEach(() => {
      act(() => {
        useImageStore.setState({
          images: [
            createMockImageData({ index: 0, imageId: "img-100" }),
            createMockImageData({ index: 1, imageId: "img-200" }),
          ],
          currentIndex: 0,
        });
      });
    });

    it("should get image index by imageId", () => {
      const index = useImageStore.getState().getImageIndexByImageId("img-200");
      expect(index).toBe(1);
    });

    it("should handle imageId type conversion", () => {
      const index1 = useImageStore.getState().getImageIndexByImageId("img-100");

      expect(index1).toBe(0);
    });

    it("should return undefined for non-existent imageId", () => {
      const index = useImageStore
        .getState()
        .getImageIndexByImageId("non-existent");
      expect(index).toBeUndefined();
    });

    it("should set imageId for image", () => {
      act(() => {
        useImageStore.getState().setImageId(0, "new-id-123");
      });

      const { images } = useImageStore.getState();
      expect(images[0].imageId).toBe("new-id-123");
    });

    it("should not affect other images when setting imageId", () => {
      act(() => {
        useImageStore.getState().setImageId(0, "new-id-123");
      });

      const { images } = useImageStore.getState();
      expect(images[1].imageId).toBe("img-200");
    });
  });

  describe("Metadata Updates", () => {
    beforeEach(() => {
      act(() => {
        useImageStore.setState({
          images: [
            createMockImageData({ index: 0 }),
            createMockImageData({ index: 1 }),
          ],
          currentIndex: 0,
        });
      });
    });

    it("should update image name", () => {
      act(() => {
        useImageStore.getState().updateImageMetadata(0, {
          imageName: "updated-name.jpg",
        });
      });

      const { images } = useImageStore.getState();
      expect(images[0].imageName).toBe("updated-name.jpg");
    });

    it("should update image description", () => {
      act(() => {
        useImageStore.getState().updateImageMetadata(0, {
          imageDescription: "Updated description",
        });
      });

      const { images } = useImageStore.getState();
      expect(images[0].imageDescription).toBe("Updated description");
    });

    it("should update device metadata", () => {
      act(() => {
        useImageStore.getState().updateImageMetadata(0, {
          deviceBrandId: "brand-123",
          deviceModelId: "model-456",
          deviceLensId: "lens-789",
        });
      });

      const { images } = useImageStore.getState();
      expect(images[0].deviceBrandId).toBe("brand-123");
      expect(images[0].deviceModelId).toBe("model-456");
      expect(images[0].deviceLensId).toBe("lens-789");
    });

    it("should update sample metadata", () => {
      act(() => {
        useImageStore.getState().updateImageMetadata(0, {
          trayCode: "TRAY-001",
          magnification: 100,
        });
      });

      const { images } = useImageStore.getState();
      expect(images[0].trayCode).toBe("TRAY-001");
      expect(images[0].magnification).toBe(100);
    });

    it("should update multiple fields at once", () => {
      act(() => {
        useImageStore.getState().updateImageMetadata(0, {
          imageName: "complete.jpg",
          imageDescription: "Complete test",
          deviceBrandId: "brand-1",
          trayCode: "TRAY-1",
          magnification: 50,
        });
      });

      const { images } = useImageStore.getState();
      expect(images[0].imageName).toBe("complete.jpg");
      expect(images[0].imageDescription).toBe("Complete test");
      expect(images[0].deviceBrandId).toBe("brand-1");
      expect(images[0].trayCode).toBe("TRAY-1");
      expect(images[0].magnification).toBe(50);
    });

    it("should preserve other fields when updating metadata", () => {
      const originalWorkflowIds = ["workflow-1"];

      act(() => {
        useImageStore.setState({
          images: [
            createMockImageData({
              index: 0,
              workflowIds: originalWorkflowIds,
            }),
          ],
        });
      });

      act(() => {
        useImageStore.getState().updateImageMetadata(0, {
          imageName: "new-name.jpg",
        });
      });

      const { images } = useImageStore.getState();
      expect(images[0].workflowIds).toEqual(originalWorkflowIds);
    });

    it("should not affect other images", () => {
      act(() => {
        useImageStore.getState().updateImageMetadata(0, {
          imageName: "updated.jpg",
        });
      });

      const { images } = useImageStore.getState();
      expect(images[1].imageName).toBe("test-image.jpg"); // Default from mock
    });
  });

  describe("Edge Cases", () => {
    it("should handle addWorkflowToImage for non-existent image", () => {
      act(() => {
        useImageStore.getState().addWorkflowToImage(999, "workflow-123");
      });

      const { images } = useImageStore.getState();
      expect(images).toHaveLength(0);
    });

    it("should handle setActiveWorkflow for non-existent image", () => {
      act(() => {
        useImageStore.getState().setActiveWorkflow(999, "workflow-123");
      });

      const { images } = useImageStore.getState();
      expect(images).toHaveLength(0);
    });

    it("should handle setImageId for non-existent image", () => {
      act(() => {
        useImageStore.getState().setImageId(999, "new-id");
      });

      const { images } = useImageStore.getState();
      expect(images).toHaveLength(0);
    });

    it("should handle updateImageMetadata for non-existent image", () => {
      act(() => {
        useImageStore.getState().updateImageMetadata(999, {
          imageName: "test.jpg",
        });
      });

      const { images } = useImageStore.getState();
      expect(images).toHaveLength(0);
    });

    it("should handle empty images array operations", () => {
      const currentImage = useImageStore.getState().getCurrentImage();
      const imageIndex = useImageStore
        .getState()
        .getImageIndexByImageId("test");

      expect(currentImage).toBeUndefined();
      expect(imageIndex).toBeUndefined();
    });
  });
});
