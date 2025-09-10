import React, { useState } from "react";
import { Overlay, InfoContainer } from "./signupElements";
import {
  Box,
  CardHeader,
  IconButton,
  TextField,
  Button,
  Grid,
  FormControlLabel,
  Link,
  Checkbox,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { colours } from "../../../styles/colours";
import Cookies from "js-cookie";
import { emailSchema, passwordSchema, booleanSchema } from "@common/validation";

interface params {
  setSignUpOpen: React.Dispatch<React.SetStateAction<boolean>>;
  onSignIn: () => void;
}

const SignUp: React.FC<params> = (props) => {
  const [email, setEmail] = useState<string>("");
  const [password, setPassword] = useState<string>("");
  const [rememberMe, setRememberMe] = useState<boolean>(false);
  const [emailError, setEmailError] = useState<string>("");
  const [passwordError, setPasswordError] = useState<string>("");

  const handleClose = (): void => {
    props.setSignUpOpen(false);
    // Clear form and errors
    setEmail("");
    setPassword("");
    setRememberMe(false);
    setEmailError("");
    setPasswordError("");
  };

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>): void => {
    event.preventDefault();

    // Validate email
    const emailValidation = emailSchema.safeParse(email);
    if (!emailValidation.success) {
      setEmailError(emailValidation.error.issues[0].message);
      return;
    }

    // Validate password
    const passwordValidation = passwordSchema.safeParse(password);
    if (!passwordValidation.success) {
      setPasswordError(passwordValidation.error.issues[0].message);
      return;
    }

    // Validate remember me checkbox
    const rememberValidation = booleanSchema.safeParse(rememberMe);
    if (!rememberValidation.success) {
      // This shouldn't happen for a boolean, but just in case
      return;
    }

    // Clear errors
    setEmailError("");
    setPasswordError("");

    // Store sanitized email
    Cookies.set("user-email", emailValidation.data, { expires: 30 });
    props.onSignIn();
    handleClose();
  };

  const handleEmailChange = (
    event: React.ChangeEvent<HTMLInputElement>,
  ): void => {
    const value = event.target.value;
    setEmail(value);
    if (emailError) setEmailError("");
  };

  const handlePasswordChange = (
    event: React.ChangeEvent<HTMLInputElement>,
  ): void => {
    const value = event.target.value;
    setPassword(value);
    if (passwordError) setPasswordError("");
  };

  const handleRememberMeChange = (
    event: React.ChangeEvent<HTMLInputElement>,
  ): void => {
    setRememberMe(event.target.checked);
  };

  return (
    <Overlay>
      <Box
        sx={{
          width: "15vw",
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
          <Box
            component="form"
            onSubmit={handleSubmit}
            noValidate
            sx={{ mt: 1 }}
          >
            <TextField
              margin="normal"
              required
              fullWidth
              id="email"
              label="Email Address"
              name="email"
              autoComplete="email"
              autoFocus
              size="small"
              value={email}
              onChange={handleEmailChange}
              error={!!emailError}
              helperText={emailError}
            />
            <TextField
              margin="normal"
              required
              fullWidth
              name="password"
              label="Password"
              type="password"
              id="password"
              autoComplete="current-password"
              size="small"
              value={password}
              onChange={handlePasswordChange}
              error={!!passwordError}
              helperText={passwordError}
            />
            <FormControlLabel
              control={
                <Checkbox
                  value="remember"
                  color="primary"
                  size="small"
                  checked={rememberMe}
                  onChange={handleRememberMeChange}
                  sx={{ fontSize: "0.5vh" }}
                />
              }
              label="Remember me"
            />
            <Button
              type="submit"
              fullWidth
              variant="contained"
              sx={{ mt: 3, mb: 2, background: colours.CFIA_Background_Blue }}
            >
              Sign In
            </Button>
            <Grid container>
              <Grid size={{ xs: 2 }}>
                <Link href="#" variant="body2">
                  Forgot password?
                </Link>
              </Grid>
              <Grid>
                <Link href="#" variant="body2">
                  {"Don't have an account? Sign Up"}
                </Link>
              </Grid>
            </Grid>
          </Box>
        </InfoContainer>
      </Box>
    </Overlay>
  );
};

export default SignUp;
