// Shared colors for DFF concept overlays + their toggle swatches, so the
// on-image heatmap for "Concept k" matches the color shown in the toggle list.

/** Distinct hues (deg) per DFF concept. Index = concept number. */
export const DFF_CONCEPT_HUES = [0, 205, 130, 45, 280, 170];

/** HSL(hue, 90%, 50%) -> RGB. */
export const hueToRgb = (hueDeg: number): [number, number, number] => {
  const h = ((hueDeg % 360) + 360) % 360;
  const c = 0.9; // chroma proxy for s=0.9, l=0.5
  const x = c * (1 - Math.abs(((h / 60) % 2) - 1));
  let r = 0,
    g = 0,
    b = 0;
  if (h < 60) [r, g, b] = [c, x, 0];
  else if (h < 120) [r, g, b] = [x, c, 0];
  else if (h < 180) [r, g, b] = [0, c, x];
  else if (h < 240) [r, g, b] = [0, x, c];
  else if (h < 300) [r, g, b] = [x, 0, c];
  else [r, g, b] = [c, 0, x];
  const m = 0.5 - c / 2;
  return [
    Math.round((r + m) * 255),
    Math.round((g + m) * 255),
    Math.round((b + m) * 255),
  ];
};

/** RGB color for a concept index. */
export const conceptColorRgb = (concept: number): [number, number, number] =>
  hueToRgb(DFF_CONCEPT_HUES[concept % DFF_CONCEPT_HUES.length]);

/** CSS `rgb(...)` color for a concept index (for swatches). */
export const conceptColorCss = (concept: number): string => {
  const [r, g, b] = conceptColorRgb(concept);
  return `rgb(${r}, ${g}, ${b})`;
};

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
