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

/** Draw a smooth jet-colour CAM into an existing canvas context. */
export const drawCamHeatmap = (
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
  heatmap: number[],
  grid: number,
): void => {
  if (grid < 1 || width < 1 || height < 1 || grid * grid !== heatmap.length) {
    return;
  }

  const fineSize = 192;
  const span = grid - 1;
  const fine = document.createElement("canvas");
  fine.width = fineSize;
  fine.height = fineSize;
  const fineContext = fine.getContext("2d");
  if (!fineContext) return;

  const sample = (x: number, y: number): number => {
    const x0 = Math.floor(x);
    const y0 = Math.floor(y);
    const x1 = Math.min(x0 + 1, grid - 1);
    const y1 = Math.min(y0 + 1, grid - 1);
    const dx = x - x0;
    const dy = y - y0;
    return (
      heatmap[y0 * grid + x0] * (1 - dx) * (1 - dy) +
      heatmap[y0 * grid + x1] * dx * (1 - dy) +
      heatmap[y1 * grid + x0] * (1 - dx) * dy +
      heatmap[y1 * grid + x1] * dx * dy
    );
  };

  const image = fineContext.createImageData(fineSize, fineSize);
  for (let row = 0; row < fineSize; row++) {
    const y = (row / (fineSize - 1)) * span;
    for (let column = 0; column < fineSize; column++) {
      const x = (column / (fineSize - 1)) * span;
      const [red, green, blue] = jetColor(sample(x, y));
      const offset = (row * fineSize + column) * 4;
      image.data[offset] = red;
      image.data[offset + 1] = green;
      image.data[offset + 2] = blue;
      image.data[offset + 3] = 140;
    }
  }

  fineContext.putImageData(image, 0, 0);
  ctx.imageSmoothingEnabled = true;
  ctx.drawImage(fine, 0, 0, width, height);
};
