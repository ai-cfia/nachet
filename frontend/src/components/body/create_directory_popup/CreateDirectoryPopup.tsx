import React, { useState } from "react";
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
import { createOrGetFolder, updateFolder } from "@common/api";
import { normalizedPathSchema, safeUserInputSchema } from "@common/validation";
import { getZodErrorKey } from "@common/zodErrorMap";
import { useTranslation } from "react-i18next";
import { FolderFieldsGroup } from "../folder_fields_group/FolderFieldsGroup";
import { useDirectoryModalStore } from "@stores/useDirectoryModalStore";
import { useFolderStore } from "@stores/useFolderStore";
import { useNotificationStore } from "@stores/useNotificationStore";

interface params {
  setReadAzureStorage: React.Dispatch<React.SetStateAction<boolean>>;
  apiScopeClaim: string;
  mode: "create" | "edit";
  initialData?: {
    folderId: string;
    folderName: string;
    description: string;
  };
}

const CreateFolder: React.FC<params> = (props) => {
  const { t } = useTranslation("popups");
  const { t: tValidation } = useTranslation("validation");
  const { setReadAzureStorage, apiScopeClaim, mode, initialData } = props;
  const { closeCreateDirectory, closeEditDirectory } = useDirectoryModalStore();
  const { setCurDir } = useFolderStore();
  const backendURL = useBackendUrl();
  const [folderNameInput, setFolderNameInput] = useState<string>(
    mode === "edit" && initialData ? initialData.folderName : "",
  );
  const [descriptionInput, setDescriptionInput] = useState<string>(
    mode === "edit" && initialData ? initialData.description || "" : "",
  );
  const [validationError, setValidationError] = useState<string>("");
  const [descriptionError, setDescriptionError] = useState<string>("");
  const { instance: msalInstance, inProgress } = useMsal();
  const isAuthenticated = useIsAuthenticated();
  const { addError, addWarning } = useNotificationStore();

  const handleCreateDirectory = (): void => {
    if (!isAuthenticated) {
      addError(t("createDirectory.errors.signInRequired"), "auth");
      return;
    }

    if (inProgress !== InteractionStatus.None) {
      addWarning(t("createDirectory.errors.authInProgress"), 8000);
      return;
    }

    // Normalize folder name (lowercase, replace invalid chars with hyphens)
    const normalizedPath = folderNameInput
      .toLowerCase()
      .replace(/[^a-z0-9/._-]/g, "-")
      .replace(/^\/+|\/+$/g, ""); // Remove leading/trailing slashes

    // Validate normalized path
    const pathValidationResult = normalizedPathSchema.safeParse(normalizedPath);
    if (!pathValidationResult.success) {
      setValidationError(
        tValidation(getZodErrorKey(pathValidationResult.error)),
      );
      return;
    }

    // Sanitize description using XSS protection schema
    const descriptionValidationResult =
      safeUserInputSchema.safeParse(descriptionInput);
    if (!descriptionValidationResult.success) {
      setDescriptionError(
        tValidation(getZodErrorKey(descriptionValidationResult.error)),
      );
      return;
    }

    // Clear any previous validation errors
    setValidationError("");
    setDescriptionError("");

    const sanitizedDescription = descriptionValidationResult.data;

    acquireAccessToken(msalInstance, [apiScopeClaim])
      .then(async (accessToken) => {
        if (mode === "create") {
          // Create directory at root level using new API
          const result = await createOrGetFolder({
            backendUrl: backendURL,
            accessToken,
            normalizedPath,
            description: sanitizedDescription,
          });
          console.log(`Folder created/retrieved: ${result.folder_id}`);
        } else {
          // Edit mode - update existing folder
          if (!initialData) {
            throw new Error("Initial data required for edit mode");
          }
          const result = await updateFolder({
            backendUrl: backendURL,
            accessToken,
            folderId: initialData.folderId,
            name: normalizedPath,
            description: sanitizedDescription,
          });
          console.log(`Folder updated: ${result.id}`);
        }
        if (mode === "create") {
          closeCreateDirectory();
        } else {
          closeEditDirectory();
        }
        setCurDir(null);
        setReadAzureStorage((prev) => !prev);
      })
      .catch((error) => {
        const errorMessage =
          mode === "create"
            ? t("createDirectory.errors.createFailed")
            : t("createDirectory.errors.updateFailed");
        addError(errorMessage, "directory");
        console.error(
          "Directory operation failed:",
          error instanceof Error ? error.message : String(error),
        );
      });
  };

  const handleClose = (): void => {
    if (mode === "create") {
      closeCreateDirectory();
    } else {
      closeEditDirectory();
    }
    setFolderNameInput("");
    setDescriptionInput("");
    setValidationError("");
    setDescriptionError("");
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
              {mode === "create"
                ? t("createDirectory.titleCreate")
                : t("createDirectory.titleEdit")}
            </Typography>
            <IconButton onClick={handleClose} size="small">
              <CloseIcon />
            </IconButton>
          </Box>
          <FolderFieldsGroup
            folderName={folderNameInput}
            folderDescription={descriptionInput}
            onFolderNameChange={(value) => {
              setFolderNameInput(value);
              if (validationError) {
                setValidationError("");
              }
            }}
            onFolderDescriptionChange={(value) => {
              setDescriptionInput(value);
              if (descriptionError) {
                setDescriptionError("");
              }
            }}
            folderNameError={validationError}
            folderDescriptionError={descriptionError}
            sx={{ marginTop: "0px" }}
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
              {mode === "create"
                ? t("createDirectory.createButton")
                : t("createDirectory.updateButton")}
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
              {t("createDirectory.cancelButton")}
            </Button>
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default CreateFolder;
