// ToggleButton.tsx
import React from "react";
import Button from "@mui/material/Button";

interface ToggleButtonProps {
  isActive: boolean;
  onClick: () => void;
  text: string;
}

const ToggleButton: React.FC<ToggleButtonProps> = ({
  isActive,
  onClick,
  text,
}) => {
  return (
    <Button
      sx={{
        flexGrow: 1,
        backgroundColor: isActive ? "lightgrey" : "#05486C",
        color: isActive ? "black" : "white",
        fontWeight: "bold",
        fontSize: "1.5vh",
        "&:hover": {
          backgroundColor: isActive ? "#043354" : "darkgrey",
          color: "white",
        },
        height: "4.5vh",
        padding: "0 8vh",
        borderRadius: 0,
      }}
      onClick={onClick}
    >
      {text}
    </Button>
  );
};

export default ToggleButton;
