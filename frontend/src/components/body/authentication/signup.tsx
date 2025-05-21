import React from "react";
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

interface params {
  setSignUpOpen: React.Dispatch<React.SetStateAction<boolean>>;
  onSignIn: () => void;
}

const SignUp: React.FC<params> = (props): JSX.Element => {
  const handleClose = (): void => {
    props.setSignUpOpen(false);
  };
  const handleSubmit = (event: React.FormEvent<HTMLFormElement>): void => {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    Cookies.set("user-email", String(data.get("email") ?? ""), { expires: 30 });
    props.onSignIn();
    handleClose();
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
            />
            <FormControlLabel
              control={
                <Checkbox
                  value="remember"
                  color="primary"
                  size="small"
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
              <Grid item xs>
                <Link href="#" variant="body2">
                  Forgot password?
                </Link>
              </Grid>
              <Grid item>
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
