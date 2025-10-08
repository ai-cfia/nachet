import React from "react";
import {
  Dialog,
  DialogContent,
  Box,
  Button,
  CircularProgress,
  Typography,
} from "@mui/material";
import { useMsal, useIsAuthenticated } from "@azure/msal-react";
import { InteractionStatus } from "@azure/msal-browser";
import { colours } from "../../../styles/colours";

interface AuthPopupProps {
  open: boolean;
  onClose: () => void;
  apiScopeClaim: string;
}

const AuthPopup: React.FC<AuthPopupProps> = ({
  open,
  onClose,
  apiScopeClaim,
}) => {
  const { instance, inProgress } = useMsal();
  const isAuthenticated = useIsAuthenticated();

  const handleSignIn = async (): Promise<void> => {
    try {
      if (inProgress !== InteractionStatus.None) {
        console.warn("Interaction already in progress, please wait");
        return;
      }
      await instance.loginRedirect({
        scopes: [apiScopeClaim ?? ""],
      });
    } catch (error) {
      console.error("Login failed:", error);
    }
  };

  // Don't render if authenticated
  if (isAuthenticated) {
    return null;
  }

  const isLoading = inProgress !== InteractionStatus.None;

  return (
    <Dialog
      open={open}
      onClose={isLoading ? undefined : onClose}
      disableEscapeKeyDown={isLoading}
      maxWidth="sm"
      fullWidth
      slotProps={{
        paper: {
          sx: {
            borderRadius: 1,
            padding: "2vh",
          },
        },
      }}
    >
      <DialogContent>
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            minHeight: "20vh",
            gap: "3vh",
          }}
        >
          {isLoading ? (
            <>
              <CircularProgress
                size="8vh"
                sx={{ color: colours.CFIA_Background_Blue }}
              />
              <Typography
                variant="h6"
                sx={{
                  fontSize: "2vh",
                  fontWeight: 500,
                  color: colours.CFIA_Font_Black,
                }}
              >
                Signing in...
              </Typography>
            </>
          ) : (
            <>
              <Typography
                variant="h5"
                sx={{
                  fontSize: "2.5vh",
                  fontWeight: 600,
                  color: colours.CFIA_Font_Black,
                  textAlign: "center",
                }}
              >
                Authentication Required
              </Typography>
              <Typography
                variant="body1"
                sx={{
                  fontSize: "1.5vh",
                  color: colours.CFIA_Font_Black,
                  textAlign: "center",
                }}
              >
                Please sign in to access the application
              </Typography>
              <Button
                variant="outlined"
                onClick={handleSignIn}
                sx={{
                  marginTop: "2vh",
                  borderRadius: "0.4vh",
                  paddingTop: "1vh",
                  paddingBottom: "1vh",
                  paddingLeft: "3vh",
                  paddingRight: "3vh",
                  fontSize: "1.5vh",
                  fontWeight: 600,
                  border: `0.2vh solid ${colours.CFIA_Background_Blue}`,
                  color: colours.CFIA_Background_Blue,
                  "&:hover": {
                    backgroundColor: colours.CFIA_Background_Blue,
                    color: colours.CFIA_Background_White,
                    border: `0.2vh solid ${colours.CFIA_Background_Blue}`,
                    transition: "0.2s ease-in-out all",
                  },
                }}
              >
                SIGN IN
              </Button>
            </>
          )}
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default AuthPopup;
