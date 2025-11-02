import React from "react";
import CFIALogo from "../../../assets/CFIA_blackfont.png";
import { Button, IconButton, Box } from "@mui/material";
import { colours } from "../../../styles/colours";
import AccountCircleIcon from "@mui/icons-material/AccountCircle";
import { useMsal, useIsAuthenticated } from "@azure/msal-react";
import { InteractionStatus } from "@azure/msal-browser";
import { useTranslation } from "react-i18next";

interface params {
  windowSize: {
    width: number;
    height: number;
  };
  apiScopeClaim: string;
}

const Navbar: React.FC<params> = (props) => {
  const { instance, inProgress, accounts } = useMsal();
  const isAuthenticated = useIsAuthenticated();
  const { apiScopeClaim } = props;
  const { t } = useTranslation("header");
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
      if (inProgress !== InteractionStatus.None) {
        console.warn("Interaction already in progress, please wait");
        return;
      }
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

  return (
    <Box
      component="nav"
      sx={{
        backgroundColor: colours.CFIA_Background_White,
        color: colours.CFIA_Background_White,
        height: "4vh",
        display: "flex",
        width: "100%",
        justifyContent: "center",
        alignItems: "center",
        position: "sticky",
        top: 0,
        zIndex: 0,
      }}
    >
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          height: "4vh",
          zIndex: 0,
          width: "100%",
          padding: "0 1.5vw",
        }}
      >
        <Box
          component="img"
          src={CFIALogo}
          alt={t("navbar.logoAlt")}
          sx={{
            width: "27vh",
            height: "fit-content",
            objectFit: "contain",
            margin: "auto",
            marginLeft: 0,
            marginRight: 0,
          }}
        />

        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            listStyle: "none",
            textAlign: "center",
          }}
        >
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
              {t("navbar.signIn")}
            </Button>
          )}
          {isAuthenticated && (
            <Box sx={{ marginRight: "1.6vh" }}>
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
                {accounts[0] && (
                  <Box
                    component="span"
                    sx={{
                      color: colours.CFIA_Font_Black,
                      fontSize: "1rem",
                      marginRight: "1rem",
                    }}
                  >
                    {accounts[0].username}
                  </Box>
                )}
                <AccountCircleIcon
                  sx={{
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
            </Box>
          )}
        </Box>
      </Box>
    </Box>
  );
};

export default Navbar;
