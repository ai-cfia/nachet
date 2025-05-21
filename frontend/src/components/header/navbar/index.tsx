import React from "react";
import CFIALogo from "../../../assets/CFIA_blackfont.png";
import { Nav, NavbarContainer, NavLogo, NavMenu } from "./indexElements";
import { Button, IconButton } from "@mui/material";
import { colours } from "../../../styles/colours";
import AccountCircleIcon from "@mui/icons-material/AccountCircle";

interface params {
  windowSize: {
    width: number;
    height: number;
  };
  signedIn: boolean;
  setSignedIn: React.Dispatch<React.SetStateAction<boolean>>;
  setSignUpOpen: React.Dispatch<React.SetStateAction<boolean>>;
  signUpOpen: boolean;
}

const Navbar: React.FC<params> = (props) => {
  const buttonStyle = {
    marginRight: 0,
    marginLeft: 0,
    borderRadius: "0.4vh",
    paddingTop: "0.3vh",
    paddingBottom: "0.3vh",
    paddingLeft: "0.7vh",
    paddingRight: "0.7vh",
    fontSize: "1.17vh",
    width: "7vh",
    border: `0.01vh solid LightGrey`,
    color: colours.CFIA_Font_Black,
    "&:hover": {
      backgroundColor: "#F5F5F5",
      transition: "0.1s ease-in-out all",
      border: `0.01vh solid LightGrey`,
    },
  };
  return (
    <Nav width={props.windowSize.width} height={props.windowSize.height}>
      <NavbarContainer
        width={props.windowSize.width}
        height={props.windowSize.height}
      >
        <NavLogo
          src={CFIALogo}
          alt="CFIA Logo"
          width={props.windowSize.width}
        />

        <NavMenu>
          {!props.signedIn && (
            <Button
              variant="outlined"
              onClick={() => {
                props.setSignUpOpen(true);
              }}
              sx={buttonStyle}
            >
              SIGN IN
            </Button>
          )}
          {props.signedIn && (
            <div style={{ marginRight: "1.6vh" }}>
              <IconButton
                sx={{ padding: 0, marginTop: "0.27vh", marginRight: "0.4vh" }}
                onClick={() => {
                  props.setSignedIn(!props.signedIn);
                }}
              >
                <AccountCircleIcon
                  style={{
                    color: colours.CFIA_Background_Blue,
                    fontSize: "3vh",
                    marginTop: 0,
                    marginBottom: 0,
                    paddingTop: 0,
                    paddingBottom: 0,
                    marginRight: 0,
                    marginLeft: 0,
                  }}
                />
              </IconButton>
            </div>
          )}
        </NavMenu>
      </NavbarContainer>
    </Nav>
  );
};

export default Navbar;
