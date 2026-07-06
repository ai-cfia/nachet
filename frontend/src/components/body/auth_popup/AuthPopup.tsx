import {
  Dialog,
  DialogContent,
  Box,
  Button,
  CircularProgress,
  Typography,
} from "@mui/material";
import { colours } from "../../../styles/colours";
import { useTranslation } from "react-i18next";
import { useNachetAuth } from "@auth";

interface AuthPopupProps {
  open: boolean;
  onClose: () => void;
}

const AuthPopup = ({ open, onClose }: AuthPopupProps) => {
  const { t } = useTranslation("popups");
  const { isAuthenticated, isLoading, login } = useNachetAuth();

  const handleSignIn = async (): Promise<void> => {
    try {
      await login();
    } catch (error) {
      console.error("Login failed:", error);
    }
  };

  // Don't render if authenticated
  if (isAuthenticated) {
    return null;
  }

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
                {t("auth.signingIn")}
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
                {t("auth.title")}
              </Typography>
              <Typography
                variant="body1"
                sx={{
                  fontSize: "1.5vh",
                  color: colours.CFIA_Font_Black,
                  textAlign: "center",
                }}
              >
                {t("auth.message")}
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
                {t("auth.signInButton")}
              </Button>
            </>
          )}
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default AuthPopup;
