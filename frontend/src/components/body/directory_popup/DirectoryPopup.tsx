import React, { useState } from "react";
import {
  Box,
  Dialog,
  DialogContent,
  IconButton,
  Typography,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { colours } from "@styles/colours";
import { useBackendUrl } from "@hooks";
import { useMsal, useIsAuthenticated } from "@azure/msal-react";
import { InteractionStatus } from "@azure/msal-browser";
import { acquireAccessToken } from "@common/auth";
import { createOrGetFolder, updateFolder, deleteFolder } from "@common/api";
import { normalizedPathSchema, descriptionSchema } from "@common/validation";
import { getZodErrorKey } from "@common/zodErrorMap";
import { useTranslation } from "react-i18next";
import {
  useZodFieldValidation,
  ERROR_KEY_MAPPINGS,
} from "@hooks/useZodFieldValidation";
import { FolderFieldsGroup } from "../folder_fields_group/FolderFieldsGroup";
import { PopupActionButtons } from "@components/common";
import { useDirectoryModalStore } from "@stores/useDirectoryModalStore";
import { useFolderStore } from "@stores/useFolderStore";
import { useNotificationStore } from "@stores/useNotificationStore";

interface params {
  setReadAzureStorage: React.Dispatch<React.SetStateAction<boolean>>;
  apiScopeClaim: string;
  mode: "create" | "edit" | "delete";
  initialData?: {
    folderId: string;
    folderName: string;
    description: string;
  };
}

const DirectoryPopup: React.FC<params> = (props) => {
  const { t } = useTranslation("popups");
  const { t: tValidation } = useTranslation("validation");
  const { setReadAzureStorage, apiScopeClaim, mode, initialData } = props;
  const { closeCreateDirectory, closeEditDirectory, closeDeleteDirectory } =
    useDirectoryModalStore();
  const { setCurDir } = useFolderStore();
  const backendURL = useBackendUrl();
  const [folderNameInput, setFolderNameInput] = useState<string>(
    (mode === "edit" || mode === "delete") && initialData
      ? initialData.folderName
      : "",
  );
  const [descriptionInput, setDescriptionInput] = useState<string>(
    (mode === "edit" || mode === "delete") && initialData
      ? initialData.description || ""
      : "",
  );
  const [validationError, setValidationError] = useState<string>("");
  const [descriptionError, setDescriptionError] = useState<string>("");
  const { instance: msalInstance, inProgress } = useMsal();
  const isAuthenticated = useIsAuthenticated();
  const { addError, addWarning } = useNotificationStore();

  // Zod validation hook for auto-normalization on blur
  const descriptionValidation = useZodFieldValidation(
    descriptionSchema,
    descriptionInput,
    setDescriptionInput,
    setDescriptionError,
    ERROR_KEY_MAPPINGS.description,
  );

  const handleDirectoryOperation = (): void => {
    if (!isAuthenticated) {
      const errorKey =
        mode === "delete"
          ? "deleteDirectory.errors.signInRequired"
          : "createDirectory.errors.signInRequired";
      addError(t(errorKey), "auth");
      return;
    }

    if (inProgress !== InteractionStatus.None) {
      const warningKey =
        mode === "delete"
          ? "deleteDirectory.errors.authInProgress"
          : "createDirectory.errors.authInProgress";
      addWarning(t(warningKey), 8000);
      return;
    }

    // For delete mode, skip validation and go straight to deletion
    if (mode === "delete") {
      if (!initialData) {
        addError(t("deleteDirectory.errors.noSelection"), "directory");
        return;
      }

      acquireAccessToken(msalInstance, [apiScopeClaim])
        .then(async (accessToken) => {
          await deleteFolder({
            backendUrl: backendURL,
            accessToken,
            folderId: initialData.folderId,
          });
          console.log(`Folder deleted: ${initialData.folderId}`);
          closeDeleteDirectory();
          setCurDir(null);
          setReadAzureStorage((prev) => !prev);
        })
        .catch((error) => {
          addError(t("deleteDirectory.errors.deleteFailed"), "directory");
          console.error(
            "Directory deletion failed:",
            error instanceof Error ? error.message : String(error),
          );
        });
      return;
    }

    // For create/edit modes, validate inputs
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

    // Validate description - required, using consistent descriptionSchema
    const descriptionValidationResult =
      descriptionSchema.safeParse(descriptionInput);
    if (!descriptionValidationResult.success) {
      const issue = descriptionValidationResult.error.issues[0];
      if (issue.code === "too_small") {
        setDescriptionError(tValidation("description.empty"));
      } else if (issue.code === "too_big") {
        setDescriptionError(tValidation("description.tooLong"));
      } else {
        setDescriptionError(
          tValidation(getZodErrorKey(descriptionValidationResult.error)),
        );
      }
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
          console.log(`Folder created/retrieved: ${result.folderId}`);
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
    } else if (mode === "edit") {
      closeEditDirectory();
    } else {
      closeDeleteDirectory();
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
                : mode === "edit"
                  ? t("createDirectory.titleEdit")
                  : t("deleteDirectory.title")}
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
            onFolderDescriptionChange={descriptionValidation.onChange}
            onFolderDescriptionBlur={descriptionValidation.onBlur}
            folderNameError={validationError}
            folderDescriptionError={descriptionError}
            disabled={mode === "delete"}
            sx={{ marginTop: "0px" }}
          />
          <PopupActionButtons
            onSave={handleDirectoryOperation}
            onCancel={handleClose}
            saveLabel={
              mode === "create"
                ? t("createDirectory.createButton")
                : mode === "edit"
                  ? t("createDirectory.updateButton")
                  : t("deleteDirectory.deleteButton")
            }
            sx={{ marginTop: "2vh", marginBottom: "1vh" }}
          />
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default DirectoryPopup;
