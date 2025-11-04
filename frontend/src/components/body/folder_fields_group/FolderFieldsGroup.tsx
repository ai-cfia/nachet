import { TextField, Box } from "@mui/material";
import { useTranslation } from "react-i18next";
import { descriptionSchema } from "@common/validation";

interface FolderFieldsGroupProps {
  folderName: string;
  folderDescription: string;
  onFolderNameChange: (value: string) => void;
  onFolderDescriptionChange: (value: string) => void;
  onFolderNameBlur?: () => void;
  onFolderDescriptionBlur?: () => void;
  folderNameError?: string;
  folderDescriptionError?: string;
  disabled?: boolean;
  folderNamePlaceholder?: string;
  folderDescriptionPlaceholder?: string;
  folderNameHelper?: string;
  folderDescriptionHelper?: string;
  sx?: {
    marginTop?: string;
    width?: string;
  };
}

export const FolderFieldsGroup = (props: FolderFieldsGroupProps) => {
  const {
    folderName,
    folderDescription,
    onFolderNameChange,
    onFolderDescriptionChange,
    onFolderNameBlur,
    onFolderDescriptionBlur,
    folderNameError,
    folderDescriptionError,
    disabled = false,
    folderNamePlaceholder,
    folderDescriptionPlaceholder,
    folderNameHelper,
    folderDescriptionHelper,
    sx,
  } = props;

  const { t } = useTranslation("popups");

  // Normalize folder name: remove invalid chars and trailing dashes/underscores
  const normalizeFolderName = (value: string): string => {
    return value
      .replace(/[^a-zA-Z0-9._-]/g, "") // Remove invalid characters
      .replace(/[-_]+$/, "") // Remove trailing dashes and underscores
      .trim();
  };

  const handleFolderNameBlur = () => {
    // Use parent's blur handler if provided, otherwise normalize internally
    if (onFolderNameBlur) {
      onFolderNameBlur();
    } else {
      const normalized = normalizeFolderName(folderName);
      if (normalized !== folderName) {
        onFolderNameChange(normalized);
      }
    }
  };

  // Normalize folder description using Zod schema (consistent with other description fields)
  const handleFolderDescriptionBlur = () => {
    // Use parent's blur handler if provided, otherwise normalize internally
    if (onFolderDescriptionBlur) {
      onFolderDescriptionBlur();
    } else {
      const result = descriptionSchema.safeParse(folderDescription);
      if (result.success) {
        // Only update if normalization changed the value
        if (result.data !== folderDescription) {
          onFolderDescriptionChange(result.data);
        }
      }
      // Note: Parent components handle validation and error display on submit
    }
  };

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        gap: "10px",
        width: "100%",
      }}
    >
      <TextField
        id="input-folder-name"
        label={t("createDirectory.directoryNameLabel")}
        variant="outlined"
        value={folderName}
        onChange={(e) => onFolderNameChange(e.target.value)}
        onBlur={handleFolderNameBlur}
        sx={{
          marginTop: sx?.marginTop || "0px",
          width: sx?.width || "100%",
        }}
        error={!!folderNameError}
        helperText={
          folderNameError ||
          folderNameHelper ||
          t("createDirectory.directoryNameHelper")
        }
        disabled={disabled}
        placeholder={
          folderNamePlaceholder || t("createDirectory.directoryNamePlaceholder")
        }
        fullWidth
        InputLabelProps={{ shrink: true }}
        size="small"
      />

      <TextField
        id="input-folder-description"
        label={t("createDirectory.descriptionLabel")}
        variant="outlined"
        value={folderDescription}
        onChange={(e) => onFolderDescriptionChange(e.target.value)}
        onBlur={handleFolderDescriptionBlur}
        sx={{
          width: sx?.width || "100%",
        }}
        multiline
        rows={2}
        error={!!folderDescriptionError}
        helperText={
          folderDescriptionError ||
          folderDescriptionHelper ||
          t("createDirectory.descriptionHelper")
        }
        disabled={disabled}
        placeholder={
          folderDescriptionPlaceholder ||
          t("createDirectory.descriptionPlaceholder")
        }
        fullWidth
        InputLabelProps={{ shrink: true }}
        size="small"
      />
    </Box>
  );
};
