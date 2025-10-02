import React, { useState } from "react";
import { Overlay, InfoContainer, ButtonWrap } from "./indexElements";
import { Box, CardHeader, IconButton, TextField, Button } from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { colours } from "@styles/colours";
import { useBackendUrl } from "@hooks";
import { useMsal, useIsAuthenticated } from "@azure/msal-react";
import { InteractionStatus } from "@azure/msal-browser";
import { acquireAccessToken } from "@common/auth";
import { createAzureStorageDir } from "@common/api";
import { directoryNameSchema } from "@common/validation";

interface params {
  setCreateDirectoryOpen: React.Dispatch<React.SetStateAction<boolean>>;
  handeDirChange: (dir: string) => void;
  curDir: string;
  setCurDir: React.Dispatch<React.SetStateAction<string>>;
  setReadAzureStorage: React.Dispatch<React.SetStateAction<boolean>>;
  apiScopeClaim: string;
}

const CreateFolder: React.FC<params> = (props) => {
  const {
    setCreateDirectoryOpen,
    curDir,
    handeDirChange,
    setCurDir,
    setReadAzureStorage,
    apiScopeClaim,
  } = props;
  const backendURL = useBackendUrl();
  const [validationError, setValidationError] = useState<string>("");
  const { instance: msalInstance, inProgress } = useMsal();
  const isAuthenticated = useIsAuthenticated();

  const handleCreateDirectory = (): void => {
    if (!isAuthenticated) {
      alert("You must be signed in to create a directory");
      return;
    }

    if (inProgress !== InteractionStatus.None) {
      alert("Authentication in progress, please wait");
      return;
    }

    // Validate directory name
    const validationResult = directoryNameSchema.safeParse(curDir);
    if (!validationResult.success) {
      setValidationError(validationResult.error.issues[0].message);
      return;
    }

    // Clear any previous validation errors
    setValidationError("");

    acquireAccessToken(msalInstance, [apiScopeClaim])
      .then((accessToken) => {
        // makes a post request to the backend to create a new directory in azure storage
        return createAzureStorageDir({
          backendUrl: backendURL,
          folderName: curDir,
          accessToken,
        });
      })
      .then(() => {
        setCreateDirectoryOpen(false);
        setCurDir("General");
        setReadAzureStorage((prev) => !prev);
      })
      .catch((error) => {
        alert("Error creating directory, see console for more details");
        console.error(error);
      });
  };

  const handleClose = (): void => {
    setCreateDirectoryOpen(false);
    handeDirChange("General");
    setValidationError("");
  };

  const handleInputChange = (
    event: React.ChangeEvent<HTMLInputElement>,
  ): void => {
    const value = event.target.value;
    handeDirChange(value);

    // Clear validation error when user starts typing
    if (validationError) {
      setValidationError("");
    }
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
          title="Create New Directory"
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
          <TextField
            id="outlined-basic"
            label="Directory Name"
            variant="outlined"
            fullWidth
            InputLabelProps={{ shrink: true }}
            onChange={handleInputChange}
            value={curDir}
            error={!!validationError}
            helperText={validationError}
            sx={{ fontSize: "1.2vh" }}
            size="small"
          />
          <ButtonWrap>
            <Button
              variant="outlined"
              size="medium"
              sx={{
                marginRight: "0.9vh",
                marginLeft: 0,
                borderRadius: "0.4vh",
                paddingTop: "0.3vh",
                paddingBottom: "0.3vh",
                paddingLeft: "0.7vh",
                paddingRight: "0.7vh",
                fontSize: "1.17vh",
                width: "fit-content",
                border: `0.01vh solid LightGrey`,
                color: colours.CFIA_Font_Black,
                "&:hover": {
                  backgroundColor: "#F5F5F5",
                  transition: "0.1s ease-in-out all",
                  border: `0.01vh solid LightGrey`,
                },
              }}
              onClick={() => {
                handleCreateDirectory();
              }}
            >
              Create
            </Button>
            <Button
              variant="outlined"
              size="medium"
              sx={{
                marginRight: "0.9vh",
                marginLeft: 0,
                borderRadius: "0.4vh",
                paddingTop: "0.3vh",
                paddingBottom: "0.3vh",
                paddingLeft: "0.7vh",
                paddingRight: "0.7vh",
                fontSize: "1.17vh",
                width: "fit-content",
                border: `0.01vh solid LightGrey`,
                color: colours.CFIA_Font_Black,
                "&:hover": {
                  backgroundColor: "#F5F5F5",
                  transition: "0.1s ease-in-out all",
                  border: `0.01vh solid LightGrey`,
                },
              }}
              onClick={handleClose}
            >
              Cancel
            </Button>
          </ButtonWrap>
        </InfoContainer>
      </Box>
    </Overlay>
  );
};

export default CreateFolder;
