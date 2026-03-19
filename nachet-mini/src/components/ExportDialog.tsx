import { useState } from "react";
import {
  Box,
  Button,
  Checkbox,
  CircularProgress,
  Dialog,
  DialogContent,
  FormControlLabel,
  IconButton,
  Typography,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { useImageStore } from "@stores/useImageStore";
import { useInferenceStore } from "@stores/useInferenceStore";
import { buildExportManifest, generateExportZip } from "@common/exportUtils";
import { useTranslation } from "react-i18next";

interface Props {
  open: boolean;
  onClose: () => void;
  checkedImages: Set<number>;
  checkedResults: Set<string>;
  onExportComplete: () => void;
}

const ExportDialog = ({
  open,
  onClose,
  checkedImages,
  checkedResults,
  onExportComplete,
}: Props) => {
  const { t } = useTranslation("main");
  const { t: tCommon } = useTranslation("common");
  const images = useImageStore((s) => s.images);
  const results = useInferenceStore((s) => s.results);
  const getResultsForImage = useInferenceStore((s) => s.getResultsForImage);

  const [exporting, setExporting] = useState(false);
  const [includeImages, setIncludeImages] = useState(true);
  const [includeResults, setIncludeResults] = useState(true);
  const [includeCsv, setIncludeCsv] = useState(true);
  const [humanReadable, setHumanReadable] = useState(false);
  const [exportError, setExportError] = useState("");

  // Count what will be exported
  const imageIndices = new Set<number>(checkedImages);
  for (const key of checkedResults) {
    const idx = parseInt(key.split(":")[0], 10);
    if (!isNaN(idx)) imageIndices.add(idx);
  }

  // Count results: if image is checked, count all its results; otherwise count only checked results
  let resultCount = 0;
  for (const idx of imageIndices) {
    if (checkedImages.has(idx)) {
      resultCount += getResultsForImage(idx).length;
    }
  }
  for (const key of checkedResults) {
    const idx = parseInt(key.split(":")[0], 10);
    if (!checkedImages.has(idx)) {
      resultCount++;
    }
  }

  const nothingSelected = imageIndices.size === 0;

  const handleExport = async () => {
    setExporting(true);
    setExportError("");
    try {
      const manifest = buildExportManifest(
        images,
        checkedImages,
        checkedResults,
        getResultsForImage,
        results,
      );
      await generateExportZip(manifest, images, {
        includeImages,
        includeResults,
        includeCsv,
        humanReadable,
      });
      onExportComplete();
      onClose();
    } catch (error) {
      const message = error instanceof Error ? error.message : String(error);
      if (message.startsWith("DUPLICATE_NAME:")) {
        const name = message.slice("DUPLICATE_NAME:".length);
        setExportError(t("exportDialog.duplicateNameError", { name }));
      } else {
        console.error("Export error:", message);
      }
    } finally {
      setExporting(false);
    }
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="xs"
      fullWidth
      slotProps={{
        paper: {
          sx: { borderRadius: 1, padding: "1vh" },
        },
      }}
    >
      <DialogContent>
        <Box sx={{ display: "flex", flexDirection: "column" }}>
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
                color: "text.primary",
              }}
            >
              {t("exportDialog.title")}
            </Typography>
            <IconButton onClick={onClose} size="small" aria-label="close">
              <CloseIcon />
            </IconButton>
          </Box>

          <Typography
            variant="body2"
            sx={{ fontSize: "1.3vh", color: "text.secondary", mb: "2vh" }}
          >
            {nothingSelected
              ? t("exportDialog.nothingSelected")
              : t("exportDialog.summary", {
                  imageCount: imageIndices.size,
                  resultCount,
                })}
          </Typography>

          <Box sx={{ display: "flex", flexDirection: "column", mb: "1vh" }}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={includeImages}
                  onChange={(e) => setIncludeImages(e.target.checked)}
                  size="small"
                />
              }
              label={t("exportDialog.includeImages")}
              slotProps={{
                typography: { sx: { fontSize: "1.3vh" } },
              }}
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={includeResults}
                  onChange={(e) => setIncludeResults(e.target.checked)}
                  size="small"
                />
              }
              label={t("exportDialog.includeResults")}
              slotProps={{
                typography: { sx: { fontSize: "1.3vh" } },
              }}
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={includeCsv}
                  onChange={(e) => setIncludeCsv(e.target.checked)}
                  size="small"
                />
              }
              label={t("exportDialog.includeCsv")}
              slotProps={{
                typography: { sx: { fontSize: "1.3vh" } },
              }}
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={humanReadable}
                  onChange={(e) => {
                    setHumanReadable(e.target.checked);
                    setExportError("");
                  }}
                  size="small"
                />
              }
              label={t("exportDialog.humanReadable")}
              slotProps={{
                typography: { sx: { fontSize: "1.3vh" } },
              }}
            />
          </Box>

          {exportError && (
            <Typography color="error" sx={{ fontSize: "1.2vh", mb: "1vh" }}>
              {exportError}
            </Typography>
          )}

          <Box
            sx={{
              display: "flex",
              justifyContent: "flex-end",
              gap: "1vh",
            }}
          >
            <Button
              variant="outlined"
              onClick={onClose}
              sx={{ fontSize: "1.1vh", textTransform: "none" }}
            >
              {tCommon("actions.cancel")}
            </Button>
            <Button
              variant="contained"
              onClick={handleExport}
              disabled={
                nothingSelected ||
                exporting ||
                (!includeImages && !includeResults && !includeCsv)
              }
              sx={{ fontSize: "1.1vh", textTransform: "none" }}
              startIcon={exporting ? <CircularProgress size={14} /> : undefined}
            >
              {t("exportDialog.title")}
            </Button>
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default ExportDialog;
