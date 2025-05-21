import { BoxCSS, BoxCoordinates } from "./types";

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
