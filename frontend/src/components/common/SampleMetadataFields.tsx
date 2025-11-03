import { TextField, MenuItem, Box } from "@mui/material";
import { useTranslation } from "react-i18next";

interface SampleMetadataFieldsProps {
  // Values
  trayCode: string;
  magnification: number;
  sampleIdPrefix?: string;
  sampleDescription: string;
  // Change handlers
  onTrayCodeChange: (value: string) => void;
  onMagnificationChange: (value: number) => void;
  onSampleIdPrefixChange?: (value: string) => void;
  onSampleDescriptionChange: (value: string) => void;
  // Validation errors
  trayCodeError?: string;
  magnificationError?: string;
  sampleIdPrefixError?: string;
  sampleDescriptionError?: string;
  // UI control
  disabled?: boolean;
}

export const SampleMetadataFields = (props: SampleMetadataFieldsProps) => {
  const {
    trayCode,
    magnification,
    sampleIdPrefix,
    sampleDescription,
    onTrayCodeChange,
    onMagnificationChange,
    onSampleIdPrefixChange,
    onSampleDescriptionChange,
    trayCodeError,
    magnificationError,
    sampleIdPrefixError,
    sampleDescriptionError,
    disabled = false,
  } = props;

  const { t } = useTranslation("popups");

  // Normalize sample ID prefix: remove invalid chars and trailing dashes
  const normalizeSampleIdPrefix = (value: string): string => {
    return value
      .replace(/[^a-zA-Z0-9-]/g, "") // Remove invalid characters
      .replace(/-+$/, "") // Remove trailing dashes
      .trim();
  };

  const handleSampleIdPrefixBlur = () => {
    if (sampleIdPrefix !== undefined && onSampleIdPrefixChange) {
      const normalized = normalizeSampleIdPrefix(sampleIdPrefix);
      if (normalized !== sampleIdPrefix) {
        onSampleIdPrefixChange(normalized);
      }
    }
  };

  // Normalize sample description: remove invalid chars, trim, no consecutive spaces/periods
  const normalizeSampleDescription = (value: string): string => {
    return value
      .replace(/[^a-zA-Z0-9. ]/g, "") // Remove invalid characters (keep letters, numbers, periods, spaces)
      .replace(/\.{2,}/g, ".") // Replace consecutive periods with single period
      .replace(/\s{2,}/g, " ") // Replace consecutive spaces with single space
      .trim();
  };

  const handleSampleDescriptionBlur = () => {
    const normalized = normalizeSampleDescription(sampleDescription);
    if (normalized !== sampleDescription) {
      onSampleDescriptionChange(normalized);
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
      <Box
        sx={{
          display: "flex",
          flexDirection: "row",
          gap: "10px",
          width: "100%",
        }}
      >
        <TextField
          id="input-tray-code"
          label={t("batchUpload.metadataSection.trayCodeLabel")}
          variant="outlined"
          select
          value={trayCode}
          onChange={(e) => onTrayCodeChange(e.target.value)}
          error={!!trayCodeError}
          helperText={trayCodeError}
          disabled={disabled}
          sx={{ width: "calc(50% - 5px)" }}
        >
          <MenuItem value="">
            <em>{t("batchUpload.metadataSection.selectTrayCode")}</em>
          </MenuItem>
          <MenuItem value="A">A</MenuItem>
          <MenuItem value="B">B</MenuItem>
          <MenuItem value="C">C</MenuItem>
          <MenuItem value="D">D</MenuItem>
          <MenuItem value="E">E</MenuItem>
        </TextField>

        <TextField
          id="input-magnification"
          label={t("batchUpload.deviceSection.magnificationLabel")}
          variant="outlined"
          type="number"
          value={magnification > 0 ? magnification : ""}
          onChange={(e) =>
            onMagnificationChange(parseFloat(e.target.value) || 0)
          }
          slotProps={{
            htmlInput: {
              min: 0.2,
              max: 1000,
              step: 0.1,
              style: { textAlign: "center" },
            },
          }}
          error={!!magnificationError}
          helperText={magnificationError}
          disabled={disabled}
          sx={{ width: "calc(50% - 5px)" }}
        />
      </Box>

      {sampleIdPrefix !== undefined && onSampleIdPrefixChange && (
        <TextField
          id="input-sample-id"
          label={t("batchUpload.metadataSection.sampleIdLabel")}
          variant="outlined"
          value={sampleIdPrefix}
          onChange={(e) => onSampleIdPrefixChange(e.target.value)}
          onBlur={handleSampleIdPrefixBlur}
          error={!!sampleIdPrefixError}
          helperText={
            sampleIdPrefixError ||
            t("batchUpload.metadataSection.sampleIdHelper")
          }
          disabled={disabled}
          placeholder={t("batchUpload.metadataSection.sampleIdPlaceholder")}
          fullWidth
        />
      )}

      <TextField
        id="input-sample-description"
        label={t("batchUpload.metadataSection.sampleDescriptionLabel")}
        variant="outlined"
        value={sampleDescription}
        onChange={(e) => onSampleDescriptionChange(e.target.value)}
        onBlur={handleSampleDescriptionBlur}
        multiline
        rows={2}
        error={!!sampleDescriptionError}
        helperText={
          sampleDescriptionError ||
          t("batchUpload.metadataSection.sampleDescriptionHelper")
        }
        disabled={disabled}
        placeholder={t(
          "batchUpload.metadataSection.sampleDescriptionPlaceholder",
        )}
        fullWidth
      />
    </Box>
  );
};
