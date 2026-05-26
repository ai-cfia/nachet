/**
 * SAM 3 image preprocessing — TypeScript port of Sam3ImageProcessor.
 *
 * Mirrors the recipe in
 * `transformers/models/sam3/image_processing_sam3.py`:
 *
 *   1. Convert to RGB (the worker is responsible for decoding to an ImageBitmap,
 *      which is RGB by default — alpha gets discarded).
 *   2. Resize to 1008x1008 via bilinear interpolation. Note: this is a direct
 *      stretch, not aspect-preserving — `size = {height: 1008, width: 1008}`
 *      in the Python processor means "resize to exactly these dims."
 *   3. Rescale pixel values from [0, 255] to [0, 1] by dividing by 255.
 *   4. Normalize per-channel with ImageNet mean/std.
 *
 * Output shape is [1, 3, 1008, 1008] in NCHW order — channels first, batch
 * dimension prepended for ONNX consumption.
 *
 * The SAM 3 vision encoder has positional embeddings precomputed for exactly
 * 1008x1008 input. Other sizes produce shape mismatches in the rotary
 * embeddings — so this size is non-negotiable.
 */

/** Target spatial size — matches `size["height"/"width"]` in Sam3ImageProcessor. */
export const SAM3_IMAGE_SIZE = 1008;

/** ImageNet standard mean (RGB), divided by 255 to match the [0, 1] rescaled range. */
export const SAM3_IMAGE_MEAN: readonly number[] = [0.485, 0.456, 0.406];

/** ImageNet standard std (RGB), divided by 255 to match the [0, 1] rescaled range. */
export const SAM3_IMAGE_STD: readonly number[] = [0.229, 0.224, 0.225];

/**
 * Number of channels in the output tensor (R, G, B). Alpha is dropped.
 */
const N_CHANNELS = 3;

/**
 * Element count of the output Float32Array.
 * 1 batch * 3 channels * 1008 * 1008 = 3,048,192 elements (~11.6 MB at fp32).
 */
export const SAM3_PIXEL_TENSOR_LENGTH =
  1 * N_CHANNELS * SAM3_IMAGE_SIZE * SAM3_IMAGE_SIZE;

/** Logical shape of the output, for callers that build ONNX tensors from it. */
export const SAM3_PIXEL_TENSOR_SHAPE: readonly number[] = [
  1,
  N_CHANNELS,
  SAM3_IMAGE_SIZE,
  SAM3_IMAGE_SIZE,
];

/**
 * Preprocess an image into the SAM 3 vision encoder's expected input tensor.
 *
 * @param source Anything `OffscreenCanvas.getContext("2d").drawImage()`
 *   accepts: an HTMLImageElement, ImageBitmap, HTMLCanvasElement, or even
 *   another OffscreenCanvas. Workers should call `createImageBitmap()` from a
 *   blob/data URL before invoking this.
 * @returns Float32Array of length 3,048,192, NCHW-ordered, ready to wrap in an
 *   `ort.Tensor("float32", arr, [1, 3, 1008, 1008])`.
 */
export const preprocessImageForSam3 = (
  source: CanvasImageSource,
): Float32Array => {
  // Step 1+2: resize to 1008x1008 via a stretched draw on an offscreen canvas.
  // The canvas does bilinear filtering by default (we set imageSmoothingEnabled
  // explicitly to make it portable across browsers — Safari has historically
  // defaulted it to false on some platforms).
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

  // Read back the resized image. ImageData is always RGBA, [0, 255] uint8,
  // ordered as [r0, g0, b0, a0, r1, g1, b1, a1, ...] — i.e. HWC with alpha.
  const imageData = ctx.getImageData(
    0,
    0,
    SAM3_IMAGE_SIZE,
    SAM3_IMAGE_SIZE,
  );
  const src = imageData.data;

  // Step 3+4: rescale and normalize, while reordering HWC → CHW.
  //
  // We pre-compute the per-channel transform:
  //   normalized = (pixel/255 - mean) / std
  //               = pixel * (1/(255*std)) - mean/std
  //               = pixel * scale + offset
  //
  // Doing it as `pixel * scale + offset` is one FMA per element instead of
  // a divide + two ops per element.
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

  // Single pass: for each pixel i, write its 3 channels to the corresponding
  // positions of the 3 output planes. RGBA is interleaved (stride 4) in src;
  // out is planar (channel-major).
  for (let i = 0; i < planeSize; i++) {
    const srcIdx = i * 4; // skip alpha
    out[i] = src[srcIdx] * scale[0] + offset[0]; // R plane
    out[planeSize + i] = src[srcIdx + 1] * scale[1] + offset[1]; // G plane
    out[2 * planeSize + i] = src[srcIdx + 2] * scale[2] + offset[2]; // B plane
  }

  return out;
};
