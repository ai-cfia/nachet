import {
  Box,
  IconButton,
  Tooltip,
  Menu,
  MenuItem,
  ListItemIcon,
} from "@mui/material";
import { MouseEvent, useCallback, useState } from "react";
import { BoxCSS, InferenceBox } from "@common/types";
import { SimpleFeedbackForm } from "../feedback_form";
import { getScaledBounds } from "@common";
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
  isLayersOpen: boolean;
  onLayersToggle: () => void;
  submitPositiveFeedback: (index: number) => void;
  handleNegativeFeedback: (index: number, boxPosition: BoxCSS) => void;
}

const computeBoxPosition = (
  canvasWidth: number,
  canvasHeight: number,
  imageWidth: number,
  imageHeight: number,
  box: InferenceBox,
): BoxCSS => {
  const { scaledHeight, scaledWidth, scaledTopX, scaledTopY } = getScaledBounds(
    canvasWidth,
    canvasHeight,
    imageWidth,
    imageHeight,
    box,
  );

  return {
    minWidth: scaledWidth,
    minHeight: scaledHeight,
    maxWidth: scaledWidth,
    maxHeight: scaledHeight,
    left: scaledTopX,
    top: scaledTopY,
  };
};

const ScaledInferenceBox = (props: Props) => {
  const {
    index,
    box,
    visible,
    imageWidth,
    imageHeight,
    canvasWidth,
    canvasHeight,
    isLayersOpen,
    onLayersToggle,
    submitPositiveFeedback,
    handleNegativeFeedback,
  } = props;

  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);
  const [layersAnchorEl, setLayersAnchorEl] = useState<HTMLElement | null>(
    null,
  );

  const [zOffset, setZOffset] = useState<number>(0);

  const [isSelected, setIsSelected] = useState(false);

  // Base z-index falls back to `index` when unspecified.
  const baseZ = index;

  const computeZIndex = (base: number, offset: number) => base + offset;

  const zIndex = computeZIndex(baseZ, zOffset);

  const handleBoxClick = useCallback((event: MouseEvent<HTMLElement>) => {
    setAnchorEl(event.currentTarget);
  }, []);

  const sendBoxBackwards = useCallback(() => {
    setZOffset((prev) => {
      const currentZ = baseZ + prev;
      const newZ = Math.max(0, currentZ - 1);
      return newZ - baseZ;
    });
  }, [baseZ]);

  const sendBoxForward = useCallback(() => {
    setZOffset((prev) => {
      const currentZ = baseZ + prev;
      const newZ = currentZ + 1;
      return newZ - baseZ;
    });
  }, [baseZ]);

  const openLayersMenu = useCallback(
    (event: MouseEvent<HTMLElement>) => {
      onLayersToggle();
      event.stopPropagation();
      setLayersAnchorEl(event.currentTarget);
      setIsSelected(true);
    },
    [onLayersToggle],
  );

  const closeLayersMenu = useCallback(() => {
    onLayersToggle();
    setLayersAnchorEl(null);
    setIsSelected(false);
  }, [onLayersToggle]);

  const boxPosition = computeBoxPosition(
    canvasWidth,
    canvasHeight,
    imageWidth,
    imageHeight,
    box,
  );

  const sx = {
    ...boxPosition,
    position: "absolute",
    border: "none",
    borderRadius: 0,
    display: visible ? "block" : "none",
    zIndex: zIndex,
    // if the layers menu is open, keep the hover styles applied so the box looks active
    ...(isSelected
      ? {
          bgcolor: "rgba(11,157,235,0.12)",
          border: "1px solid rgba(11,157,235,0.22)",
          "& .layersBtn": {
            opacity: 1,
            pointerEvents: "auto",
            transform: "scale(1.05)",
            color: "primary.main",
            bgcolor: "rgba(255,255,255,1)",
            zIndex: 300,
          },
        }
      : {}),
    // hide layer icons by default; reveal on hover of the parent box
    "& .layersBtn": {
      opacity: 0,
      pointerEvents: "none",
      transition: "opacity 150ms ease, transform 150ms ease",
      filter: "drop-shadow(0 1px 2px rgba(0,0,0,0.2))",
    },
    "&:hover": {
      // show a subtle highlight without dimming children
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
    <>
      <Box
        component="div"
        role="button"
        tabIndex={0}
        sx={sx}
        onClick={handleBoxClick}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            handleBoxClick(e as unknown as MouseEvent<HTMLElement>);
          }
        }}
      >
        {/* Small label badge (score + z-index) shown top-left */}
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
            display: "none",
            ...(isLayersOpen && { display: "block" }),
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
            aria-controls={layersAnchorEl ? "layers-menu" : undefined}
            aria-haspopup="true"
          >
            <LayersOutlined fontSize="small" />
          </IconButton>
        </Tooltip>

        <Menu
          id="layers-menu"
          anchorEl={layersAnchorEl}
          open={Boolean(layersAnchorEl)}
          onClose={closeLayersMenu}
          anchorOrigin={{ vertical: "top", horizontal: "right" }}
          transformOrigin={{ vertical: "top", horizontal: "right" }}
          slotProps={{
            list: {
              onClick: (e: React.MouseEvent) => e.stopPropagation(),
              sx: { padding: 0 },
            },
            paper: { sx: { borderRadius: 20, padding: 0 } },
          }}
        >
          <MenuItem
            sx={{ padding: "0px !important", minWidth: 0 }}
            onClick={() => {
              sendBoxForward();
            }}
          >
            <ListItemIcon sx={{ minWidth: "0px !important" }}>
              <ArrowCircleUpRounded />
            </ListItemIcon>
          </MenuItem>
          <MenuItem
            sx={{ padding: 0 }}
            onClick={() => {
              sendBoxBackwards();
            }}
          >
            <ListItemIcon sx={{ minWidth: "0px !important" }}>
              <ArrowCircleDownRounded />
            </ListItemIcon>
          </MenuItem>
        </Menu>
      </Box>

      <SimpleFeedbackForm
        anchorEl={anchorEl as HTMLButtonElement | null}
        onClose={() => setAnchorEl(null)}
        submitPositiveFeedback={() => submitPositiveFeedback(index)}
        onNegativeFeedback={() => handleNegativeFeedback(index, boxPosition)}
      />
    </>
  );
};

export default ScaledInferenceBox;
