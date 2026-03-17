import {
  Box,
  FormControl,
  IconButton,
  InputLabel,
  LinearProgress,
  MenuItem,
  Select,
  Typography,
} from "@mui/material";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import type { SelectChangeEvent } from "@mui/material";
import type {
  DetectorModelEntry,
  ClassifierModelEntry,
} from "@inference/models";
import { huggingFaceUrl } from "@inference/models";
import type { ModelLoadProgress } from "@stores/useInferenceStore";
import { useTranslation } from "react-i18next";

interface Props {
  detectors: DetectorModelEntry[];
  classifiers: ClassifierModelEntry[];
  selectedDetectorId: string;
  selectedClassifierId: string;
  onSelectDetector: (id: string) => void;
  onSelectClassifier: (id: string) => void;
  isLoading: boolean;
  progress: ModelLoadProgress | null;
}

const ModelLoader = ({
  detectors,
  classifiers,
  selectedDetectorId,
  selectedClassifierId,
  onSelectDetector,
  onSelectClassifier,
  isLoading,
  progress,
}: Props) => {
  const { t } = useTranslation("main");

  const selectedDetector = detectors.find((d) => d.id === selectedDetectorId);
  const selectedClassifier = classifiers.find(
    (c) => c.id === selectedClassifierId,
  );

  return (
    <Box sx={{ display: "flex", alignItems: "center", gap: "0.4vh" }}>

      <FormControl size="small" sx={{ minWidth: "9vw", maxWidth: "9vw" }}>
        <InputLabel sx={{ fontSize: "1.2vh" }}>
          {t("modelLoader.detector")}
        </InputLabel>
        <Select
          value={selectedDetectorId}
          label={t("modelLoader.detector")}
          onChange={(e: SelectChangeEvent<string>) => {
            onSelectDetector(e.target.value);
          }}
          disabled={isLoading}
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
          target="_blank"
          rel="noopener noreferrer"
          size="small"
          sx={{ paddingRight: "0.6vh", paddingLeft: "0vh" }}
        >
          <InfoOutlinedIcon sx={{ fontSize: "1.6vh" }} />
        </IconButton>
      )}

      <FormControl size="small" sx={{ minWidth: "9vw", maxWidth: "9vw" }}>
        <InputLabel sx={{ fontSize: "1.2vh" }}>
          {t("modelLoader.classifier")}
        </InputLabel>
        <Select
          value={selectedClassifierId}
          label={t("modelLoader.classifier")}
          onChange={(e: SelectChangeEvent<string>) => {
            onSelectClassifier(e.target.value);
          }}
          disabled={isLoading}
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
          target="_blank"
          rel="noopener noreferrer"
          size="small"
          sx={{ paddingRight: "0.6vh", paddingLeft: "0vh" }}
        >
          <InfoOutlinedIcon sx={{ fontSize: "1.6vh" }} />
        </IconButton>
      )}
      {isLoading && progress && (
        <Box sx={{ minWidth: "12vw" }}>
          <Typography
            variant="caption"
            sx={{ fontSize: "1vh", color: "text.secondary" }}
          >
            {progress.name} {Math.round(progress.progress)}%
          </Typography>
          <LinearProgress
            variant="determinate"
            value={progress.progress}
            sx={{ height: "0.6vh", borderRadius: "0.3vh" }}
          />
        </Box>
      )}
    </Box>
  );
};

export default ModelLoader;
