import { useState, useRef, useEffect, useCallback } from "react";
import { BoxCSS } from "@common/types";

interface CanvasFreeformBoxProps {
  position: BoxCSS;
  canvasWidth: number;
  canvasHeight: number;
  onSubmit: (boxPosition: BoxCSS) => void;
  dragEnabled: boolean;
  onChangesSavedChange: (saved: boolean) => void;
  onSaveBoxRef?: (saveFunc: () => void) => void;
}

type ResizeHandle =
  | "none"
  | "top"
  | "right"
  | "bottom"
  | "left"
  | "top-right"
  | "bottom-right"
  | "bottom-left"
  | "top-left";

const CanvasFreeformBox = (props: CanvasFreeformBoxProps) => {
  const {
    onSubmit,
    position,
    canvasWidth,
    canvasHeight,
    dragEnabled,
    onChangesSavedChange,
    onSaveBoxRef,
  } = props;
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [boxX, setBoxX] = useState(position.left);
  const [boxY, setBoxY] = useState(position.top);
  const [boxWidth, setBoxWidth] = useState(position.minWidth);
  const [boxHeight, setBoxHeight] = useState(position.minHeight);

  const [isDragging, setIsDragging] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const [resizeHandle, setResizeHandle] = useState<ResizeHandle>("none");
  const [dragStartX, setDragStartX] = useState(0);
  const [dragStartY, setDragStartY] = useState(0);
  const [startBoxX, setStartBoxX] = useState(0);
  const [startBoxY, setStartBoxY] = useState(0);
  const [startBoxWidth, setStartBoxWidth] = useState(0);
  const [startBoxHeight, setStartBoxHeight] = useState(0);

  const HANDLE_SIZE = 10;

  const drawBox = useCallback(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;

    // Clear canvas
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    // Draw green rectangle border
    ctx.strokeStyle = "green";
    ctx.lineWidth = 2;
    ctx.strokeRect(boxX, boxY, boxWidth, boxHeight);

    // Draw resize handles if resize is enabled
    if (!dragEnabled) {
      ctx.fillStyle = "green";
      const handles = [
        { x: boxX, y: boxY }, // top-left
        { x: boxX + boxWidth, y: boxY }, // top-right
        { x: boxX + boxWidth, y: boxY + boxHeight }, // bottom-right
        { x: boxX, y: boxY + boxHeight }, // bottom-left
      ];

      handles.forEach((handle) => {
        ctx.fillRect(
          handle.x - HANDLE_SIZE / 2,
          handle.y - HANDLE_SIZE / 2,
          HANDLE_SIZE,
          HANDLE_SIZE,
        );
      });
    }
  }, [boxX, boxY, boxWidth, boxHeight, dragEnabled]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    canvas.width = canvasWidth;
    canvas.height = canvasHeight;
    drawBox();
  }, [canvasWidth, canvasHeight, drawBox]);

  const getResizeHandle = (mouseX: number, mouseY: number): ResizeHandle => {
    if (dragEnabled) return "none";

    const threshold = HANDLE_SIZE;

    // Check corners first
    if (
      Math.abs(mouseX - boxX) < threshold &&
      Math.abs(mouseY - boxY) < threshold
    )
      return "top-left";
    if (
      Math.abs(mouseX - (boxX + boxWidth)) < threshold &&
      Math.abs(mouseY - boxY) < threshold
    )
      return "top-right";
    if (
      Math.abs(mouseX - (boxX + boxWidth)) < threshold &&
      Math.abs(mouseY - (boxY + boxHeight)) < threshold
    )
      return "bottom-right";
    if (
      Math.abs(mouseX - boxX) < threshold &&
      Math.abs(mouseY - (boxY + boxHeight)) < threshold
    )
      return "bottom-left";

    // Check edges
    if (
      mouseX >= boxX &&
      mouseX <= boxX + boxWidth &&
      Math.abs(mouseY - boxY) < threshold
    )
      return "top";
    if (
      mouseX >= boxX &&
      mouseX <= boxX + boxWidth &&
      Math.abs(mouseY - (boxY + boxHeight)) < threshold
    )
      return "bottom";
    if (
      mouseY >= boxY &&
      mouseY <= boxY + boxHeight &&
      Math.abs(mouseX - boxX) < threshold
    )
      return "left";
    if (
      mouseY >= boxY &&
      mouseY <= boxY + boxHeight &&
      Math.abs(mouseX - (boxX + boxWidth)) < threshold
    )
      return "right";

    return "none";
  };

  const isInsideBox = (mouseX: number, mouseY: number): boolean => {
    return (
      mouseX >= boxX &&
      mouseX <= boxX + boxWidth &&
      mouseY >= boxY &&
      mouseY <= boxY + boxHeight
    );
  };

  const handleMouseDown = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    const handle = getResizeHandle(mouseX, mouseY);

    if (handle !== "none") {
      // Start resizing
      setIsResizing(true);
      setResizeHandle(handle);
      setDragStartX(mouseX);
      setDragStartY(mouseY);
      setStartBoxX(boxX);
      setStartBoxY(boxY);
      setStartBoxWidth(boxWidth);
      setStartBoxHeight(boxHeight);
      onChangesSavedChange(false);
    } else if (isInsideBox(mouseX, mouseY) && dragEnabled) {
      // Start dragging
      setIsDragging(true);
      setDragStartX(mouseX);
      setDragStartY(mouseY);
      setStartBoxX(boxX);
      setStartBoxY(boxY);
      onChangesSavedChange(false);
    }
  };

  const handleMouseMove = (e: React.MouseEvent<HTMLCanvasElement>) => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    const rect = canvas.getBoundingClientRect();
    const mouseX = e.clientX - rect.left;
    const mouseY = e.clientY - rect.top;

    if (isDragging) {
      const deltaX = mouseX - dragStartX;
      const deltaY = mouseY - dragStartY;
      setBoxX(
        Math.max(0, Math.min(canvasWidth - boxWidth, startBoxX + deltaX)),
      );
      setBoxY(
        Math.max(0, Math.min(canvasHeight - boxHeight, startBoxY + deltaY)),
      );
    } else if (isResizing) {
      const deltaX = mouseX - dragStartX;
      const deltaY = mouseY - dragStartY;

      let newX = startBoxX;
      let newY = startBoxY;
      let newWidth = startBoxWidth;
      let newHeight = startBoxHeight;

      switch (resizeHandle) {
        case "top-left":
          newX = startBoxX + deltaX;
          newY = startBoxY + deltaY;
          newWidth = startBoxWidth - deltaX;
          newHeight = startBoxHeight - deltaY;
          break;
        case "top-right":
          newY = startBoxY + deltaY;
          newWidth = startBoxWidth + deltaX;
          newHeight = startBoxHeight - deltaY;
          break;
        case "bottom-right":
          newWidth = startBoxWidth + deltaX;
          newHeight = startBoxHeight + deltaY;
          break;
        case "bottom-left":
          newX = startBoxX + deltaX;
          newWidth = startBoxWidth - deltaX;
          newHeight = startBoxHeight + deltaY;
          break;
        case "top":
          newY = startBoxY + deltaY;
          newHeight = startBoxHeight - deltaY;
          break;
        case "bottom":
          newHeight = startBoxHeight + deltaY;
          break;
        case "left":
          newX = startBoxX + deltaX;
          newWidth = startBoxWidth - deltaX;
          break;
        case "right":
          newWidth = startBoxWidth + deltaX;
          break;
      }

      // Enforce minimum size
      if (newWidth >= 20) {
        setBoxX(newX);
        setBoxWidth(newWidth);
      }
      if (newHeight >= 20) {
        setBoxY(newY);
        setBoxHeight(newHeight);
      }
    } else {
      // Update cursor based on hover position
      const handle = getResizeHandle(mouseX, mouseY);
      if (handle !== "none") {
        const cursors: Record<ResizeHandle, string> = {
          none: "default",
          top: "ns-resize",
          right: "ew-resize",
          bottom: "ns-resize",
          left: "ew-resize",
          "top-right": "nesw-resize",
          "bottom-right": "nwse-resize",
          "bottom-left": "nesw-resize",
          "top-left": "nwse-resize",
        };
        canvas.style.cursor = cursors[handle];
      } else if (isInsideBox(mouseX, mouseY) && dragEnabled) {
        canvas.style.cursor = "move";
      } else {
        canvas.style.cursor = "default";
      }
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
    setIsResizing(false);
    setResizeHandle("none");
  };

  const handleSubmit = useCallback(() => {
    const currPosition: BoxCSS = {
      top: boxY,
      left: boxX,
      minWidth: boxWidth,
      minHeight: boxHeight,
      maxWidth: boxWidth,
      maxHeight: boxHeight,
    };
    onChangesSavedChange(true);
    onSubmit(currPosition);
  }, [boxX, boxY, boxWidth, boxHeight, onChangesSavedChange, onSubmit]);

  // Expose handleSubmit via callback for external button
  useEffect(() => {
    if (onSaveBoxRef) {
      onSaveBoxRef(handleSubmit);
    }
  }, [onSaveBoxRef, handleSubmit]);

  return (
    <canvas
      ref={canvasRef}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        zIndex: 100,
        pointerEvents: "auto",
      }}
    />
  );
};

export default CanvasFreeformBox;
