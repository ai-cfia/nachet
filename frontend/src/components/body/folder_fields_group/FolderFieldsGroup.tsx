import { TextField, Box } from "@mui/material";
import { useTranslation } from "react-i18next";

interface FolderFieldsGroupProps {
  folderName: string;
  folderDescription: string;
  onFolderNameChange: (value: string) => void;
  onFolderDescriptionChange: (value: string) => void;
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
    const normalized = normalizeFolderName(folderName);
    if (normalized !== folderName) {
      onFolderNameChange(normalized);
    }
  };

  // Normalize folder description: remove invalid chars, trim, no consecutive spaces/periods
  const normalizeFolderDescription = (value: string): string => {
    return value
      .replace(/[^a-zA-Z0-9. ]/g, "") // Remove invalid characters (keep letters, numbers, periods, spaces)
      .replace(/\.{2,}/g, ".") // Replace consecutive periods with single period
      .replace(/\s{2,}/g, " ") // Replace consecutive spaces with single space
      .trim();
  };

  const handleFolderDescriptionBlur = () => {
    const normalized = normalizeFolderDescription(folderDescription);
    if (normalized !== folderDescription) {
      onFolderDescriptionChange(normalized);
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
