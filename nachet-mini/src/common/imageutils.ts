import type { BoxCoordinates } from "./types";

interface ImageValidationResult {
  isValid: boolean;
  errors: string[];
  dimensions?: {
    width: number;
    height: number;
  };
}

/**
 * Validates an image file for MIME type (PNG or JPEG), file size (max 10MB), and dimensions (max 1920x1080)
 */
export const validateImageFile = async (
  file: File,
): Promise<ImageValidationResult> => {
  const errors: string[] = [];

  // Accept PNG and JPEG (broader format support for demos)
  if (file.type !== "image/png" && file.type !== "image/jpeg") {
    errors.push("File must be a PNG or JPEG image");
  }

  const maxSize = 10 * 1024 * 1024;
  if (file.size > maxSize) {
    errors.push("File size must be less than 10MB");
  }

  try {
    const dimensions = await getImageDimensions(file);

    if (dimensions.width > 1920 || dimensions.height > 1080) {
      errors.push("Image dimensions must not exceed 1920x1080 pixels");
    }

    return {
      isValid: errors.length === 0,
      errors,
      dimensions,
    };
  } catch (error) {
    errors.push("Unable to read image dimensions");
    console.error("Error getting image dimensions:", error);
    return {
      isValid: false,
      errors,
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
