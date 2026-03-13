import {
  Box,
  Button,
  FormControl,
  InputLabel,
  LinearProgress,
  MenuItem,
  Select,
  Typography,
} from "@mui/material";
import type { SelectChangeEvent } from "@mui/material";
import type {
  DetectorModelEntry,
  ClassifierModelEntry,
} from "@inference/models";
import type { ModelLoadProgress } from "@stores/useInferenceStore";

interface Props {
  detectors: DetectorModelEntry[];
  classifiers: ClassifierModelEntry[];
  selectedDetectorId: string;
  selectedClassifierId: string;
  onSelectDetector: (id: string) => void;
  onSelectClassifier: (id: string) => void;
  onLoad: () => void;
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
  onLoad,
  isLoading,
  progress,
}: Props) => (
  <Box sx={{ display: "flex", alignItems: "center", gap: "1vw" }}>
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

    <FormControl size="small" sx={{ minWidth: "11vw" }}>
      <InputLabel sx={{ fontSize: "1.2vh" }}>Detector</InputLabel>
      <Select
        value={selectedDetectorId}
        label="Detector"
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

    <FormControl size="small" sx={{ minWidth: "11vw" }}>
      <InputLabel sx={{ fontSize: "1.2vh" }}>Classifier</InputLabel>
      <Select
        value={selectedClassifierId}
        label="Classifier"
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

    <Button
      variant="contained"
      size="small"
      onClick={onLoad}
      disabled={isLoading}
      sx={{ fontSize: "1.1vh", textTransform: "none", whiteSpace: "nowrap" }}
    >
      {isLoading ? "Loading…" : "Load Model"}
    </Button>
  </Box>
);

export default ModelLoader;
