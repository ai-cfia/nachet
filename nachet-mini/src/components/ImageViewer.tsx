import { useRef, useEffect, useState, useCallback } from "react";
import { Box, Typography } from "@mui/material";
import type { InferenceResult } from "@common/types";
import { getUnscaledCoordinates, getScaledBounds } from "@common/imageutils";
import InferenceOverlay from "@components/InferenceOverlay";
import { useIsPortrait } from "@hooks/useIsPortrait";
import { useBoxEditStore, generateUserBoxId } from "@stores/useBoxEditStore";

interface Props {
  src: string | undefined;
  imageDims: number[];
  result: InferenceResult | null;
}

const MIN_DRAW_PX = 20;

const ImageViewer = ({ src, imageDims, result }: Props) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [containerSize, setContainerSize] = useState({ width: 0, height: 0 });
  const isPortrait = useIsPortrait();

  // Box edit store
  const isEditing = useBoxEditStore((s) => s.isEditing);
  const editedBoxes = useBoxEditStore((s) => s.editedBoxes);
  const selectedBoxIndex = useBoxEditStore((s) => s.selectedBoxIndex);
  const isDrawing = useBoxEditStore((s) => s.isDrawing);
  const updateBox = useBoxEditStore((s) => s.updateBox);
  const addBox = useBoxEditStore((s) => s.addBox);
  const deleteBox = useBoxEditStore((s) => s.deleteBox);
  const setSelectedBoxIndex = useBoxEditStore((s) => s.setSelectedBoxIndex);
  const setIsDrawing = useBoxEditStore((s) => s.setIsDrawing);

  // Draw state
  const [drawStart, setDrawStart] = useState<{
    imageX: number;
    imageY: number;
  } | null>(null);
  const [drawCurrent, setDrawCurrent] = useState<{
    imageX: number;
    imageY: number;
  } | null>(null);

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

  const toImageCoords = useCallback(
    (clientX: number, clientY: number) => {
      const container = containerRef.current;
      if (!container) return { imageX: 0, imageY: 0 };
      const rect = container.getBoundingClientRect();
      return getUnscaledCoordinates(
        containerSize.width,
        containerSize.height,
        imgW,
        imgH,
        clientX - rect.left,
        clientY - rect.top,
      );
    },
    [containerSize.width, containerSize.height, imgW, imgH],
  );

  const handleDrawMouseDown = useCallback(
    (e: React.MouseEvent) => {
      if (!isDrawing) return;
      e.preventDefault();
      const coords = toImageCoords(e.clientX, e.clientY);
      setDrawStart(coords);
      setDrawCurrent(coords);
    },
    [isDrawing, toImageCoords],
  );

  useEffect(() => {
    if (!drawStart) return;

    const handleMouseMove = (e: globalThis.MouseEvent) => {
      const coords = toImageCoords(e.clientX, e.clientY);
      setDrawCurrent(coords);
    };

    const handleMouseUp = (e: globalThis.MouseEvent) => {
      const end = toImageCoords(e.clientX, e.clientY);
      const topX = Math.max(0, Math.min(drawStart.imageX, end.imageX));
      const topY = Math.max(0, Math.min(drawStart.imageY, end.imageY));
      const bottomX = Math.min(imgW, Math.max(drawStart.imageX, end.imageX));
      const bottomY = Math.min(imgH, Math.max(drawStart.imageY, end.imageY));

      if (bottomX - topX >= MIN_DRAW_PX && bottomY - topY >= MIN_DRAW_PX) {
        addBox({
          topX,
          topY,
          bottomX,
          bottomY,
          boxId: generateUserBoxId(),
          inferenceId: "user-drawn",
          classId: "",
          label: "",
          isVerified: false,
          bboxSource: "user",
        });
      }

      setDrawStart(null);
      setDrawCurrent(null);
      setIsDrawing(false);
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [drawStart, toImageCoords, imgW, imgH, addBox, setIsDrawing]);

  // Compute draw preview rectangle in display coordinates
  const drawPreviewStyle = (() => {
    if (!drawStart || !drawCurrent || containerSize.width === 0) return null;
    const topX = Math.min(drawStart.imageX, drawCurrent.imageX);
    const topY = Math.min(drawStart.imageY, drawCurrent.imageY);
    const bottomX = Math.max(drawStart.imageX, drawCurrent.imageX);
    const bottomY = Math.max(drawStart.imageY, drawCurrent.imageY);
    const { scaledWidth, scaledHeight, scaledTopX, scaledTopY } =
      getScaledBounds(containerSize.width, containerSize.height, imgW, imgH, {
        topX,
        topY,
        bottomX,
        bottomY,
      });
    return {
      position: "absolute" as const,
      left: scaledTopX,
      top: scaledTopY,
      width: scaledWidth,
      height: scaledHeight,
      border: "2px dashed #1565c0",
      backgroundColor: "rgba(21,101,192,0.1)",
      pointerEvents: "none" as const,
      zIndex: 500,
    };
  })();

  const displayBoxes = isEditing ? editedBoxes : (result?.boxes ?? []);

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
              ? {
                  transform: "rotate(-90deg)",
                  maxWidth: "100%",
                  maxHeight: "100%",
                }
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
          {/* Draw overlay */}
          {isEditing && isDrawing && (
            <div
              data-testid="draw-overlay"
              onMouseDown={handleDrawMouseDown}
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                width: "100%",
                height: "100%",
                cursor: "crosshair",
                zIndex: 450,
              }}
            />
          )}
          {/* Draw preview rectangle */}
          {drawPreviewStyle && (
            <div data-testid="draw-preview" style={drawPreviewStyle} />
          )}
          {/* Boxes */}
          {containerSize.width > 0 &&
            displayBoxes.map((box, i) => (
              <InferenceOverlay
                key={isEditing ? `edit-${i}` : box.boxId}
                index={i}
                imageWidth={imgW}
                imageHeight={imgH}
                box={box}
                canvasWidth={containerSize.width}
                canvasHeight={containerSize.height}
                label={
                  isEditing
                    ? box.label || `Box ${i + 1}`
                    : (result?.classifications[i] ?? "")
                }
                visible={true}
                totalBoxes={displayBoxes.length}
                isClassifying={
                  isEditing ? false : result?.classifications[i] === ""
                }
                minBoxSize={result?.minBoxSize ?? 0}
                editMode={isEditing}
                isEditSelected={isEditing && selectedBoxIndex === i}
                onBoxUpdate={isEditing ? updateBox : undefined}
                onBoxDelete={isEditing ? deleteBox : undefined}
                onBoxSelect={isEditing ? setSelectedBoxIndex : undefined}
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
