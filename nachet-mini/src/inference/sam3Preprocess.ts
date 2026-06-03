/**
 * SAM 3 image preprocessing — TypeScript port of Sam3ImageProcessor.
 *
 * Resizes to 1008x1008 via bilinear (stretched, not aspect-preserved — the
 * vision encoder's positional embeddings are precomputed for exactly this
 * size), rescales [0, 255] → [0, 1], normalizes with ImageNet mean/std,
 * and reorders HWC → NCHW for ONNX consumption.
 */

/** Target spatial size — non-negotiable; positional embeddings are baked for it. */
export const SAM3_IMAGE_SIZE = 1008;

/** ImageNet normalization constants in [0, 1] scale. */
export const SAM3_IMAGE_MEAN: readonly number[] = [0.485, 0.456, 0.406];
export const SAM3_IMAGE_STD: readonly number[] = [0.229, 0.224, 0.225];

const N_CHANNELS = 3;

/** Element count of the output Float32Array (1 × 3 × 1008 × 1008 = 3,048,192). */
export const SAM3_PIXEL_TENSOR_LENGTH =
  1 * N_CHANNELS * SAM3_IMAGE_SIZE * SAM3_IMAGE_SIZE;

/** Output tensor shape [batch, channels, H, W] for ort.Tensor construction. */
export const SAM3_PIXEL_TENSOR_SHAPE: readonly number[] = [
  1,
  N_CHANNELS,
  SAM3_IMAGE_SIZE,
  SAM3_IMAGE_SIZE,
];

/**
 * Preprocess an image into SAM 3's vision encoder input tensor.
 * Returns NCHW Float32Array ready to wrap in an ort.Tensor.
 */
export const preprocessImageForSam3 = (
  source: CanvasImageSource,
): Float32Array => {
  // Resize to 1008x1008 via a stretched draw. Set imageSmoothingEnabled
  // explicitly for Safari, which has defaulted it to false on some platforms.
  const canvas = new OffscreenCanvas(SAM3_IMAGE_SIZE, SAM3_IMAGE_SIZE);
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  if (!ctx) {
    throw new Error(
      "Failed to acquire 2D context on OffscreenCanvas for SAM 3 preprocessing.",
    );
  }
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = "high";
  ctx.drawImage(source, 0, 0, SAM3_IMAGE_SIZE, SAM3_IMAGE_SIZE);

  // ImageData is always RGBA [0, 255] uint8, HWC-ordered.
  const imageData = ctx.getImageData(0, 0, SAM3_IMAGE_SIZE, SAM3_IMAGE_SIZE);
  const src = imageData.data;

  // Pre-compute per-channel transform so the inner loop is one FMA per element:
  //   normalized = pixel * (1/(255*std)) + (-mean/std)
  const scale = [
    1 / (255 * SAM3_IMAGE_STD[0]),
    1 / (255 * SAM3_IMAGE_STD[1]),
    1 / (255 * SAM3_IMAGE_STD[2]),
  ];
  const offset = [
    -SAM3_IMAGE_MEAN[0] / SAM3_IMAGE_STD[0],
    -SAM3_IMAGE_MEAN[1] / SAM3_IMAGE_STD[1],
    -SAM3_IMAGE_MEAN[2] / SAM3_IMAGE_STD[2],
  ];

  const planeSize = SAM3_IMAGE_SIZE * SAM3_IMAGE_SIZE;
  const out = new Float32Array(SAM3_PIXEL_TENSOR_LENGTH);

  // Single pass HWC → CHW: src is interleaved (stride 4), out is planar.
  for (let i = 0; i < planeSize; i++) {
    const srcIdx = i * 4; // skip alpha
    out[i] = src[srcIdx] * scale[0] + offset[0]; // R plane
    out[planeSize + i] = src[srcIdx + 1] * scale[1] + offset[1]; // G plane
    out[2 * planeSize + i] = src[srcIdx + 2] * scale[2] + offset[2]; // B plane
  }

  return out;
};
