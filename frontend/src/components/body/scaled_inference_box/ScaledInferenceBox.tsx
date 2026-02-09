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
  ArrowUpward,
  ArrowDownward,
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
  submitPositiveFeedback: (index: number) => void;
  handleNegativeFeedback: (index: number, boxPosition: BoxCSS) => void;
}

function computeBoxPosition(
  canvasWidth: number,
  canvasHeight: number,
  imageWidth: number,
  imageHeight: number,
  box: InferenceBox,
): BoxCSS {
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
}

const ScaledInferenceBox = (props: Props) => {
  const {
    index,
    box,
    visible,
    imageWidth,
    imageHeight,
    canvasWidth,
    canvasHeight,
    submitPositiveFeedback,
    handleNegativeFeedback,
  } = props;

  const [anchorEl, setAnchorEl] = useState<HTMLElement | null>(null);
  const [layersAnchorEl, setLayersAnchorEl] = useState<HTMLElement | null>(
    null,
  );

  const [zOffset, setZOffset] = useState<number>(0);

  // Base z-index falls back to `index + 10` when unspecified.
  const baseZ = typeof box.z === "number" ? box.z : index + 10;

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

  const openLayersMenu = useCallback((event: MouseEvent<HTMLElement>) => {
    event.stopPropagation();
    setLayersAnchorEl(event.currentTarget);
  }, []);

  const closeLayersMenu = useCallback(() => {
    setLayersAnchorEl(null);
  }, []);

  const boxPosition = computeBoxPosition(
    canvasWidth,
    canvasHeight,
    imageWidth,
    imageHeight,
    box,
  );

  const isLayersOpen = Boolean(layersAnchorEl);

  const sx = {
    ...boxPosition,
    position: "absolute",
    border: "none",
    borderRadius: 0,
    display: visible ? "block" : "none",
    zIndex: zIndex + 10,
    // if the layers menu is open, keep the hover styles applied so the box looks active
    ...(isLayersOpen
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
            list: { onClick: (e: React.MouseEvent) => e.stopPropagation() },
          }}
        >
          <MenuItem
            onClick={() => {
              sendBoxForward();
            }}
          >
            <ListItemIcon>
              <ArrowUpward />
            </ListItemIcon>
          </MenuItem>
          <MenuItem
            onClick={() => {
              sendBoxBackwards();
            }}
          >
            <ListItemIcon>
              <ArrowDownward />
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