// Colormap for heatmap overlays (CAM activation maps).

/** "jet" colormap (blue=cold → red=hot): value [0,1] -> RGB. */
export const jetColor = (t: number): [number, number, number] => {
  const v = Math.max(0, Math.min(1, t));
  const clamp = (x: number) => Math.max(0, Math.min(1, x));
  return [
    Math.round(clamp(1.5 - Math.abs(4 * v - 3)) * 255),
    Math.round(clamp(1.5 - Math.abs(4 * v - 2)) * 255),
    Math.round(clamp(1.5 - Math.abs(4 * v - 1)) * 255),
  ];
};
