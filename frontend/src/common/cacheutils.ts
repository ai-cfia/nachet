import React from "react";
import UTIF from "utif";
import { BlobError, DecodeError, FetchError, ValueError } from "@common";
import { DecodedTiff } from "../hooks/useDecoderTiff";
import { ApiInferenceData, Images, LabelOccurrences } from "./types";

export const getInferenceLabelIndex = (
  prediction: string,
  labelOccurrences: LabelOccurrences,
): number => {
  let labelIndex = 0;
  Object.keys(labelOccurrences).forEach((key, index) => {
    if (prediction === key) {
      labelIndex = index;
    }
  });
  return labelIndex;
};

const drawBoxLabel = (
  box: Images["boxes"][0],
  score: number,
  index: number,
  ctx: CanvasRenderingContext2D,
  prediction: string,
  labelOccurrences: LabelOccurrences,
  switchTable: boolean,
): void => {
  const bottomY = box.bottomY;
  const topY = box.topY;
  const bottomX = box.bottomX;
  const topX = box.topX;
  const labelIndex = getInferenceLabelIndex(prediction, labelOccurrences);
  const scorePercentage = (score * 100).toFixed(0);
  const boxMidX = (bottomX - topX) / 2 + topX;
  // check to see if label is cut off by the canvas edge, if so, move it to the bottom of the bounding box
  const xValue = boxMidX;
  let yValue = topY - 8;
  if (topY <= 40) {
    yValue = bottomY + 23;
  }
  ctx.beginPath();
  // Commented out white rectangle background for label text
  // const labelBgWidth = 90;
  // const labelBgHeight = 25;
  // ctx.fillStyle = "white";
  // ctx.fillRect(
  //   boxMidX - labelBgWidth / 2,
  //   topY - labelBgHeight,
  //   labelBgWidth,
  //   labelBgHeight - 2,
  // );
  // draw label index
  ctx.font = "bold 2.5vh Arial";
  ctx.fillStyle = "black";
  ctx.textAlign = "center";
  if (switchTable) {
    ctx.fillText(`[${labelIndex + 1}] - ${scorePercentage}%`, xValue, yValue);
  } else {
    ctx.fillText(`[${index + 1}]`, xValue, yValue);
  }
  ctx.closePath();
};

const drawBox = (
  box: Images["boxes"][0],
  ctx: CanvasRenderingContext2D,
): void => {
  const bottomY = box.bottomY;
  const topY = box.topY;
  const bottomX = box.bottomX;
  const topX = box.topX;
  ctx.beginPath();

  // draw bounding box
  ctx.lineWidth = 3;
  if (box.is_verified) {
    ctx.strokeStyle = "green";
  } else {
    ctx.strokeStyle = "red";
  }
  ctx.rect(topX, topY, bottomX - topX, bottomY - topY);
  ctx.stroke();
  ctx.closePath();
};

const drawBoxes = (
  imageData: Images,
  selectedLabel: string,
  labelOccurrences: LabelOccurrences,
  switchTable: boolean,
  canvas: HTMLCanvasElement,
  ctx: CanvasRenderingContext2D,
): void => {
  if (!imageData.annotated) {
    return;
  }
  if (imageData.classifications == null) {
    throw new ValueError("Image object is missing classifications");
  }
  if (imageData.boxes == null) {
    throw new ValueError("Image object is missing boxes");
  }
  if (imageData.scores == null) {
    throw new ValueError("Image object is missing scores");
  }
  let selectedClassifications = imageData.classifications.map(
    (prediction, index) => ({ label: prediction, index }),
  );

  if (selectedLabel !== "all") {
    selectedClassifications = imageData.classifications
      .map((prediction, index) => ({ label: prediction, index }))
      .filter((item) => item.label === selectedLabel);
  }
  selectedClassifications.forEach((prediction) => {
    drawBox(imageData.boxes[prediction.index], ctx);
  });
  selectedClassifications.forEach((prediction) => {
    drawBoxLabel(
      imageData.boxes[prediction.index],
      imageData.scores[prediction.index],
      prediction.index,
      ctx,
      prediction.label,
      labelOccurrences,
      switchTable,
    );
  });

  // capture label in bottom left
  ctx.beginPath();
  ctx.font = "bold 16px Arial";
  ctx.textAlign = "left";
  ctx.fillStyle = "red";
  ctx.fillText(
    `${imageData.imageId ? imageData.imageId : `Capture ${imageData.index}`}`,
    10,
    canvas.height - 15,
  );
  ctx.stroke();
  ctx.closePath();
};

