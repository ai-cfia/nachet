import React from "react";
import { Box, Button, CardHeader, IconButton, Typography } from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { Overlay, InfoContainer } from "../authentication/signupElements";
import { colours } from "../../../styles/colours";
import { useAuth } from "../../../common/auth/useAuth";

interface OAuthLoginProps {
  setSignUpOpen: React.Dispatch<React.SetStateAction<boolean>>;
}

const OAuthLogin: React.FC<OAuthLoginProps> = ({ setSignUpOpen }) => {
  const { login } = useAuth();

  const handleClose = (): void => {
    setSignUpOpen(false);
  };

  const handleLogin = async (): Promise<void> => {
    try {
      await login();
      handleClose();
    } catch (error) {
      console.error("Login failed:", error);
    }
  };

  return (
    <Overlay>
      <Box
        sx={{
          width: "20vw",
          height: "fit-content",
          zIndex: 30,
          border: `0.01vh solid LightGrey`,
          borderRadius: 1,
          background: colours.CFIA_Background_White,
        }}
        boxShadow={1}
      >
        <CardHeader
          title="Sign In"
          titleTypographyProps={{
            variant: "h6",
            align: "left",
            fontWeight: 600,
            fontSize: "1.3vh",
            color: colours.CFIA_Font_Black,
            zIndex: 30,
          }}
          action={
            <IconButton onClick={handleClose}>
              <CloseIcon />
            </IconButton>
          }
          sx={{ padding: "0.8vh 0.8vh 0.8vh 0.8vh" }}
        />
        <InfoContainer>
          <Box sx={{ p: 2 }}>
            <Typography
              variant="body2"
              color="textSecondary"
              sx={{ mb: 3, textAlign: "center" }}
            >
              Sign in with your organizational account to access Nachet
            </Typography>
            <Button
              fullWidth
              variant="contained"
              onClick={handleLogin}
              sx={{
                mt: 2,
                mb: 2,
                background: colours.CFIA_Background_Blue,
                "&:hover": {
                  backgroundColor: "#1976d2",
                },
              }}
            >
              Sign in with Microsoft
            </Button>
            <Typography
              variant="caption"
              color="textSecondary"
              sx={{ textAlign: "center", display: "block" }}
            >
              You will be redirected to Microsoft login
            </Typography>
          </Box>
        </InfoContainer>
      </Box>
    </Overlay>
  );
};

export default OAuthLogin;
