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
import { deleteFolder } from "@common/api";
import { useTranslation } from "react-i18next";
import { useDirectoryModalStore } from "@stores/useDirectoryModalStore";
import { useFolderStore } from "@stores/useFolderStore";
import { useNotificationStore } from "@stores/useNotificationStore";

interface params {
  setReadAzureStorage: React.Dispatch<React.SetStateAction<boolean>>;
  apiScopeClaim: string;
}

const DeleteDirectoryPopup: React.FC<params> = (props) => {
  const { t } = useTranslation("popups");
  const { apiScopeClaim, setReadAzureStorage } = props;
  const { closeDeleteDirectory } = useDirectoryModalStore();
  const { curDir, setCurDir } = useFolderStore();
  const backendURL = useBackendUrl();
  const { instance: msalInstance, inProgress } = useMsal();
  const isAuthenticated = useIsAuthenticated();
  const { addError, addWarning } = useNotificationStore();

  const handleDelFromDirectory = (): void => {
    if (!isAuthenticated) {
      addError(t("deleteDirectory.errors.signInRequired"), "auth");
      return;
    }

    if (inProgress !== InteractionStatus.None) {
      addWarning(t("deleteDirectory.errors.authInProgress"), 8000);
      return;
    }

    if (!curDir) {
      addWarning(t("deleteDirectory.errors.noSelection"), 8000);
      return;
    }

    acquireAccessToken(msalInstance, [apiScopeClaim])
      .then((accessToken) => {
        // Delete folder using the new DELETE /folders/{folder_id} endpoint
        return deleteFolder({
          backendUrl: backendURL,
          folderId: curDir.folderId,
          accessToken,
        });
      })
      .then((result) => {
        console.log(`Folder deleted: ${result.id}`);
        setCurDir(null);
        setReadAzureStorage((prev) => !prev);
      })
      .catch((error) => {
        addError(t("deleteDirectory.errors.deleteFailed"), "directory");
        console.error(
          "Delete folder failed:",
          error instanceof Error ? error.message : String(error),
        );
      });
  };

  const handleClose = (): void => {
    closeDeleteDirectory();
  };
  const handleYes = (): void => {
    handleDelFromDirectory();
    closeDeleteDirectory();
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
              {t("deleteDirectory.title")}
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
            {t("deleteDirectory.confirmMessage", {
              folderName: curDir?.folderName,
            })}
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
              {t("deleteDirectory.deleteButton")}
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
              {t("deleteDirectory.cancelButton")}
            </Button>
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default DeleteDirectoryPopup;
