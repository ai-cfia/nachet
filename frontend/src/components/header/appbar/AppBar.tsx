import { colours } from "../../../styles/colours";
import { Box, Typography, Switch, Stack } from "@mui/material";
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
        <Stack
          direction="row"
          spacing={1}
          alignItems="center"
          sx={{ height: "100%" }}
        >
          <Typography
            sx={{
              fontSize: "1.2vh",
              color: colours.CFIA_Font_White,
              fontWeight: props.switchLanguage ? "normal" : "bold",
            }}
          >
            EN
          </Typography>
          <Switch
            checked={props.switchLanguage}
            onChange={() => props.setSwitchLanguage(!props.switchLanguage)}
            size="small"
            sx={{
              "& .MuiSwitch-switchBase.Mui-checked": {
                color: colours.CFIA_Font_White,
              },
              "& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track": {
                backgroundColor: colours.CFIA_Font_White,
              },
              "& .MuiSwitch-track": {
                backgroundColor: colours.CFIA_Font_White,
              },
            }}
          />
          <Typography
            sx={{
              fontSize: "1.2vh",
              color: colours.CFIA_Font_White,
              fontWeight: props.switchLanguage ? "bold" : "normal",
            }}
          >
            FR
          </Typography>
        </Stack>
      </Box>
    </Box>
  );
};

export default Appbar;
