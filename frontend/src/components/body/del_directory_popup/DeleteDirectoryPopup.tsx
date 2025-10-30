import React from "react";
import {
  Box,
  Dialog,
  DialogContent,
  IconButton,
  Button,
  Typography,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { colours } from "@styles/colours";
import { useBackendUrl } from "@hooks";
import { useMsal, useIsAuthenticated } from "@azure/msal-react";
import { InteractionStatus } from "@azure/msal-browser";
import { acquireAccessToken } from "@common/auth";
import { deleteAzureStorageDir } from "@common/api";
import { AzureStorageDirectoryItem } from "@common/types";

interface params {
  setDelDirectoryOpen: React.Dispatch<React.SetStateAction<boolean>>;
  curDir: AzureStorageDirectoryItem | null;
  setCurDir: React.Dispatch<
    React.SetStateAction<AzureStorageDirectoryItem | null>
  >;
  setReadAzureStorage: React.Dispatch<React.SetStateAction<boolean>>;
  apiScopeClaim: string;
}

const DeleteDirectoryPopup: React.FC<params> = (props) => {
  const {
    apiScopeClaim,
    setDelDirectoryOpen,
    curDir,
    setCurDir,
    setReadAzureStorage,
  } = props;
  const backendURL = useBackendUrl();
  const { instance: msalInstance, inProgress } = useMsal();
  const isAuthenticated = useIsAuthenticated();

  const handleDelFromDirectory = (): void => {
    if (!isAuthenticated) {
      alert("You must be signed in to delete a directory");
      return;
    }

    if (inProgress !== InteractionStatus.None) {
      alert("Authentication in progress, please wait");
      return;
    }

    if (!curDir) {
      alert("No directory selected to delete");
      return;
    }

    acquireAccessToken(msalInstance, [apiScopeClaim])
      .then((accessToken) => {
        // makes a post request to the backend to delete a directory in azure storage
        return deleteAzureStorageDir({
          backendUrl: backendURL,
          folderName: curDir.folderName,
          accessToken,
        });
      })
      .then(() => {
        setCurDir(null);
        setReadAzureStorage((prev) => !prev);
      })
      .catch((error) => {
        alert("Error deleting directory, see console for more details");
        console.error(error);
      });
  };

  const handleClose = (): void => {
    setDelDirectoryOpen(false);
  };
  const handleYes = (): void => {
    handleDelFromDirectory();
    setDelDirectoryOpen(false);
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
              Delete Directory
            </Typography>
            <IconButton onClick={handleClose} size="small">
              <CloseIcon />
            </IconButton>
          </Box>
          <Typography
            variant="body1"
            sx={{
              fontSize: "1.5vh",
              fontWeight: 500,
              color: colours.CFIA_Font_Black,
              textAlign: "center",
              marginTop: "2vh",
              marginBottom: "2vh",
            }}
          >
            Are you sure you want to delete {curDir?.folderName}?
          </Typography>
          <Box
            sx={{
              display: "flex",
              flexDirection: "row",
              alignItems: "center",
              justifyContent: "center",
              marginTop: "2vh",
              marginBottom: "1vh",
              gap: "2vh",
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
                border: `0.15vh solid #d32f2f`,
                color: "#d32f2f",
                "&:hover": {
                  backgroundColor: "#d32f2f",
                  color: colours.CFIA_Background_White,
                  border: `0.15vh solid #d32f2f`,
                  transition: "0.2s ease-in-out all",
                },
              }}
              onClick={handleYes}
            >
              Delete
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

export default DeleteDirectoryPopup;
