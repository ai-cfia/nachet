import { useRef, useEffect, useState } from "react";
import { Box, Typography } from "@mui/material";
import type { InferenceResult } from "@common/types";
import InferenceOverlay from "@components/InferenceOverlay";
import { useIsPortrait } from "@hooks/useIsPortrait";

interface Props {
  src: string | undefined;
  imageDims: number[];
  result: InferenceResult | null;
}

const ImageViewer = ({ src, imageDims, result }: Props) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerSize, setContainerSize] = useState({ width: 0, height: 0 });
  const isPortrait = useIsPortrait();

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver((entries) => {
      const entry = entries[0];
      if (!entry) return;
      const { width, height } = entry.contentRect;
      setContainerSize({ width, height });
    });
    ro.observe(el);
    return () => {
      ro.disconnect();
    };
  }, []);

  const imgW = imageDims[0] ?? 0;
  const imgH = imageDims[1] ?? 0;

  return (
    <Box
      ref={containerRef}
      sx={{
        position: "relative",
        width: "100%",
        height: "100%",
        overflow: "hidden",
        bgcolor: "#f5f5f5",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        border: "0.01vh solid LightGrey",
        borderRadius: "0.4vh",
      }}
      data-testid="image-viewer-component"
    >
      {src ? (
        <Box
          sx={{
            position: "relative",
            width: "100%",
            height: "100%",
            ...(isPortrait
              ? { transform: "rotate(-90deg)", maxWidth: "100%", maxHeight: "100%" }
              : {}),
          }}
        >
          <img
            src={src}
            alt="Uploaded image"
            style={{
              width: "100%",
              height: "100%",
              objectFit: "contain",
              display: "block",
            }}
          />
          {result &&
            containerSize.width > 0 &&
            result.boxes.map((box, i) => (
              <InferenceOverlay
                key={box.boxId}
                index={i}
                imageWidth={imgW}
                imageHeight={imgH}
                box={box}
                canvasWidth={containerSize.width}
                canvasHeight={containerSize.height}
                label={result.classifications[i] ?? ""}
                visible={true}
                totalBoxes={result.totalBoxes}
                isClassifying={result.classifications[i] === ""}
              />
            ))}
        </Box>
      ) : (
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{ fontSize: "1.3vh" }}
        >
          No image loaded
        </Typography>
      )}
    </Box>
  );
};

export default ImageViewer;