const drawFreeformBox = (
  box: { top: number; left: number; minWidth: number; minHeight: number },
  dragEnabled: boolean,
  ctx: CanvasRenderingContext2D,
): void => {
  const boxX = box.left;
  const boxY = box.top;
  const boxWidth = box.minWidth;
  const boxHeight = box.minHeight;

  console.log("Drawing freeform box:", {
    boxX,
    boxY,
    boxWidth,
    boxHeight,
    dragEnabled,
    canvasWidth: ctx.canvas.width,
    canvasHeight: ctx.canvas.height,
  });

  // Draw green rectangle border
  ctx.strokeStyle = "green";
  ctx.lineWidth = 2;
  ctx.strokeRect(boxX, boxY, boxWidth, boxHeight);

  console.log(
    "After strokeRect - strokeStyle:",
    ctx.strokeStyle,
    "lineWidth:",
    ctx.lineWidth,
  );

  // Draw resize handles if resize is enabled (not in drag mode)
  if (!dragEnabled) {
    const HANDLE_SIZE = 10;
    ctx.fillStyle = "green";
    const handles = [
      { x: boxX, y: boxY }, // top-left
      { x: boxX + boxWidth, y: boxY }, // top-right
      { x: boxX + boxWidth, y: boxY + boxHeight }, // bottom-right
      { x: boxX, y: boxY + boxHeight }, // bottom-left
    ];

    handles.forEach((handle) => {
      ctx.fillRect(
        handle.x - HANDLE_SIZE / 2,
        handle.y - HANDLE_SIZE / 2,
        HANDLE_SIZE,
        HANDLE_SIZE,
      );
    });
  }
};

export const drawImage = async (
  canvas: HTMLCanvasElement,
  ctx: CanvasRenderingContext2D,
  imageSrc: string,
): Promise<void> => {
  const image = new Image();
  image.src = imageSrc;
  await image.decode();
  canvas.width = image.width;
  canvas.height = image.height;
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(image, 0, 0);
};

export const drawTiff = (
  canvas: HTMLCanvasElement,
  ctx: CanvasRenderingContext2D,
  decodedTiff: DecodedTiff,
): void => {
  const { rgba, width, height } = decodedTiff;
  if (width === 0 || height === 0) {
    return;
  }
  canvas.width = width;
  canvas.height = height;
  const imgd = ctx.createImageData(width, height);
  for (let i = 0; i < rgba.length; i += 1) {
    imgd.data[i] = rgba[i];
  }
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.putImageData(imgd, 0, 0);
};

