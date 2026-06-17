import {
  Box,
  FormControl,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Skeleton,
  TextField,
} from "@mui/material";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import type { SelectChangeEvent } from "@mui/material";
import type {
  DetectorModelEntry,
  ClassifierModelEntry,
} from "@inference/models";
import { huggingFaceUrl } from "@inference/models";
import { useTranslation } from "react-i18next";

interface Props {
  detectors: DetectorModelEntry[];
  classifiers: ClassifierModelEntry[];
  selectedDetectorId: string;
  selectedClassifierId: string;
  onSelectDetector: (id: string) => void;
  onSelectClassifier: (id: string) => void;
  isLoading: boolean;
  disabled: boolean;
  /**
   * Text-promptable detector inputs. When the selected detector's kind is
   * `text-promptable-segmentation` (e.g. SAM3), a TextField is rendered next to
   * the dropdowns. Closed-vocabulary detectors (RT-DETR, DETR) hide it.
   */
  detectorPrompt: string;
  onDetectorPromptChange: (value: string) => void;
  detectorRequiresPrompt: boolean;
}

const ModelLoader = ({
  detectors,
  classifiers,
  selectedDetectorId,
  selectedClassifierId,
  onSelectDetector,
  onSelectClassifier,
  isLoading,
  disabled,
  detectorPrompt,
  onDetectorPromptChange,
  detectorRequiresPrompt,
}: Props) => {
  const { t } = useTranslation("main");
  const detectorLabel = t("modelLoader.detector");
  const classifierLabel = t("modelLoader.classifier");

  const selectedDetector = detectors.find((d) => d.id === selectedDetectorId);
  const selectedClassifier = classifiers.find(
    (c) => c.id === selectedClassifierId,
  );

  const dropdownSx = {
    minWidth: { xs: "fit-content", md: "8vw" },
    maxWidth: { xs: "fit-content", md: "8vw" },
  };

  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: "0.4vh" }}>
      <FormControl
        size="small"
        sx={dropdownSx}
        disabled={isLoading || disabled}
      >
        <InputLabel id="detector-model-label" sx={{ fontSize: "1.2vh" }}>
          {detectorLabel}
        </InputLabel>
        <Select
          id="detector-model-select"
          labelId="detector-model-label"
          value={selectedDetectorId}
          label={detectorLabel}
          onChange={(e: SelectChangeEvent<string>) => {
            onSelectDetector(e.target.value);
          }}
          sx={{ fontSize: "1.2vh" }}
        >
          {detectors.map((d) => (
            <MenuItem key={d.id} value={d.id} sx={{ fontSize: "1.2vh" }}>
              {d.id}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      {selectedDetector && (
        <IconButton
          component="a"
          href={huggingFaceUrl(selectedDetector.model)}
          aria-label={t("modelLoader.detectorInfo")}
          target="_blank"
          rel="noopener noreferrer"
          size="small"
          sx={{ paddingRight: "0.6vh", paddingLeft: "0vh" }}
        >
          <InfoOutlinedIcon sx={{ fontSize: "1.6vh" }} />
        </IconButton>
      )}

      <FormControl
        size="small"
        sx={dropdownSx}
        disabled={isLoading || disabled}
      >
        <InputLabel id="classifier-model-label" sx={{ fontSize: "1.2vh" }}>
          {classifierLabel}
        </InputLabel>
        <Select
          id="classifier-model-select"
          labelId="classifier-model-label"
          value={selectedClassifierId}
          label={classifierLabel}
          onChange={(e: SelectChangeEvent<string>) => {
            onSelectClassifier(e.target.value);
          }}
          sx={{ fontSize: "1.2vh" }}
        >
          {classifiers.map((c) => (
            <MenuItem key={c.id} value={c.id} sx={{ fontSize: "1.2vh" }}>
              {c.id}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      {selectedClassifier && (
        <IconButton
          component="a"
          href={huggingFaceUrl(selectedClassifier.model)}
          aria-label={t("modelLoader.classifierInfo")}
          target="_blank"
          rel="noopener noreferrer"
          size="small"
          sx={{ paddingRight: "0.6vh", paddingLeft: "0vh" }}
        >
          <InfoOutlinedIcon sx={{ fontSize: "1.6vh" }} />
        </IconButton>
      )}

      {detectorRequiresPrompt && (
        <TextField
          id="detector-prompt-input"
          size="small"
          label={t("modelLoader.prompt")}
          placeholder={t("modelLoader.promptPlaceholder")}
          value={detectorPrompt}
          onChange={(e) => onDetectorPromptChange(e.target.value)}
          // Accessible name beats the visual label for screen readers since
          // the label text is shrunk to ~1.2vh for visual density.
          inputProps={{
            "aria-label": t("modelLoader.prompt"),
            style: { fontSize: "1.2vh" },
          }}
          InputLabelProps={{ sx: { fontSize: "1.2vh" } }}
          sx={{
            minWidth: { xs: "fit-content", md: "10vw" },
            maxWidth: { xs: "fit-content", md: "12vw" },
          }}
        />
      )}
    </Box>
  );
};

export default ModelLoader;
