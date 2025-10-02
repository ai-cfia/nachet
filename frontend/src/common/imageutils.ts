import { BoxCSS, BoxCoordinates } from "./types";

interface ImageValidationResult {
  isValid: boolean;
  errors: string[];
  dimensions?: {
    width: number;
    height: number;
  };
}

/**
 * Validates an image file for MIME type (PNG), file size (max 10MB), and dimensions (max 1920x1080)
 * @param file - The file to validate
 * @returns Promise with validation result
 */
export const validateImageFile = async (
  file: File,
): Promise<ImageValidationResult> => {
  const errors: string[] = [];

  // Check MIME type
  if (file.type !== "image/png") {
    errors.push("File must be a PNG image");
  }

  // Check file size (10MB = 10 * 1024 * 1024 bytes)
  const maxSize = 10 * 1024 * 1024;
  if (file.size > maxSize) {
    errors.push("File size must be less than 10MB");
  }

  // Check image dimensions
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
 * @param file - The image file
 * @returns Promise with width and height
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
  const scaledWidth = (box.bottomX - box.topX) * scaleFactorWidth;
  const scaledHeight = (box.bottomY - box.topY) * scaleFactorHeight;
  const scaledTopX = box.topX * scaleFactorWidth;
  const scaledTopY = box.topY * scaleFactorHeight;
  return {
    scaledWidth,
    scaledHeight,
    scaledTopX,
    scaledTopY,
  };
};

export const getUnscaledCoordinates = (
  containerWidth: number,
  containerHeight: number,
  itemWidth: number,
  itemHeight: number,
  box: BoxCSS,
): BoxCoordinates => {
  const scaleFactorWidth = itemWidth / containerWidth;
  const scaleFactorHeight = itemHeight / containerHeight;
  const topX = box.left * scaleFactorWidth;
  const topY = box.top * scaleFactorHeight;
  const bottomX = (box.left + box.minWidth) * scaleFactorWidth;
  const bottomY = (box.top + box.minHeight) * scaleFactorHeight;
  return {
    topX,
    topY,
    bottomX,
    bottomY,
  };
};
