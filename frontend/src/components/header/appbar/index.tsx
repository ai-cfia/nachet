import { AppbarWrap, AppbarContainer, AppbarHeader } from "./indexElements";
import { colours } from "../../../styles/colours";
import { Button } from "@mui/material";
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
    <AppbarWrap width={props.windowSize.width} height={props.windowSize.height}>
      <AppbarContainer
        width={props.windowSize.width}
        height={props.windowSize.height}
      >
        <AppbarHeader>Seed Classification Interface</AppbarHeader>
        <Button
          variant="outlined"
          onClick={() => {
            props.setSwitchLanguage(!props.switchLanguage);
          }}
          sx={buttonStyle}
        >
          {props.switchLanguage ? "EN" : "FR"}
        </Button>
      </AppbarContainer>
    </AppbarWrap>
  );
};

export default Appbar;
