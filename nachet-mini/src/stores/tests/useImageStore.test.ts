import { describe, it, expect, beforeEach } from "vitest";
import { useImageStore } from "../useImageStore";
import { useMetadataDefaultsStore } from "../useMetadataDefaultsStore";
import type { ImageMetadata } from "@common/types";

const defaultDefaults = {
  namePrefix: "image",
  deviceBrandId: "",
  deviceModelId: "",
  deviceLensId: "",
  trayCode: "" as const,
  description: "",
};

const defaultMeta: ImageMetadata = {
  imageName: "image-0001.png",
  deviceBrandId: "",
  deviceModelId: "",
  deviceLensId: "",
  trayCode: "",
  description: "",
};

describe("useImageStore", () => {
  beforeEach(() => {
    useImageStore.setState({ images: [], currentIndex: 0 });
    useMetadataDefaultsStore.setState({ defaults: { ...defaultDefaults } });
  });

  it("has correct initial state", () => {
    const { images, currentIndex } = useImageStore.getState();
    expect(images).toEqual([]);
    expect(currentIndex).toBe(0);
  });

  describe("addImage", () => {
    it("adds the first image with index 0 and returns true", () => {
      const added = useImageStore
        .getState()
        .addImage("data:image/png;base64,abc", [640, 480]);
      expect(added).toBe(true);
      const { images, currentIndex } = useImageStore.getState();
      expect(images).toHaveLength(1);
      expect(images[0].index).toBe(0);
      expect(currentIndex).toBe(0);
    });

    it("auto-generates name from prefix and 1-based padded index", () => {
      useImageStore.getState().addImage("src", [100, 100]);
      expect(useImageStore.getState().images[0].metadata.imageName).toBe(
        "image-0001.png",
      );
    });

    it("uses a custom name when provided", () => {
      useImageStore.getState().addImage("src", [100, 100], "my-photo.jpg");
      expect(useImageStore.getState().images[0].metadata.imageName).toBe(
        "my-photo.jpg",
      );
    });

    it("assigns sequential indices to multiple images", () => {
      useImageStore.getState().addImage("src0", [100, 100]);
      useImageStore.getState().addImage("src1", [200, 200]);
      useImageStore.getState().addImage("src2", [300, 300]);
      expect(useImageStore.getState().images.map((img) => img.index)).toEqual([
        0, 1, 2,
      ]);
    });

    it("generates names based on next index (not array length)", () => {
      useImageStore.getState().addImage("src0", [100, 100]);
      useImageStore.getState().addImage("src1", [100, 100]);
      expect(useImageStore.getState().images[1].metadata.imageName).toBe(
        "image-0002.png",
      );
    });

    it("applies metadata from MetadataDefaultsStore", () => {
      useMetadataDefaultsStore.setState({
        defaults: {
          ...defaultDefaults,
          namePrefix: "seed",
          deviceBrandId: "brand-1",
          description: "scan",
        },
      });
      useImageStore.getState().addImage("src", [100, 100]);
      const img = useImageStore.getState().images[0];
      expect(img.metadata.imageName).toBe("seed-0001.png");
      expect(img.metadata.deviceBrandId).toBe("brand-1");
      expect(img.metadata.description).toBe("scan");
    });

    it("stores sha256 and imageDims", () => {
      useImageStore
        .getState()
        .addImage("src", [640, 480], undefined, "deadbeef");
      const img = useImageStore.getState().images[0];
      expect(img.sha256).toBe("deadbeef");
      expect(img.imageDims).toEqual([640, 480]);
    });

    it("stores empty string for sha256 when not provided", () => {
      useImageStore.getState().addImage("src", [100, 100]);
      expect(useImageStore.getState().images[0].sha256).toBe("");
    });

    it("rejects duplicate with same sha256 and same name, returns false", () => {
      useImageStore
        .getState()
        .addImage("src1", [100, 100], "img.png", "abc123");
      const result = useImageStore
        .getState()
        .addImage("src2", [100, 100], "img.png", "abc123");
      expect(result).toBe(false);
      expect(useImageStore.getState().images).toHaveLength(1);
    });

    it("allows same sha256 with a different name", () => {
      useImageStore
        .getState()
        .addImage("src1", [100, 100], "img-a.png", "abc123");
      const result = useImageStore
        .getState()
        .addImage("src2", [100, 100], "img-b.png", "abc123");
      expect(result).toBe(true);
      expect(useImageStore.getState().images).toHaveLength(2);
    });

    it("allows same name with a different sha256", () => {
      useImageStore.getState().addImage("src1", [100, 100], "img.png", "hash1");
      const result = useImageStore
        .getState()
        .addImage("src2", [100, 100], "img.png", "hash2");
      expect(result).toBe(true);
    });

    it("skips duplicate check entirely when sha256 is not provided", () => {
      useImageStore.getState().addImage("src1", [100, 100], "img.png");
      const result = useImageStore
        .getState()
        .addImage("src2", [100, 100], "img.png");
      expect(result).toBe(true);
      expect(useImageStore.getState().images).toHaveLength(2);
    });

    it("sets src on the stored image", () => {
      useImageStore
        .getState()
        .addImage("data:image/png;base64,XYZ", [100, 100]);
      expect(useImageStore.getState().images[0].src).toBe(
        "data:image/png;base64,XYZ",
      );
    });
  });

  describe("removeImage", () => {
    it("removes the image matching the given index", () => {
      useImageStore.getState().addImage("src0", [100, 100]);
      useImageStore.getState().addImage("src1", [100, 100]);
      useImageStore.getState().removeImage(0);
      expect(useImageStore.getState().images).toHaveLength(1);
      expect(useImageStore.getState().images[0].index).toBe(1);
    });

    it("switches currentIndex to first remaining index when removing the current image", () => {
      useImageStore.getState().addImage("src0", [100, 100]);
      useImageStore.getState().addImage("src1", [100, 100]);
      useImageStore.getState().addImage("src2", [100, 100]);
      // after 3 adds, currentIndex = 2
      useImageStore.getState().removeImage(2);
      // remaining indices: [0, 1] → first sorted = 0
      expect(useImageStore.getState().currentIndex).toBe(0);
    });

    it("preserves currentIndex when removing a non-current image", () => {
      useImageStore.getState().addImage("src0", [100, 100]);
      useImageStore.getState().addImage("src1", [100, 100]);
      useImageStore.getState().addImage("src2", [100, 100]);
      // currentIndex = 2 after 3 adds; remove index 0 (non-current)
      useImageStore.getState().removeImage(0);
      expect(useImageStore.getState().currentIndex).toBe(2);
    });

    it("resets currentIndex to 0 when removing the last image", () => {
      useImageStore.getState().addImage("src0", [100, 100]);
      useImageStore.getState().removeImage(0);
      expect(useImageStore.getState().images).toHaveLength(0);
      expect(useImageStore.getState().currentIndex).toBe(0);
    });

    it("picks first sorted remaining index when removing mid-image with currentIndex above it", () => {
      useImageStore.getState().addImage("src0", [100, 100]);
      useImageStore.getState().addImage("src1", [100, 100]);
      useImageStore.getState().addImage("src2", [100, 100]);
      useImageStore.setState({ currentIndex: 1 });
      useImageStore.getState().removeImage(1);
      // remaining: indices [0, 2], first sorted = 0
      expect(useImageStore.getState().currentIndex).toBe(0);
    });
  });

  describe("setCurrentIndex", () => {
    it("updates currentIndex", () => {
      useImageStore.getState().setCurrentIndex(7);
      expect(useImageStore.getState().currentIndex).toBe(7);
    });
  });

  describe("clearImages", () => {
    it("empties images array and resets currentIndex to 0", () => {
      useImageStore.getState().addImage("src0", [100, 100]);
      useImageStore.getState().addImage("src1", [100, 100]);
      useImageStore.getState().clearImages();
      expect(useImageStore.getState().images).toEqual([]);
      expect(useImageStore.getState().currentIndex).toBe(0);
    });
  });

  describe("getCurrentImage", () => {
    it("returns the image matching currentIndex", () => {
      useImageStore.getState().addImage("src0", [100, 100]);
      useImageStore.getState().addImage("src1", [200, 200]);
      // currentIndex = 1 after second add
      const img = useImageStore.getState().getCurrentImage();
      expect(img?.index).toBe(1);
      expect(img?.src).toBe("src1");
    });

    it("returns undefined when no images exist", () => {
      expect(useImageStore.getState().getCurrentImage()).toBeUndefined();
    });

    it("returns the correct image after currentIndex changes", () => {
      useImageStore.getState().addImage("src0", [100, 100]);
      useImageStore.getState().addImage("src1", [200, 200]);
      useImageStore.getState().setCurrentIndex(0);
      expect(useImageStore.getState().getCurrentImage()?.src).toBe("src0");
    });
  });

  describe("updateImageMetadata", () => {
    it("updates metadata for the image at the given index", () => {
      useImageStore.getState().addImage("src0", [100, 100]);
      const newMeta: ImageMetadata = {
        ...defaultMeta,
        imageName: "updated.png",
        description: "new",
      };
      useImageStore.getState().updateImageMetadata(0, newMeta);
      expect(useImageStore.getState().images[0].metadata).toEqual(newMeta);
    });

    it("does not affect other images", () => {
      useImageStore.getState().addImage("src0", [100, 100]);
      useImageStore.getState().addImage("src1", [100, 100]);
      const original1Meta = { ...useImageStore.getState().images[1].metadata };
      useImageStore
        .getState()
        .updateImageMetadata(0, { ...defaultMeta, description: "changed" });
      expect(useImageStore.getState().images[1].metadata).toEqual(
        original1Meta,
      );
    });
  });

  describe("updateImageHash", () => {
    it("updates sha256 for the image at the given index", () => {
      useImageStore.getState().addImage("src0", [100, 100]);
      useImageStore.getState().updateImageHash(0, "newhash");
      expect(useImageStore.getState().images[0].sha256).toBe("newhash");
    });

    it("does not affect other images", () => {
      useImageStore.getState().addImage("src0", [100, 100]);
      useImageStore
        .getState()
        .addImage("src1", [100, 100], undefined, "original");
      useImageStore.getState().updateImageHash(0, "changed");
      expect(useImageStore.getState().images[1].sha256).toBe("original");
    });
  });
});
