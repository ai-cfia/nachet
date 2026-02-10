import { Button } from "@mui/material";
import { MouseEvent, useState } from "react";
import { BoxCSS, InferenceBox } from "@common/types";
import { SimpleFeedbackForm } from "../feedback_form";
import { getScaledBounds } from "@common";

const ScaledInferenceBox = (props: {
  index: number;
  imageWidth: number;
  imageHeight: number;
  box: InferenceBox;
  canvasWidth: number;
  canvasHeight: number;
  label: string;
  visible: boolean;
  submitPositiveFeedback: (index: number) => void;
  handleNegativeFeedback: (index: number, boxPosition: BoxCSS) => void;
}) => {
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
  const [anchorEl, setAnchorEl] = useState<HTMLButtonElement | null>(null);

  const handleClick = (event: MouseEvent<HTMLButtonElement>) => {
    setAnchorEl(event.currentTarget);
  };

<<<<<<< HEAD
  const sendBoxBackwards = useCallback(() => {
<<<<<<< HEAD
    if (typeof box.z === "number") {
      box.z = Math.max(0, box.z - 1);
    } else {
      box.z = Math.max(0, index + 10 - 1);
    }
    console.log("Box z-index after sending backwards: ", box.z);
  }, [box]);

  const sendBoxForward = useCallback(() => {
    if (typeof box.z === "number") {
      box.z = box.z + 1;
    } else {
      box.z = index + 10 + 1;
    }
    console.log("Box z-index after sending forward: ", box.z);
  }, [box]);
=======
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
>>>>>>> 8362bc6 (functionnal z index changes)

  const openLayersMenu = useCallback((event: MouseEvent<HTMLElement>) => {
    // stop propagation to avoid opening the feedback form
    event.stopPropagation();
    setLayersAnchorEl(event.currentTarget);
  }, []);

  const closeLayersMenu = useCallback(() => {
    setLayersAnchorEl(null);
  }, []);

  const boxPosition = computeBoxPosition(
=======
  const { scaledHeight, scaledWidth, scaledTopX, scaledTopY } = getScaledBounds(
>>>>>>> parent of 1506747 (layer submenu)
    canvasWidth,
    canvasHeight,
    imageWidth,
    imageHeight,
    box,
  );

  const boxPosition: BoxCSS = {
    minWidth: scaledWidth,
    minHeight: scaledHeight,
    maxWidth: scaledWidth,
    maxHeight: scaledHeight,
    left: scaledTopX,
    top: scaledTopY,
  };

  const style = {
    ...boxPosition,
    position: "absolute",
    border: "none",
    borderRadius: 0,
    display: visible ? "block" : "none",
<<<<<<< HEAD
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
=======
    zIndex: 10,
>>>>>>> parent of 1506747 (layer submenu)
    "&:hover": {
      bgcolor: "#0b9deb",
      opacity: 0.2,
    },
  };

  return (
    <>
      <Button sx={style} onClick={handleClick} />
      <SimpleFeedbackForm
        anchorEl={anchorEl}
        onClose={() => setAnchorEl(null)}
        submitPositiveFeedback={() => submitPositiveFeedback(index)}
        onNegativeFeedback={() => handleNegativeFeedback(index, boxPosition)}
      />
    </>
  );
};

export default ScaledInferenceBox;
