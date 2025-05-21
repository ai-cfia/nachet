import Draggable, { DraggableData, DraggableEvent } from "react-draggable";
import { NumberSize, Resizable } from "re-resizable";
import { Box, IconButton } from "@mui/material";
import OpenWithOutlinedIcon from "@mui/icons-material/OpenWithOutlined";
import SaveIcon from "@mui/icons-material/Save";
import CancelOutlinedIcon from "@mui/icons-material/CancelOutlined";
import OpenInFullOutlinedIcon from "@mui/icons-material/OpenInFullOutlined";
import { useState } from "react";
import { BoxCSS } from "../../../common/types";

interface FreeformBoxProps {
  position: BoxCSS;
  onSubmit: (boxPosition: BoxCSS) => void;
  onCancel: () => void;
}

const FreeformBox = (props: FreeformBoxProps) => {
  const { onSubmit, onCancel, position } = props;
  const [dragEnabled, setDragEnabled] = useState(true);
  const [topX, setTopX] = useState(position.left);
  const [topY, setTopY] = useState(position.top);
  const [width, setWidth] = useState(position.minWidth);
  const [height, setHeight] = useState(position.minHeight);
  const [changesSaved, setChangesSaved] = useState(true);

  const buttonStyle = {
    borderRadius: "0",
    maxHeight: "25px",
    maxWidth: "25px",
  };

  const handleDragStop = (
    _event: DraggableEvent,
    dragElement: DraggableData,
  ) => {
    setTopX(dragElement.x);
    setTopY(dragElement.y);
    setChangesSaved(false);
  };

  const handleResizeStop = (
    _event: MouseEvent | TouchEvent,
    _direction: string,
    _ref: HTMLElement,
    delta: NumberSize,
  ) => {
    setWidth(width + delta.width);
    setHeight(height + delta.height);
    setChangesSaved(false);
  };

  const handleSubmit = () => {
    const currPosition = {
      top: topY,
      left: topX,
      minWidth: width,
      minHeight: height,
      maxWidth: width,
      maxHeight: height,
    };
    setChangesSaved(true);
    onSubmit(currPosition);
  };

  return (
    <Draggable
      defaultPosition={{
        x: position.left,
        y: position.top,
      }}
      bounds="parent"
      disabled={!dragEnabled}
      onStop={handleDragStop}
    >
      <Resizable
        style={{
          position: "absolute",
          zIndex: 100,
          backgroundColor: "none",
          border: "2px solid green",
          padding: "10px",
          minWidth: "5px",
          minHeight: "5px",
        }}
        defaultSize={{
          width: position.minWidth,
          height: position.minHeight,
        }}
        enable={{
          top: false,
          right: !dragEnabled,
          bottom: !dragEnabled,
          left: false,
          topRight: false,
          bottomRight: !dragEnabled,
          bottomLeft: false,
          topLeft: false,
        }}
        onResizeStop={handleResizeStop}
        bounds="parent"
      >
        <Box
          sx={{
            position: "absolute",
            top: -30,
            right: position.minWidth < 50 ? -25 : 0,
            backgroundColor: "white",
            borderRadius: "5%",
            display: "flex",
            flexDirection: "row",
            justifyContent: "center",
            alignItems: "center",
            border: `0.01vh solid LightGrey`,
            fitContent: "wrap",
          }}
        >
          <IconButton
            sx={{
              ...buttonStyle,
              color: "blue",
            }}
            onClick={() => setDragEnabled(!dragEnabled)}
          >
            {dragEnabled ? (
              <OpenWithOutlinedIcon />
            ) : (
              <OpenInFullOutlinedIcon />
            )}
          </IconButton>

          <IconButton
            sx={{
              ...buttonStyle,
              color: changesSaved ? "green" : "grey",
              marginRight: "10px",
              marginLeft: "10px",
            }}
            onClick={handleSubmit}
          >
            <SaveIcon />
          </IconButton>

          <IconButton
            sx={{
              ...buttonStyle,
              color: "red",
            }}
            onClick={onCancel}
          >
            <CancelOutlinedIcon />
          </IconButton>
        </Box>
      </Resizable>
    </Draggable>
  );
};

export default FreeformBox;
