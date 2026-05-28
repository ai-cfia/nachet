import type { BoxCoordinates } from "./types";

/**
 * Converts display (mouse) coordinates back to original image-space coordinates.
 * Reverse of getScaledBounds() — accounts for objectFit: "contain" letterboxing.
 */
export const getUnscaledCoordinates = (
  containerWidth: number,
  containerHeight: number,
  itemWidth: number,
  itemHeight: number,
  displayX: number,
  displayY: number,
): { imageX: number; imageY: number } => {
  const scaleFactorWidth = containerWidth / itemWidth;
  const scaleFactorHeight = containerHeight / itemHeight;
  const scaleFactor = Math.min(scaleFactorWidth, scaleFactorHeight);

  if (
    !isFinite(scaleFactor) ||
    scaleFactor === 0 ||
    isNaN(scaleFactor) ||
    itemWidth === 0 ||
    itemHeight === 0
  ) {
    return { imageX: 0, imageY: 0 };
  }

  const displayedWidth = itemWidth * scaleFactor;
  const displayedHeight = itemHeight * scaleFactor;
  const offsetX = (containerWidth - displayedWidth) / 2;
  const offsetY = (containerHeight - displayedHeight) / 2;

  return {
    imageX: (displayX - offsetX) / scaleFactor,
    imageY: (displayY - offsetY) / scaleFactor,
  };
};

interface ImageValidationResult {
  isValid: boolean;
  errorKeys: string[];
  dimensions?: {
    width: number;
    height: number;
  };
}

const MAX_IMAGE_WIDTH = 8000;
const MAX_IMAGE_HEIGHT = 8000;

/**
 * Validates an image file for MIME type (PNG or JPEG), file size (max 10MB), and dimensions (max 8000x8000)
 */
export const validateImageFile = async (
  file: File,
): Promise<ImageValidationResult> => {
  const errorKeys: string[] = [];

  // Accept PNG and JPEG (broader format support for demos)
  if (file.type !== "image/png" && file.type !== "image/jpeg") {
    errorKeys.push("invalidType");
  }

  const maxSize = 10 * 1024 * 1024;
  if (file.size > maxSize) {
    errorKeys.push("fileTooLarge");
  }

  try {
    const dimensions = await getImageDimensions(file);

    if (
      dimensions.width > MAX_IMAGE_WIDTH ||
      dimensions.height > MAX_IMAGE_HEIGHT
    ) {
      errorKeys.push("dimensionsTooLarge");
    }

    return {
      isValid: errorKeys.length === 0,
      errorKeys,
      dimensions,
    };
  } catch (error) {
    errorKeys.push("unreadableDimensions");
    console.error("Error getting image dimensions:", error);
    return {
      isValid: false,
      errorKeys,
    };
  }
};

/**
 * Gets the dimensions of an image file
 */
export const getImageDimensions = (
  file: File,
): Promise<{ width: number; height: number }> => {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const objectUrl = URL.createObjectURL(file);

    img.onload = () => {
      URL.revokeObjectURL(objectUrl);
      resolve({
        width: img.naturalWidth,
        height: img.naturalHeight,
      });
    };

    img.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      reject(new Error("Failed to load image"));
    };

    img.src = objectUrl;
  });
};

/**
 * Computes scaled bounding box coordinates for objectFit: "contain" display.
 * Accounts for letterboxing/pillarboxing offsets.
 */
export const getScaledBounds = (
  containerWidth: number,
  containerHeight: number,
  itemWidth: number,
  itemHeight: number,
  box: BoxCoordinates,
): {
  scaledWidth: number;
  scaledHeight: number;
  scaledTopX: number;
  scaledTopY: number;
} => {
  const scaleFactorWidth = containerWidth / itemWidth;
  const scaleFactorHeight = containerHeight / itemHeight;
  const scaleFactor = Math.min(scaleFactorWidth, scaleFactorHeight);

  if (
    !isFinite(scaleFactor) ||
    scaleFactor === 0 ||
    isNaN(scaleFactor) ||
    itemWidth === 0 ||
    itemHeight === 0
  ) {
    console.error("Invalid scale factor or dimensions!", {
      scaleFactor,
      itemWidth,
      itemHeight,
    });
    return {
      scaledWidth: 0,
      scaledHeight: 0,
      scaledTopX: 0,
      scaledTopY: 0,
    };
  }

  const displayedWidth = itemWidth * scaleFactor;
  const displayedHeight = itemHeight * scaleFactor;
  const offsetX = (containerWidth - displayedWidth) / 2;
  const offsetY = (containerHeight - displayedHeight) / 2;

  return {
    scaledWidth: (box.bottomX - box.topX) * scaleFactor,
    scaledHeight: (box.bottomY - box.topY) * scaleFactor,
    scaledTopX: box.topX * scaleFactor + offsetX,
    scaledTopY: box.topY * scaleFactor + offsetY,
  };
};
