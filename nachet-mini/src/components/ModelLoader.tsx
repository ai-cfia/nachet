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
import type { ModelConfig } from "@inference/models";
import type { ModelLoadProgress } from "@stores/useInferenceStore";

interface Props {
  presets: ModelConfig[];
  selectedId: string;
  onSelectId: (id: string) => void;
  onLoad: () => void;
  isLoading: boolean;
  progress: ModelLoadProgress | null;
}

const ModelLoader = ({
  presets,
  selectedId,
  onSelectId,
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

    <FormControl size="small" sx={{ minWidth: "14vw" }}>
      <InputLabel sx={{ fontSize: "1.2vh" }}>Model</InputLabel>
      <Select
        value={selectedId}
        label="Model"
        onChange={(e: SelectChangeEvent<string>) => {
          onSelectId(e.target.value);
        }}
        disabled={isLoading}
        sx={{ fontSize: "1.2vh" }}
      >
        {presets.map((p) => (
          <MenuItem key={p.id} value={p.id} sx={{ fontSize: "1.2vh" }}>
            {p.id}
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
