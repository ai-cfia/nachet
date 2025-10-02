import React, { useEffect } from "react";
import CFIALogo from "../../../assets/CFIA_blackfont.png";
import { Nav, NavbarContainer, NavLogo, NavMenu } from "./indexElements";
import { Button, IconButton } from "@mui/material";
import { colours } from "../../../styles/colours";
import AccountCircleIcon from "@mui/icons-material/AccountCircle";
import { useMsal, useIsAuthenticated } from "@azure/msal-react";

interface params {
  windowSize: {
    width: number;
    height: number;
  };
  setUuid: React.Dispatch<React.SetStateAction<string>>;
  setUserAccount: React.Dispatch<
    React.SetStateAction<import("@azure/msal-browser").AccountInfo | null>
  >;
  apiScopeClaim: string;
}

const Navbar: React.FC<params> = (props) => {
  const { instance, accounts, inProgress } = useMsal();
  const isAuthenticated = useIsAuthenticated();
  const { setUuid, setUserAccount, apiScopeClaim } = props;
  const logout = async (): Promise<void> => {
    try {
      await instance.logoutRedirect();
    } catch (error) {
      console.error("Logout failed:", error);
      throw error;
    }
  };
  const login = async (): Promise<void> => {
    try {
      await instance.loginRedirect({
        // scopes: ["openid", "profile", "email"],
        scopes: [apiScopeClaim ?? ""],
      });
    } catch (error) {
      console.error("Login failed:", error);
      throw error;
    }
  };
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

  useEffect(() => {
    if (inProgress === "none" && accounts.length > 0) {
      // https://github.com/AzureAD/microsoft-authentication-library-for-js/blob/dev/lib/msal-common/docs/Accounts.md
      setUuid(accounts[0].idTokenClaims?.oid ?? "");
      // console.log("User Account: ", accounts[0]);
      setUserAccount(accounts[0]);
      instance.setActiveAccount(accounts[0]);
    } else {
      setUuid("");
      setUserAccount(null);
    }
  }, [accounts, inProgress, instance, setUserAccount, setUuid]);

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
          {!isAuthenticated && (
            <Button
              variant="outlined"
              onClick={async () => {
                try {
                  await login();
                } catch (error) {
                  console.error("Login failed:", error);
                }
              }}
              sx={buttonStyle}
            >
              SIGN IN
            </Button>
          )}
          {isAuthenticated && (
            <div style={{ marginRight: "1.6vh" }}>
              <IconButton
                sx={{ padding: 0, marginTop: "0.27vh", marginRight: "0.4vh" }}
                onClick={async () => {
                  try {
                    await logout();
                  } catch (error) {
                    console.error("Logout failed:", error);
                  }
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