export const loadToCanvas = async (
  canvasRef: React.MutableRefObject<HTMLCanvasElement | null>,
  decodedTiff: DecodedTiff,
  imageData: Images,
  selectedLabel: string,
  labelOccurrences: any,
  switchTable: boolean,
  showInference: boolean,
  freeformBox?: {
    top: number;
    left: number;
    minWidth: number;
    minHeight: number;
  } | null,
  dragEnabled?: boolean,
): Promise<void> => {
  // loads the current image to the canvas and draws the bounding boxes and labels,
  // should update whenever a change is made to the image cache or the score threshold and the selected label is changed
  const canvas: HTMLCanvasElement | null = canvasRef.current;
  if (canvas == null) {
    return;
  }
  const ctx: CanvasRenderingContext2D | null = canvas.getContext("2d");
  if (ctx == null) {
    return;
  }

  if (imageData.src.includes("image/tiff")) {
    drawTiff(canvas, ctx, decodedTiff);
  } else {
    await drawImage(canvas, ctx, imageData.src);
  }
  if (showInference) {
    drawBoxes(
      imageData,
      selectedLabel,
      labelOccurrences,
      switchTable,
      canvas,
      ctx,
    );
  }
  // Draw freeform box if provided
  console.log(
    "loadToCanvas - freeformBox:",
    freeformBox,
    "dragEnabled:",
    dragEnabled,
  );
  if (freeformBox) {
    // The scaledFeedbackBox is in display coordinates (scaled with offsets for objectFit: contain)
    // We need to reverse the scaling that was applied by getScaledBounds
    const containerWidth = canvas.getBoundingClientRect().width;
    const containerHeight = canvas.getBoundingClientRect().height;
    const imageWidth = canvas.width;
    const imageHeight = canvas.height;

    // Calculate the same scale factor used in getScaledBounds
    const scaleFactorWidth = containerWidth / imageWidth;
    const scaleFactorHeight = containerHeight / imageHeight;
    const scaleFactor = Math.min(scaleFactorWidth, scaleFactorHeight);

    // Calculate offsets for objectFit: contain
    const displayedWidth = imageWidth * scaleFactor;
    const displayedHeight = imageHeight * scaleFactor;
    const offsetX = (containerWidth - displayedWidth) / 2;
    const offsetY = (containerHeight - displayedHeight) / 2;

    console.log("Unscaling freeform box:", {
      containerWidth,
      containerHeight,
      imageWidth,
      imageHeight,
      scaleFactor,
      offsetX,
      offsetY,
      displayedWidth,
      displayedHeight,
    });

    // Reverse the transformation: remove offset, then divide by scale factor
    const unscaledBox = {
      left: (freeformBox.left - offsetX) / scaleFactor,
      top: (freeformBox.top - offsetY) / scaleFactor,
      minWidth: freeformBox.minWidth / scaleFactor,
      minHeight: freeformBox.minHeight / scaleFactor,
    };

    console.log("Unscaled box for canvas:", unscaledBox);

    drawFreeformBox(unscaledBox, dragEnabled ?? true, ctx);
  }
};

export const fetchArrayBuffer = async (
  imageSrc: string,
): Promise<ArrayBuffer> => {
  const file = await fetch(imageSrc)
    .then(async (res) => {
      if (!res.ok) {
        throw new FetchError("decodeTiff - Failed to fetch TIFF file");
      }
      return await res.blob();
    })
    .then(async (blob) => {
      if (blob.size === 0) {
        throw new BlobError("decodeTiff - Invalid blob size from api");
      }
      return new File([blob], "file", { type: "image/tiff" });
    });
  return await file.arrayBuffer();
};

export const utifToRGBA = (bytes: ArrayBuffer): DecodedTiff => {
  // Decode image
  const ifds = UTIF.decode(bytes);
  if (ifds.length === 0) {
    throw new DecodeError("decodeTiff - Failed to decode TIFF array");
  }
  UTIF.decodeImage(bytes, ifds[0]);
  if (ifds[0].width < 1 || ifds[0].height < 1 || ifds[0].data.length === 0) {
    throw new DecodeError("decodeTiff - Invalid image size or data");
  }
  const rgba = UTIF.toRGBA8(ifds[0]);
  if (rgba.length === 0) {
    throw new DecodeError("decodeTiff - Failed to convert TIFF to RGBA");
  }
  return {
    rgba,
    width: ifds[0].width,
    height: ifds[0].height,
  };
};

export const decodeTiff = async (imageSrc: string): Promise<DecodedTiff> => {
  let decodedTiff: DecodedTiff = {
    rgba: new Uint8Array(0) as Uint8Array<ArrayBufferLike>,
    width: 0,
    height: 0,
  };
  if (imageSrc == null || imageSrc === "" || !imageSrc.includes("image/tiff")) {
    return decodedTiff;
  }
  try {
    // Convert base64 to bytes
    const bytes = await fetchArrayBuffer(imageSrc);
    const { rgba, width, height } = utifToRGBA(bytes);

    decodedTiff = {
      rgba,
      width,
      height,
    };
  } catch (error) {
    console.error("Error in decodeTiff - ", error);
  }
  return decodedTiff;
};

export const getImageDims = async (src: string): Promise<number[]> => {
  if (typeof src !== "string") {
    throw new TypeError("Image source is not a string");
  }
  if (src.includes("image/tiff")) {
    return decodeTiff(src).then((decodedTiff) => {
      return [decodedTiff.width, decodedTiff.height];
    });
  } else {
    const image = new Image();
    image.src = src;
    return new Promise((resolve) => {
      image.onload = () => {
        resolve([image.width, image.height]);
      };
    });
  }
};

