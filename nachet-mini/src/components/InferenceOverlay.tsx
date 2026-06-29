import {
  Box,
  CircularProgress,
  IconButton,
  Tooltip,
  Menu,
  MenuItem,
  ListItemIcon,
} from "@mui/material";
import {
  type MouseEvent as ReactMouseEvent,
  useCallback,
  useState,
  useEffect,
  useRef,
} from "react";
import type { InferenceBox } from "@common/types";
import type { DffBoxResult } from "@stores/useInferenceStore";
import { conceptColorRgb, jetColor } from "@common/dffColors";
import { getScaledBounds, getUnscaledCoordinates } from "@common/imageutils";
import { useIsPortrait } from "@hooks/useIsPortrait";
import {
  LayersOutlined,
  ArrowCircleDownRounded,
  ArrowCircleUpRounded,
  DeleteOutline,
} from "@mui/icons-material";

type ResizeHandle = "nw" | "n" | "ne" | "e" | "se" | "s" | "sw" | "w" | null;

const HANDLE_SIZE = 8;
const MIN_BOX_PX = 20;

const handleCursors: Record<string, string> = {
  nw: "nwse-resize",
  n: "ns-resize",
  ne: "nesw-resize",
  e: "ew-resize",
  se: "nwse-resize",
  s: "ns-resize",
  sw: "nesw-resize",
  w: "ew-resize",
};

interface Props {
  index: number;
  imageWidth: number;
  imageHeight: number;
  box: InferenceBox;
  canvasWidth: number;
  canvasHeight: number;
  label: string;
  visible: boolean;
  totalBoxes: number;
  isClassifying: boolean;
  minBoxSize: number;
  editMode?: boolean;
  isEditSelected?: boolean;
  /** DFF concept heatmaps for this box (when the patched classifier is active). */
  dff?: DffBoxResult;
  /** Which concept indices to overlay on this box (empty/undefined = none). */
  activeConcepts?: number[];
  /** When set, show only this concept as a jet (blue→red) heatmap instead. */
  jetConcept?: number;
  onBoxUpdate?: (index: number, box: InferenceBox) => void;
  onBoxDelete?: (index: number) => void;
  onBoxSelect?: (index: number) => void;
}

const isSmallBox = (box: InferenceBox, minBoxSize: number): boolean => {
  const width = Math.abs(box.bottomX - box.topX);
  const height = Math.abs(box.bottomY - box.topY);
  return Math.max(width, height) < minBoxSize;
};

