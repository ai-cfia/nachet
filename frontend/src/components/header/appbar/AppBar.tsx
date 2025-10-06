import { colours } from "../../../styles/colours";
import { Button, Box, Typography } from "@mui/material";
import React from "react";

interface params {
  windowSize: {
    width: number;
    height: number;
  };
  setSwitchLanguage: React.Dispatch<React.SetStateAction<boolean>>;
  switchLanguage: boolean;
}

const Appbar: React.FC<params> = (props) => {
  const buttonStyle = {
    marginRight: 0,
    marginLeft: 0,
    borderRadius: "0.4vh",
    paddingTop: "0.2vh",
    paddingBottom: "0.2vh",
    paddingLeft: "0.5vh",
    paddingRight: "0.5vh",
    fontSize: "1.17vh",
    width: "7vh",
    backgroundColor: colours.CFIA_Background_Blue,
    border: `0.01vh solid ${colours.CFIA_Background_Blue}`,
    color: colours.CFIA_Font_White,
    "&:hover": {
      border: `0.01vh solid ${colours.CFIA_Background_White}`,
    },
  };

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
          Nachet Weed Seed Species Classifier
        </Typography>
        <Button
          variant="outlined"
          onClick={() => {
            props.setSwitchLanguage(!props.switchLanguage);
          }}
          sx={buttonStyle}
        >
          {props.switchLanguage ? "EN" : "FR"}
        </Button>
      </Box>
    </Box>
  );
};

export default Appbar;