export const nextCacheIndex = (
  imageIndex: number,
  imageCache: Images[],
): number => {
  if (imageIndex < 0) {
    throw new ValueError("Image index is less than 0");
  }
  if (imageCache == null) {
    throw new ValueError("Image cache is null");
  }
  return imageCache.length > 0
    ? imageCache[imageCache.length - 1].index + 1
    : imageIndex + 1;
};

export const loadCaptureToCache = async (
  src: string,
  imageCache: Images[],
  index: number,
): Promise<Images[]> => {
  if (src == null || src === "") {
    throw new ValueError("Image source is null or empty");
  }
  if (index < 0) {
    throw new ValueError("Image index is less than 0");
  }
  if (imageCache == null) {
    throw new ValueError("Image cache is null");
  }
  return getImageDims(src).then((dims) => {
    const newCache = [
      ...imageCache,
      {
        index: index,
        src,
        scores: [],
        classifications: [],
        boxes: [],
        annotated: false,
        imageDims: dims,
        overlapping: [],
        overlappingIndices: [],
        topN: [],
      },
    ];

    return newCache;
  });
};

export const loadResultsToCache = (
  inferenceData: ApiInferenceData,
  imageCache: Images[],
  imageIndex: number,
): Images[] => {
  if (inferenceData == null) {
    throw new ValueError("Inference data is null");
  }
  if (inferenceData.boxes == null) {
    throw new ValueError("Inference data boxes are null");
  }
  if (imageIndex == null || imageIndex < 0) {
    throw new ValueError("Image index is invalid");
  }
  if (imageCache == null) {
    throw new ValueError("Image cache is null");
  }
  // amends the image cache given an image index, with the inference data
  // which is received from the server
  const newCache = [...imageCache];
  const topN = inferenceData.boxes.map((box) => box.topN);
  const index = newCache.findIndex((item) => item.index === imageIndex);
  if (index === -1) {
    throw new ValueError("Image index not found in cache");
  }

  newCache[index] = {
    ...newCache[index],
    scores: inferenceData.boxes.map((box) => box.score),
    classifications: inferenceData.boxes.map((box) =>
      box.label.replace(/^\d+\s+/, ""),
    ),
    boxes: inferenceData.boxes.map((box) => {
      return {
        ...box.box,
        inferenceId: inferenceData.inference_id,
        boxId: box.box_id,
        classId: box.object_type_id,
        label: box.label,
        is_verified: box.is_verified !== undefined ? box.is_verified : false,
      };
    }),
    overlapping: inferenceData.boxes.map((box) => box.overlapping),
    overlappingIndices: inferenceData.boxes.map(
      (box) => box.overlappingIndices,
    ),
    topN,
    annotated: true,
  };

  return newCache;
};

export const getLabelOccurrence = (image: Images): LabelOccurrences => {
  if (image == null) {
    throw new ValueError("Image object is null");
  }
  if (
    image.annotated &&
    (image.scores == null || image.classifications == null)
  ) {
    throw new ValueError("Image object is missing scores and classifications");
  }
  // gets the number of occurences of each label in the current
  // image based on score threshold and seed label selection in classification results
  const result: LabelOccurrences = {};

  if (image.annotated) {
    image.scores.forEach((score: number, index: number) => {
      if (score) {
        const label: string = image.classifications[index];
        if (result[label] !== undefined) {
          result[label] = result[label] + 1;
        } else {
          result[label] = 1;
        }
      }
    });
  }

  return result;
};

// DOM-based alternatives to canvas drawing functions - Much more testable!

export interface BoxElement {
  boxDiv: HTMLDivElement;
  labelDiv: HTMLDivElement;
}