const InferenceOverlay = ({
  index,
  box,
  visible,
  imageWidth,
  imageHeight,
  canvasWidth,
  canvasHeight,
  label,
  isClassifying,
  minBoxSize,
  editMode = false,
  isEditSelected = false,
  dff,
  activeConcepts,
  jetConcept,
  onBoxUpdate,
  onBoxDelete,
  onBoxSelect,
}: Props) => {
  const [layersAnchorEl, setLayersAnchorEl] = useState<HTMLElement | null>(
    null,
  );
  const [zOffset, setZOffset] = useState(0);
  const [isSelected, setIsSelected] = useState(false);
  const isPortrait = useIsPortrait();

  // Drag/resize state
  const [isDragging, setIsDragging] = useState(false);
  const [resizeHandle, setResizeHandle] = useState<ResizeHandle>(null);
  const dragStart = useRef({ mouseX: 0, mouseY: 0, box: box });

  // DFF concept overlay canvas; ImageViewer passes the box's heatmaps plus the
  // set of active concept indices (toggled per concept in the Images panel).
  const dffCanvasRef = useRef<HTMLCanvasElement>(null);

  const baseZ = index;
  const zIndex = baseZ + zOffset + (isEditSelected ? 100 : 0);
  const isLayersOpen = Boolean(layersAnchorEl);

  const { scaledHeight, scaledWidth, scaledTopX, scaledTopY } = getScaledBounds(
    canvasWidth,
    canvasHeight,
    imageWidth,
    imageHeight,
    box,
  );

  const toImageCoords = useCallback(
    (clientX: number, clientY: number, containerEl: Element) => {
      const rect = containerEl.getBoundingClientRect();
      const displayX = clientX - rect.left;
      const displayY = clientY - rect.top;
      return getUnscaledCoordinates(
        canvasWidth,
        canvasHeight,
        imageWidth,
        imageHeight,
        displayX,
        displayY,
      );
    },
    [canvasWidth, canvasHeight, imageWidth, imageHeight],
  );

  // Render the DFF overlay. Two modes:
  //  - jet: a single concept as a blue→red heatmap.
  //  - stack: color each cell by whichever of the toggled-on concepts is
  //    strongest there (one concept -> its smooth map; several -> a clean
  //    dominant-per-cell combined map, no wash).
  // The 12x12 heatmap is bilinearly upsampled to a fine grid *before* coloring,
  // so the jet ramp interpolates in value space (smooth blue→red) instead of
  // canvas-blending final colors (which looks blocky/muddy).
  useEffect(() => {
    const canvas = dffCanvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (!dff || editMode) return;

    const g = dff.grid;
    const COLOR_ALPHA = 215; // colored stack (per-cell dominant concept)
    const JET_ALPHA = 140; // jet heatmap (~0.55, matches the old seed cutouts)
    const F = 192; // fine grid side for smooth value-space interpolation
    const stack = activeConcepts ?? [];
    const jc = jetConcept;
    const jetHeat =
      jc !== undefined && dff.heatmaps[jc]?.length === g * g
        ? dff.heatmaps[jc]
        : undefined;
    if (!jetHeat && stack.length === 0) return;

    // Bilinear sample of a (g x g) heatmap at fractional (fx, fy) in [0, g-1].
    const sample = (heat: Float32Array | number[], fx: number, fy: number) => {
      const x0 = Math.floor(fx);
      const y0 = Math.floor(fy);
      const x1 = Math.min(x0 + 1, g - 1);
      const y1 = Math.min(y0 + 1, g - 1);
      const dx = fx - x0;
      const dy = fy - y0;
      return (
        heat[y0 * g + x0] * (1 - dx) * (1 - dy) +
        heat[y0 * g + x1] * dx * (1 - dy) +
        heat[y1 * g + x0] * (1 - dx) * dy +
        heat[y1 * g + x1] * dx * dy
      );
    };

    const fine = document.createElement("canvas");
    fine.width = F;
    fine.height = F;
    const fctx = fine.getContext("2d");
    if (!fctx) return;
    const img = fctx.createImageData(F, F);
    const span = g - 1;

    for (let j = 0; j < F; j++) {
      const fy = (j / (F - 1)) * span;
      for (let i = 0; i < F; i++) {
        const fx = (i / (F - 1)) * span;
        const o = (j * F + i) * 4;
        if (jetHeat) {
          const [r, gg, b] = jetColor(sample(jetHeat, fx, fy));
          img.data[o] = r;
          img.data[o + 1] = gg;
          img.data[o + 2] = b;
          img.data[o + 3] = JET_ALPHA;
        } else {
          let best = -1;
          let bestVal = -1;
          for (const c of stack) {
            const heat = dff.heatmaps[c];
            if (!heat || g * g !== heat.length) continue;
            const v = sample(heat, fx, fy);
            if (v > bestVal) {
              bestVal = v;
              best = c;
            }
          }
          if (best < 0) continue;
          const [r, gg, b] = conceptColorRgb(best);
          img.data[o] = r;
          img.data[o + 1] = gg;
          img.data[o + 2] = b;
          img.data[o + 3] = Math.round(
            Math.max(0, Math.min(1, bestVal)) * COLOR_ALPHA,
          );
        }
      }
    }
    fctx.putImageData(img, 0, 0);
    ctx.imageSmoothingEnabled = true;
    ctx.drawImage(fine, 0, 0, canvas.width, canvas.height);
  }, [dff, activeConcepts, jetConcept, editMode, scaledWidth, scaledHeight]);

  // Window-level mouse handlers for drag/resize
  useEffect(() => {
    if (!isDragging && !resizeHandle) return;

    const handleMouseMove = (e: globalThis.MouseEvent) => {
      const container = document.querySelector(
        '[data-testid="image-viewer-component"]',
      );
      if (!container) return;

      const current = toImageCoords(e.clientX, e.clientY, container);
      const start = dragStart.current;

      if (isDragging) {
        const dx = current.imageX - start.mouseX;
        const dy = current.imageY - start.mouseY;
        const w = start.box.bottomX - start.box.topX;
        const h = start.box.bottomY - start.box.topY;

        let newTopX = start.box.topX + dx;
        let newTopY = start.box.topY + dy;
        newTopX = Math.max(0, Math.min(newTopX, imageWidth - w));
        newTopY = Math.max(0, Math.min(newTopY, imageHeight - h));

        onBoxUpdate?.(index, {
          ...start.box,
          topX: newTopX,
          topY: newTopY,
          bottomX: newTopX + w,
          bottomY: newTopY + h,
        });
      } else if (resizeHandle) {
        let { topX, topY, bottomX, bottomY } = start.box;
        const dx = current.imageX - start.mouseX;
        const dy = current.imageY - start.mouseY;

        if (resizeHandle.includes("w")) topX = start.box.topX + dx;
        if (resizeHandle.includes("e")) bottomX = start.box.bottomX + dx;
        if (resizeHandle.includes("n")) topY = start.box.topY + dy;
        if (resizeHandle.includes("s")) bottomY = start.box.bottomY + dy;

        // Enforce minimum size
        if (bottomX - topX < MIN_BOX_PX) {
          if (resizeHandle.includes("w")) topX = bottomX - MIN_BOX_PX;
          else bottomX = topX + MIN_BOX_PX;
        }
        if (bottomY - topY < MIN_BOX_PX) {
          if (resizeHandle.includes("n")) topY = bottomY - MIN_BOX_PX;
          else bottomY = topY + MIN_BOX_PX;
        }

        // Clamp to image bounds
        topX = Math.max(0, topX);
        topY = Math.max(0, topY);
        bottomX = Math.min(imageWidth, bottomX);
        bottomY = Math.min(imageHeight, bottomY);

        onBoxUpdate?.(index, {
          ...start.box,
          topX,
          topY,
          bottomX,
          bottomY,
        });
      }
    };

    const handleMouseUp = () => {
      setIsDragging(false);
      setResizeHandle(null);
    };

    window.addEventListener("mousemove", handleMouseMove);
    window.addEventListener("mouseup", handleMouseUp);
    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      window.removeEventListener("mouseup", handleMouseUp);
    };
  }, [
    isDragging,
    resizeHandle,
    index,
    imageWidth,
    imageHeight,
    toImageCoords,
    onBoxUpdate,
  ]);

  const handleBoxMouseDown = useCallback(
    (e: ReactMouseEvent) => {
      if (!editMode) return;
      e.stopPropagation();
      e.preventDefault();
      onBoxSelect?.(index);

      const container = document.querySelector(
        '[data-testid="image-viewer-component"]',
      );
      if (!container) return;
      const coords = toImageCoords(e.clientX, e.clientY, container);
      dragStart.current = {
        mouseX: coords.imageX,
        mouseY: coords.imageY,
        box,
      };
      setIsDragging(true);
    },
    [editMode, index, box, toImageCoords, onBoxSelect],
  );

  const handleResizeMouseDown = useCallback(
    (e: ReactMouseEvent<HTMLDivElement>) => {
      if (!editMode) return;
      const handle = e.currentTarget.dataset.resizeHandle as ResizeHandle;
      if (!handle) return;
      e.stopPropagation();
      e.preventDefault();
      onBoxSelect?.(index);

      const container = document.querySelector(
        '[data-testid="image-viewer-component"]',
      );
      if (!container) return;
      const coords = toImageCoords(e.clientX, e.clientY, container);
      dragStart.current = {
        mouseX: coords.imageX,
        mouseY: coords.imageY,
        box,
      };
      setResizeHandle(handle);
    },
    [editMode, index, box, toImageCoords, onBoxSelect],
  );

  const sendBoxForward = useCallback(() => {
    setZOffset((prev) => baseZ + prev + 1 - baseZ);
  }, [baseZ]);

  const sendBoxBackwards = useCallback(() => {
    setZOffset((prev) => {
      const newZ = Math.max(0, baseZ + prev - 1);
      return newZ - baseZ;
    });
  }, [baseZ]);

  const openLayersMenu = useCallback((event: ReactMouseEvent<HTMLElement>) => {
    event.stopPropagation();
    setLayersAnchorEl(event.currentTarget);
    setIsSelected(true);
  }, []);

  const closeLayersMenu = useCallback(() => {
    setLayersAnchorEl(null);
    setIsSelected(false);
  }, []);

  const small = isSmallBox(box, minBoxSize);
  const borderColor = small ? "rgba(255,0,0,0.7)" : "rgba(128,0,128,0.7)";
  const hoverBg = small ? "rgba(255,0,0,0.12)" : "rgba(128,0,128,0.12)";
  const labelAtBottom = box.topY < 40;
  const effectiveSelected = editMode ? isEditSelected : isSelected;

  const sx = {
    position: "absolute",
    minWidth: scaledWidth,
    minHeight: scaledHeight,
    maxWidth: scaledWidth,
    maxHeight: scaledHeight,
    left: scaledTopX,
    top: scaledTopY,
    border: `2px solid ${editMode ? (isEditSelected ? "#1565c0" : borderColor) : borderColor}`,
    borderRadius: 0,
    display: visible ? "block" : "none",
    zIndex,
    cursor: editMode ? (isDragging ? "grabbing" : "grab") : "default",
    ...(effectiveSelected && {
      bgcolor: editMode ? "rgba(21,101,192,0.12)" : hoverBg,
      border: `2px solid ${editMode ? "#1565c0" : borderColor}`,
    }),
    "& .layersBtn, & .deleteBtn": {
      opacity: 0,
      pointerEvents: "none",
      transition: "opacity 150ms ease, transform 150ms ease",
      filter: "drop-shadow(0 1px 2px rgba(0,0,0,0.2))",
      ...(effectiveSelected && {
        opacity: 1,
        pointerEvents: "auto",
        transform: "scale(1.05)",
        color: small ? "error.main" : "primary.main",
        bgcolor: "rgba(255,255,255,1)",
        zIndex: 300,
      }),
    },
    "&:hover": {
      bgcolor: editMode ? "rgba(21,101,192,0.12)" : hoverBg,
      border: `2px solid ${editMode ? "#1565c0" : borderColor}`,
      "& .layersBtn, & .deleteBtn": {
        opacity: 1,
        pointerEvents: "auto",
        transform: "scale(1.05)",
        color: small ? "error.main" : "primary.main",
        bgcolor: "rgba(255,255,255,1)",
      },
    },
  };

  const resizeHandles: { handle: ResizeHandle; style: React.CSSProperties }[] =
    [
      {
        handle: "nw",
        style: {
          top: -HANDLE_SIZE / 2,
          left: -HANDLE_SIZE / 2,
          cursor: handleCursors.nw,
        },
      },
      {
        handle: "n",
        style: {
          top: -HANDLE_SIZE / 2,
          left: "50%",
          marginLeft: -HANDLE_SIZE / 2,
          cursor: handleCursors.n,
        },
      },
      {
        handle: "ne",
        style: {
          top: -HANDLE_SIZE / 2,
          right: -HANDLE_SIZE / 2,
          cursor: handleCursors.ne,
        },
      },
      {
        handle: "e",
        style: {
          top: "50%",
          right: -HANDLE_SIZE / 2,
          marginTop: -HANDLE_SIZE / 2,
          cursor: handleCursors.e,
        },
      },
      {
        handle: "se",
        style: {
          bottom: -HANDLE_SIZE / 2,
          right: -HANDLE_SIZE / 2,
          cursor: handleCursors.se,
        },
      },
      {
        handle: "s",
        style: {
          bottom: -HANDLE_SIZE / 2,
          left: "50%",
          marginLeft: -HANDLE_SIZE / 2,
          cursor: handleCursors.s,
        },
      },
      {
        handle: "sw",
        style: {
          bottom: -HANDLE_SIZE / 2,
          left: -HANDLE_SIZE / 2,
          cursor: handleCursors.sw,
        },
      },
      {
        handle: "w",
        style: {
          top: "50%",
          left: -HANDLE_SIZE / 2,
          marginTop: -HANDLE_SIZE / 2,
          cursor: handleCursors.w,
        },
      },
    ];

  return (
    <Box
      component="div"
      aria-label={label}
      data-testid={`inference-overlay-${index}`}
      sx={sx}
      onMouseDown={editMode ? handleBoxMouseDown : undefined}
    >
      {/* DFF overlay: colored concept stack or a single jet heatmap */}
      {dff &&
        !editMode &&
        (jetConcept !== undefined ||
          (activeConcepts && activeConcepts.length > 0)) && (
          <canvas
            ref={dffCanvasRef}
            data-testid={`dff-overlay-${index}`}
            width={Math.max(1, Math.round(scaledWidth))}
            height={Math.max(1, Math.round(scaledHeight))}
            style={{
              position: "absolute",
              top: 0,
              left: 0,
              width: "100%",
              height: "100%",
              pointerEvents: "none",
              zIndex: 250,
            }}
          />
        )}

      {/* box number (+ spinner when classifying) */}
      <Box
        data-testid={`inference-overlay-label-${index}`}
        sx={{
          position: "absolute",
          ...(labelAtBottom
            ? { bottom: -23, left: -2 }
            : { top: -23, left: -2 }),
          color: small ? "rgba(255,0,0,0.9)" : "rgba(128,0,128,0.9)",
          fontSize: "20px",
          fontWeight: 700,
          lineHeight: 1,
          pointerEvents: "none",
          display: "flex",
          alignItems: "center",
          gap: "4px",
          ...(isPortrait
            ? { transform: "rotate(90deg)", transformOrigin: "bottom right" }
            : {}),
        }}
      >
        {index + 1}
        {isClassifying && (
          <CircularProgress size={20} sx={{ color: borderColor }} />
        )}
      </Box>

      {/* Resize handles (edit mode only) */}
      {editMode &&
        resizeHandles.map(({ handle, style }) => (
          <div
            key={handle}
            data-testid={`resize-handle-${handle}`}
            data-resize-handle={handle}
            onMouseDown={handleResizeMouseDown}
            style={{
              position: "absolute",
              width: HANDLE_SIZE,
              height: HANDLE_SIZE,
              backgroundColor: "#1565c0",
              border: "1px solid white",
              zIndex: 400,
              ...style,
            }}
          />
        ))}

      {/* Delete button (edit mode) */}
      {editMode && (
        <Tooltip title="Delete" placement="top">
          <IconButton
            className="deleteBtn"
            size="small"
            onClick={(e) => {
              e.stopPropagation();
              onBoxDelete?.(index);
            }}
            sx={{
              position: "absolute",
              top: 6,
              left: 6,
              zIndex: 300,
              bgcolor: "rgba(255,255,255,0.95)",
              color: "error.main",
              width: 28,
              height: 28,
              minWidth: 28,
              borderRadius: 1,
            }}
            aria-label="delete box"
          >
            <DeleteOutline fontSize="small" />
          </IconButton>
        </Tooltip>
      )}

      {/* z-index badge — visible while layers menu is open */}
      {!editMode && (
        <Box
          aria-hidden
          data-testid={`z-index-badge-${index}`}
          sx={{
            position: "absolute",
            top: 6,
            left: 6,
            zIndex: 310,
            bgcolor: "rgba(255,255,255,0.95)",
            color: "text.primary",
            px: 0.6,
            py: 0.2,
            borderRadius: 0.5,
            fontSize: "0.75rem",
            pointerEvents: "none",
            boxShadow: "0 1px 2px rgba(0,0,0,0.1)",
            display: isLayersOpen ? "block" : "none",
          }}
        >
          {zIndex}
        </Box>
      )}

      {!editMode && (
        <Tooltip title="Layers" placement="top">
          <IconButton
            className="layersBtn"
            size="small"
            onClick={openLayersMenu}
            sx={{
              position: "absolute",
              top: 6,
              right: 6,
              zIndex: 300,
              bgcolor: "rgba(255,255,255,0.95)",
              color: "primary.main",
              width: 28,
              height: 28,
              minWidth: 28,
              borderRadius: 1,
            }}
            aria-label="layers"
            aria-controls={isLayersOpen ? "layers-menu" : undefined}
            aria-haspopup="true"
          >
            <LayersOutlined fontSize="small" />
          </IconButton>
        </Tooltip>
      )}

      {!editMode && (
        <Menu
          id="layers-menu"
          anchorEl={layersAnchorEl}
          open={isLayersOpen}
          onClose={closeLayersMenu}
          anchorOrigin={{ vertical: "top", horizontal: "right" }}
          transformOrigin={{ vertical: "top", horizontal: "right" }}
          slotProps={{
            list: {
              onClick: (e: ReactMouseEvent) => e.stopPropagation(),
              sx: { padding: 0 },
            },
            paper: { sx: { borderRadius: 20, padding: 0 } },
          }}
        >
          <MenuItem
            sx={{ padding: "0px !important", minWidth: 0 }}
            data-testid="layers-menu-forward"
            onClick={() => {
              sendBoxForward();
              closeLayersMenu();
            }}
          >
            <ListItemIcon sx={{ minWidth: "0px !important" }}>
              <ArrowCircleUpRounded />
            </ListItemIcon>
          </MenuItem>
          <MenuItem
            sx={{ padding: 0 }}
            data-testid="layers-menu-backward"
            onClick={() => {
              sendBoxBackwards();
              closeLayersMenu();
            }}
          >
            <ListItemIcon sx={{ minWidth: "0px !important" }}>
              <ArrowCircleDownRounded />
            </ListItemIcon>
          </MenuItem>
        </Menu>
      )}
    </Box>
  );
};

export default InferenceOverlay;
