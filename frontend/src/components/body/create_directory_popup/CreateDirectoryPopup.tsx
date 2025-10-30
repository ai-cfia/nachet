import React, { useState } from "react";
import {
  Box,
  Dialog,
  DialogContent,
  IconButton,
  TextField,
  Button,
  Typography,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { colours } from "@styles/colours";
import { useBackendUrl } from "@hooks";
import { useMsal, useIsAuthenticated } from "@azure/msal-react";
import { InteractionStatus } from "@azure/msal-browser";
import { acquireAccessToken } from "@common/auth";
import { createAzureStorageDir } from "@common/api";
import { directoryNameSchema } from "@common/validation";
import { AzureStorageDirectoryItem } from "@common/types";

interface params {
  setCreateDirectoryOpen: React.Dispatch<React.SetStateAction<boolean>>;
  curDir: AzureStorageDirectoryItem | null;
  setCurDir: React.Dispatch<
    React.SetStateAction<AzureStorageDirectoryItem | null>
  >;
  setReadAzureStorage: React.Dispatch<React.SetStateAction<boolean>>;
  apiScopeClaim: string;
}

const CreateFolder: React.FC<params> = (props) => {
  const {
    setCreateDirectoryOpen,
    setCurDir,
    setReadAzureStorage,
    apiScopeClaim,
  } = props;
  const backendURL = useBackendUrl();
  const [folderNameInput, setFolderNameInput] = useState<string>("");
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
    const validationResult = directoryNameSchema.safeParse(folderNameInput);
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
          folderName: folderNameInput,
          accessToken,
        });
      })
      .then(() => {
        setCreateDirectoryOpen(false);
        setCurDir(null);
        setReadAzureStorage((prev) => !prev);
      })
      .catch((error) => {
        alert("Error creating directory, see console for more details");
        console.error(error);
      });
  };

  const handleClose = (): void => {
    setCreateDirectoryOpen(false);
    setFolderNameInput("");
    setValidationError("");
  };

  const handleInputChange = (
    event: React.ChangeEvent<HTMLInputElement>,
  ): void => {
    const value = event.target.value;
    setFolderNameInput(value);

    // Clear validation error when user starts typing
    if (validationError) {
      setValidationError("");
    }
  };

  return (
    <Dialog
      open={true}
      onClose={handleClose}
      maxWidth="xs"
      fullWidth
      slotProps={{
        paper: {
          sx: {
            borderRadius: 1,
            padding: "1vh",
          },
        },
      }}
    >
      <DialogContent>
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
          }}
        >
          <Box
            sx={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "2vh",
            }}
          >
            <Typography
              variant="h6"
              sx={{
                fontWeight: 600,
                fontSize: "1.8vh",
                color: colours.CFIA_Font_Black,
              }}
            >
              Create New Directory
            </Typography>
            <IconButton onClick={handleClose} size="small">
              <CloseIcon />
            </IconButton>
          </Box>
          <TextField
            id="outlined-basic"
            label="Directory Name"
            variant="outlined"
            fullWidth
            InputLabelProps={{ shrink: true }}
            onChange={handleInputChange}
            value={folderNameInput}
            error={!!validationError}
            helperText={validationError}
            sx={{ fontSize: "1.2vh" }}
            size="small"
          />
          <Box
            sx={{
              display: "flex",
              flexDirection: "row",
              alignItems: "center",
              justifyContent: "center",
              marginTop: "2vh",
              marginBottom: "1vh",
              gap: "1vh",
            }}
          >
            <Button
              variant="outlined"
              size="medium"
              sx={{
                borderRadius: "0.4vh",
                paddingTop: "0.6vh",
                paddingBottom: "0.6vh",
                paddingLeft: "1.5vh",
                paddingRight: "1.5vh",
                fontSize: "1.17vh",
                width: "fit-content",
                border: `0.15vh solid ${colours.CFIA_Background_Blue}`,
                color: colours.CFIA_Background_Blue,
                "&:hover": {
                  backgroundColor: colours.CFIA_Background_Blue,
                  color: colours.CFIA_Background_White,
                  border: `0.15vh solid ${colours.CFIA_Background_Blue}`,
                  transition: "0.2s ease-in-out all",
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
                borderRadius: "0.4vh",
                paddingTop: "0.6vh",
                paddingBottom: "0.6vh",
                paddingLeft: "1.5vh",
                paddingRight: "1.5vh",
                fontSize: "1.17vh",
                width: "fit-content",
                border: `0.15vh solid LightGrey`,
                color: colours.CFIA_Font_Black,
                "&:hover": {
                  backgroundColor: "#F5F5F5",
                  transition: "0.2s ease-in-out all",
                  border: `0.15vh solid LightGrey`,
                },
              }}
              onClick={handleClose}
            >
              Cancel
            </Button>
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default CreateFolder;
