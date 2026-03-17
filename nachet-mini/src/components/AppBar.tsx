import { colours } from "../styles/colours";
import { Box, Typography } from "@mui/material";

const AppBar: React.FC = () => {
  return (
    <Box
      sx={{
        backgroundColor: colours.CFIA_Background_Blue,
        color: colours.CFIA_Font_White,
        height: "3.5vh",
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        position: "sticky",
        top: 0,
        zIndex: 3,
        boxShadow: "0 0 5px 0 rgba(0, 0, 0, 0.5)",
      }}
    >
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          zIndex: 3,
          width: "100%",
          padding: "0 1.5vw",
          height: "2.8vh",
        }}
      >
        <Typography
          variant="h2"
          sx={{
            color: colours.CFIA_Font_White,
            fontSize: "1.4vh",
            fontWeight: "bold",
            textDecoration: "none",
            display: "flex",
            alignItems: "center",
            justifySelf: "flex-start",
            zIndex: 3,
          }}
        >
          Nachet Mini
        </Typography>
      </Box>
    </Box>
  );
};

export default AppBar;