export const createBoxElement = (
  box: Images["boxes"][0],
  score: number,
  index: number,
  prediction: string,
  labelOccurrences: LabelOccurrences,
  switchTable: boolean,
): BoxElement => {
  if (box == null) {
    throw new ValueError("Box is null");
  }

  const { topX, topY, bottomX, bottomY } = box;
  const width = bottomX - topX;
  const height = bottomY - topY;

  // Create bounding box div
  const boxDiv = document.createElement("div");
  boxDiv.style.position = "absolute";
  boxDiv.style.left = `${topX}px`;
  boxDiv.style.top = `${topY}px`;
  boxDiv.style.width = `${width}px`;
  boxDiv.style.height = `${height}px`;
  boxDiv.style.border = `3px solid ${box.is_verified ? "green" : "red"}`;
  boxDiv.style.pointerEvents = "none";
  boxDiv.className = "inference-box";
  boxDiv.setAttribute("data-testid", `inference-box-${index}`);

  // Create label div
  const labelDiv = document.createElement("div");
  const labelIndex = getInferenceLabelIndex(prediction, labelOccurrences);
  const scorePercentage = (score * 100).toFixed(0);
  const boxMidX = width / 2;

  // Label positioning logic (same as canvas version)
  let labelTop = -25;
  if (topY <= 40) {
    labelTop = height + 5;
  }

  labelDiv.style.position = "absolute";
  labelDiv.style.left = `${boxMidX - 45}px`; // Center label (90px width / 2)
  labelDiv.style.top = `${labelTop}px`;
  labelDiv.style.width = "90px";
  labelDiv.style.height = "25px";
  labelDiv.style.backgroundColor = "white";
  labelDiv.style.color = "black";
  labelDiv.style.fontSize = "12px";
  labelDiv.style.fontWeight = "bold";
  labelDiv.style.textAlign = "center";
  labelDiv.style.lineHeight = "25px";
  labelDiv.style.border = "1px solid #ccc";
  labelDiv.style.pointerEvents = "none";
  labelDiv.className = "inference-label";
  labelDiv.setAttribute("data-testid", `inference-label-${index}`);

  if (switchTable) {
    labelDiv.textContent = `[${labelIndex + 1}] - ${scorePercentage}%`;
  } else {
    labelDiv.textContent = `[${index + 1}]`;
  }

  return { boxDiv, labelDiv };
};

export const createBoxElements = (
  imageData: Images,
  selectedLabel: string,
  labelOccurrences: LabelOccurrences,
  switchTable: boolean,
): BoxElement[] => {
  if (!imageData.annotated) {
    return [];
  }
  if (imageData.classifications == null) {
    throw new ValueError("Image object is missing classifications");
  }
  if (imageData.boxes == null) {
    throw new ValueError("Image object is missing boxes");
  }
  if (imageData.scores == null) {
    throw new ValueError("Image object is missing scores");
  }

  let selectedClassifications = imageData.classifications.map(
    (prediction, index) => ({ label: prediction, index }),
  );

  if (selectedLabel !== "all") {
    selectedClassifications = imageData.classifications
      .map((prediction, index) => ({ label: prediction, index }))
      .filter((item) => item.label === selectedLabel);
  }

  return selectedClassifications.map((prediction) =>
    createBoxElement(
      imageData.boxes[prediction.index],
      imageData.scores[prediction.index],
      prediction.index,
      prediction.label,
      labelOccurrences,
      switchTable,
    ),
  );
};

export const renderBoxesToContainer = (
  container: HTMLElement,
  imageData: Images,
  selectedLabel: string,
  labelOccurrences: LabelOccurrences,
  switchTable: boolean,
  showInference: boolean,
): void => {
  if (container == null) {
    throw new ValueError("Container element is null");
  }

  // Clear existing boxes
  const existingBoxes = container.querySelectorAll(
    ".inference-box, .inference-label",
  );
  existingBoxes.forEach((box) => box.remove());

  if (!showInference) {
    return;
  }

  // Create and append new box elements
  const boxElements = createBoxElements(
    imageData,
    selectedLabel,
    labelOccurrences,
    switchTable,
  );

  boxElements.forEach(({ boxDiv, labelDiv }) => {
    boxDiv.appendChild(labelDiv);
    container.appendChild(boxDiv);
  });

  // Add capture label (equivalent to canvas bottom-left text)
  const captureLabel = document.createElement("div");
  captureLabel.style.position = "absolute";
  captureLabel.style.left = "10px";
  captureLabel.style.bottom = "15px";
  captureLabel.style.color = "red";
  captureLabel.style.fontSize = "14px";
  captureLabel.style.fontWeight = "bold";
  captureLabel.style.pointerEvents = "none";
  captureLabel.className = "capture-label";
  captureLabel.setAttribute("data-testid", "capture-label");
  captureLabel.textContent = `${imageData.imageId ? imageData.imageId : `Capture ${imageData.index}`}`;
  container.appendChild(captureLabel);
};
