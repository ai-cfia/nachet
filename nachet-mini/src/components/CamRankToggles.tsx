import { Box, IconButton, Tooltip } from "@mui/material";
import VisibilityIcon from "@mui/icons-material/Visibility";
import VisibilityOffOutlinedIcon from "@mui/icons-material/VisibilityOffOutlined";
import type { InferenceResult } from "@common/types";
import { useInferenceStore } from "@stores/useInferenceStore";

/**
 * Global CAM rank toggles shown under a run in the Images panel.
 *
 * One toggle per prediction rank ("Top 1" = each seed's top-1 species,
 * "Top 2" = each seed's 2nd, …). Turning one on overlays that rank's
 * activation map on *every* seed of the run at once; single-select (not
 * stackable), so one rank shows at a time.
 */

interface Props {
  /** "imageIndex:modelConfigId" for this run. */
  resultKey: string;
  result: InferenceResult;
}

const CamRankToggles = ({ resultKey, result }: Props) => {
  const camResults = useInferenceStore((s) => s.camResults);
  const camRank = useInferenceStore((s) => s.camRank);
  const toggleCamRank = useInferenceStore((s) => s.toggleCamRank);
  const setActiveResultKey = useInferenceStore((s) => s.setActiveResultKey);

  // Number of ranks = CAM class count from the first box that has data.
  let rankCount = 0;
  for (const box of result.boxes) {
    const cam = camResults.get(`${resultKey}:${box.boxId}`);
    if (cam) {
      rankCount = cam.classes.length;
      break;
    }
  }
  if (rankCount === 0) return null;

  const activeRank = camRank.get(resultKey);

  return (
    <Box>
      {Array.from({ length: rankCount }, (_, r) => {
        const on = activeRank === r;
        return (
          <Box
            key={r}
            role="button"
            aria-pressed={on}
            data-testid={`cam-rank-${r}`}
            onClick={() => {
              setActiveResultKey(resultKey);
              toggleCamRank(resultKey, r);
            }}
            sx={{
              display: "flex",
              alignItems: "center",
              gap: "0.4vw",
              pl: "5.2vh",
              pr: "0.8vh",
              py: "0.35vh",
              fontSize: "1.25vh",
              cursor: "pointer",
              color: on ? "text.primary" : "text.secondary",
              backgroundColor: on ? "#E3F2FD" : "transparent",
              borderTop: "1px solid #f5f5f5",
              "&:hover": { backgroundColor: on ? "#E3F2FD" : "#F5F5F5" },
            }}
          >
            <Box sx={{ flex: 1 }}>{`Top ${r + 1}`}</Box>
            <Tooltip title="Overlay this prediction rank on all seeds">
              <IconButton
                size="small"
                sx={{ padding: "0.2vh" }}
                aria-label={`overlay top ${r + 1}`}
                aria-pressed={on}
                onClick={(e) => {
                  e.stopPropagation();
                  setActiveResultKey(resultKey);
                  toggleCamRank(resultKey, r);
                }}
              >
                {on ? (
                  <VisibilityIcon
                    sx={{ fontSize: "1.9vh", color: "#1565c0" }}
                  />
                ) : (
                  <VisibilityOffOutlinedIcon
                    sx={{ fontSize: "1.9vh", color: "#bdbdbd" }}
                  />
                )}
              </IconButton>
            </Tooltip>
          </Box>
        );
      })}
    </Box>
  );
};

export default CamRankToggles;
