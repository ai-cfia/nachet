import { Button } from "@mui/material";

const ControlBarButton = (props: {
  label: string;
  icon: React.ReactNode;
  disabled: boolean;
  onClick: () => void;
  sx?: object;
}) => {
  const { label, icon, onClick, disabled, sx } = props;
  const buttonStyle = {
    borderRadius: "0.4vh",
    paddingTop: { xs: "1vh", md: "0.3vh" },
    paddingBottom: { xs: "1vh", md: "0.3vh" },
    paddingLeft: { xs: "1.5vh", md: "0.7vh" },
    paddingRight: { xs: "1.5vh", md: "0.7vh" },
    fontSize: { xs: "1.8vh", md: "1.17vh" },
    width: "fit-content",
    textTransform: "none",
    "&:hover": {
      backgroundColor: "#F5F5F5",
      transition: "0.1s ease-in-out all",
    },
    ...sx,
  };
  return (
    <Button
      color="inherit"
      variant="outlined"
      disabled={disabled}
      onClick={onClick}
      sx={buttonStyle}
    >
      <div
        style={{
          display: "flex",
          alignItems: "center",
          flexWrap: "wrap",
        }}
      >
        {icon}
        <span>{label}</span>
      </div>
    </Button>
  );
};

export default ControlBarButton;
