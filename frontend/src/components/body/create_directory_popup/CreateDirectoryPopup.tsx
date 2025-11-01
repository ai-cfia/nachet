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
import { createOrGetFolder, updateFolder } from "@common/api";
import { normalizedPathSchema, safeUserInputSchema } from "@common/validation";
import { AzureStorageDirectoryItem } from "@common/types";

interface params {
  setCreateDirectoryOpen: React.Dispatch<React.SetStateAction<boolean>>;
  curDir: AzureStorageDirectoryItem | null;
  setCurDir: React.Dispatch<
    React.SetStateAction<AzureStorageDirectoryItem | null>
  >;
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
  const {
    setCreateDirectoryOpen,
    setCurDir,
    setReadAzureStorage,
    apiScopeClaim,
    mode,
    initialData,
  } = props;
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

  const handleCreateDirectory = (): void => {
    if (!isAuthenticated) {
      alert("You must be signed in to create a directory");
      return;
    }

    if (inProgress !== InteractionStatus.None) {
      alert("Authentication in progress, please wait");
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
      setValidationError(pathValidationResult.error.issues[0].message);
      return;
    }

    // Sanitize description using XSS protection schema
    const descriptionValidationResult =
      safeUserInputSchema.safeParse(descriptionInput);
    if (!descriptionValidationResult.success) {
      setDescriptionError(descriptionValidationResult.error.issues[0].message);
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
        setCreateDirectoryOpen(false);
        setCurDir(null);
        setReadAzureStorage((prev) => !prev);
      })
      .catch((error) => {
        const action = mode === "create" ? "creating" : "updating";
        alert(`Error ${action} directory, see console for more details`);
        console.error(error);
      });
  };

  const handleClose = (): void => {
    setCreateDirectoryOpen(false);
    setFolderNameInput("");
    setDescriptionInput("");
    setValidationError("");
    setDescriptionError("");
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
              {mode === "create" ? "Create New Directory" : "Edit Directory"}
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
            helperText={
              validationError ||
              "Directory will be created at root level. Use letters, numbers, hyphens, and underscores."
            }
            sx={{ fontSize: "1.2vh" }}
            size="small"
            placeholder="e.g., avena-fatua or mycology-samples"
          />
          <TextField
            id="input-description"
            label="Description (Optional)"
            variant="outlined"
            fullWidth
            multiline
            rows={3}
            InputLabelProps={{ shrink: true }}
            value={descriptionInput}
            onChange={(e) => {
              setDescriptionInput(e.target.value);
              if (descriptionError) {
                setDescriptionError("");
              }
            }}
            error={!!descriptionError}
            helperText={
              descriptionError ||
              "Optional description for this directory (max 500 characters)"
            }
            sx={{ fontSize: "1.2vh", marginTop: "2vh" }}
            size="small"
            placeholder="e.g., Sample collection from field trial 2025"
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
              {mode === "create" ? "Create" : "Update"}
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
