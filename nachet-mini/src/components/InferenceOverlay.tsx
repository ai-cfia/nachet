import {
  Box,
  IconButton,
  Tooltip,
  Menu,
  MenuItem,
  ListItemIcon,
} from "@mui/material";
import { type MouseEvent, useCallback, useState } from "react";
import type { InferenceBox } from "@common/types";
import { getScaledBounds } from "@common/imageutils";
import {
  LayersOutlined,
  ArrowCircleDownRounded,
  ArrowCircleUpRounded,
} from "@mui/icons-material";

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
}

const InferenceOverlay = ({
  index,
  box,
  visible,
  imageWidth,
  imageHeight,
  canvasWidth,
  canvasHeight,
  label,
}: Props) => {
  const [layersAnchorEl, setLayersAnchorEl] = useState<HTMLElement | null>(
    null,
  );
  const [zOffset, setZOffset] = useState(0);
  const [isSelected, setIsSelected] = useState(false);

  const baseZ = index;
  const zIndex = baseZ + zOffset;
  const isLayersOpen = Boolean(layersAnchorEl);

  const { scaledHeight, scaledWidth, scaledTopX, scaledTopY } = getScaledBounds(
    canvasWidth,
    canvasHeight,
    imageWidth,
    imageHeight,
    box,
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

  const openLayersMenu = useCallback((event: MouseEvent<HTMLElement>) => {
    event.stopPropagation();
    setLayersAnchorEl(event.currentTarget);
    setIsSelected(true);
  }, []);

  const closeLayersMenu = useCallback(() => {
    setLayersAnchorEl(null);
    setIsSelected(false);
  }, []);

  const sx = {
    position: "absolute",
    minWidth: scaledWidth,
    minHeight: scaledHeight,
    maxWidth: scaledWidth,
    maxHeight: scaledHeight,
    left: scaledTopX,
    top: scaledTopY,
    border: "none",
    borderRadius: 0,
    display: visible ? "block" : "none",
    zIndex,
    ...(isSelected && {
      bgcolor: "rgba(11,157,235,0.12)",
      border: "1px solid rgba(11,157,235,0.22)",
    }),
    "& .layersBtn": {
      opacity: 0,
      pointerEvents: "none",
      transition: "opacity 150ms ease, transform 150ms ease",
      filter: "drop-shadow(0 1px 2px rgba(0,0,0,0.2))",
      ...(isSelected && {
        opacity: 1,
        pointerEvents: "auto",
        transform: "scale(1.05)",
        color: "primary.main",
        bgcolor: "rgba(255,255,255,1)",
        zIndex: 300,
      }),
    },
    "&:hover": {
      bgcolor: "rgba(11,157,235,0.12)",
      border: "1px solid rgba(11,157,235,0.22)",
      "& .layersBtn": {
        opacity: 1,
        pointerEvents: "auto",
        transform: "scale(1.05)",
        color: "primary.main",
        bgcolor: "rgba(255,255,255,1)",
      },
    },
  };

  return (
    <Box
      component="div"
      aria-label={label}
      sx={sx}
    >
      {/* z-index badge — visible while layers menu is open */}
      <Box
        aria-hidden
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

      <Menu
        id="layers-menu"
        anchorEl={layersAnchorEl}
        open={isLayersOpen}
        onClose={closeLayersMenu}
        anchorOrigin={{ vertical: "top", horizontal: "right" }}
        transformOrigin={{ vertical: "top", horizontal: "right" }}
        slotProps={{
          list: {
            onClick: (e: MouseEvent) => e.stopPropagation(),
            sx: { padding: 0 },
          },
          paper: { sx: { borderRadius: 20, padding: 0 } },
        }}
      >
        <MenuItem
          sx={{ padding: "0px !important", minWidth: 0 }}
          onClick={sendBoxForward}
        >
          <ListItemIcon sx={{ minWidth: "0px !important" }}>
            <ArrowCircleUpRounded />
          </ListItemIcon>
        </MenuItem>
        <MenuItem sx={{ padding: 0 }} onClick={sendBoxBackwards}>
          <ListItemIcon sx={{ minWidth: "0px !important" }}>
            <ArrowCircleDownRounded />
          </ListItemIcon>
        </MenuItem>
      </Menu>
    </Box>
  );
};

export default InferenceOverlay;
