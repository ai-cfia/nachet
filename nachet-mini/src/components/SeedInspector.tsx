import { useEffect, useRef, useState } from "react";
import {
  Box,
  Button,
  Collapse,
  IconButton,
  Tooltip,
  Typography,
} from "@mui/material";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import VisibilityIcon from "@mui/icons-material/Visibility";
import VisibilityOffOutlinedIcon from "@mui/icons-material/VisibilityOffOutlined";
import { useTranslation } from "react-i18next";
import type {
  BoxTaxonomy,
  InferenceBox,
  RankedPrediction,
  SpeciesTaxonomy,
} from "@common/types";
import { drawCamHeatmap } from "@common/heatmapColors";
import type { CamBoxResult } from "@stores/useInferenceStore";

interface Props {
  imageSrc: string;
  imageDims: number[];
  box: InferenceBox;
  taxonomy?: BoxTaxonomy;
  topResults: RankedPrediction[];
  cam?: CamBoxResult;
}

interface CropProps {
  imageSrc: string;
  imageDims: number[];
  box: InferenceBox;
  cam?: CamBoxResult;
  selectedCam?: CamBoxResult["classes"][number];
}

interface SpeciesListProps {
  predictions: RankedPrediction[];
  cam?: CamBoxResult;
  selectedRank: number | null;
  onToggleRank: (rank: number) => void;
}

const CANVAS_SIZE = 240;
const MEDIA_WIDTH = 152;
const MEDIA_HEIGHT = 116;

const percentage = (score: number): string =>
  score > 0 && score < 0.0001 ? "< 0.01%" : `${(score * 100).toFixed(2)}%`;

const RankedList = ({ predictions }: { predictions: RankedPrediction[] }) => (
  <Box sx={{ display: "grid", gap: 0.25 }}>
    {predictions.map(({ label, score }, index) => (
      <Box
        key={label}
        sx={{
          display: "grid",
          gridTemplateColumns: "1rem minmax(0, 1fr) auto",
          gap: 0.5,
          alignItems: "baseline",
          minWidth: 0,
        }}
      >
        <Typography variant="caption" color="text.secondary">
          {index + 1}.
        </Typography>
        <Typography
          variant="caption"
          sx={{ overflowWrap: "anywhere", lineHeight: 1.25 }}
        >
          {label}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {percentage(score)}
        </Typography>
      </Box>
    ))}
  </Box>
);

const SeedCropCanvas = ({
  imageSrc,
  imageDims,
  box,
  cam,
  selectedCam,
}: CropProps) => {
  const { t } = useTranslation("main");
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const cropWidth = Math.max(1, box.bottomX - box.topX);
  const cropHeight = Math.max(1, box.bottomY - box.topY);
  const canvasScale = CANVAS_SIZE / Math.max(cropWidth, cropHeight);
  const displayScale = Math.min(
    MEDIA_WIDTH / cropWidth,
    MEDIA_HEIGHT / cropHeight,
  );
  const canvasWidth = Math.max(1, Math.round(cropWidth * canvasScale));
  const canvasHeight = Math.max(1, Math.round(cropHeight * canvasScale));
  const displayWidth = Math.max(1, Math.round(cropWidth * displayScale));
  const displayHeight = Math.max(1, Math.round(cropHeight * displayScale));

  // Draw the selected box from the original image, then reuse the tray's CAM
  // renderer when a species focus is active.
  useEffect(() => {
    let cancelled = false;
    const image = new Image();
    image.onload = () => {
      if (cancelled) return;
      const canvas = canvasRef.current;
      const context = canvas?.getContext("2d");
      if (!canvas || !context) return;

      const imageWidth = imageDims[0] || image.naturalWidth;
      const imageHeight = imageDims[1] || image.naturalHeight;
      const sourceX = Math.max(0, Math.min(box.topX, imageWidth));
      const sourceY = Math.max(0, Math.min(box.topY, imageHeight));
      const sourceWidth = Math.max(
        1,
        Math.min(box.bottomX, imageWidth) - sourceX,
      );
      const sourceHeight = Math.max(
        1,
        Math.min(box.bottomY, imageHeight) - sourceY,
      );

      context.clearRect(0, 0, canvas.width, canvas.height);
      context.drawImage(
        image,
        sourceX,
        sourceY,
        sourceWidth,
        sourceHeight,
        0,
        0,
        canvas.width,
        canvas.height,
      );
      if (selectedCam && cam) {
        drawCamHeatmap(
          context,
          canvas.width,
          canvas.height,
          selectedCam.heatmap,
          cam.grid,
        );
      }
    };
    image.src = imageSrc;

    return () => {
      cancelled = true;
      image.onload = null;
    };
  }, [box, cam, imageDims, imageSrc, selectedCam]);

  return (
    <Box
      sx={{
        width: "100%",
        maxWidth: MEDIA_WIDTH,
        height: MEDIA_HEIGHT,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        border: "1px solid",
        borderColor: "divider",
        borderRadius: 0.5,
        bgcolor: "grey.50",
        overflow: "hidden",
      }}
    >
      <canvas
        ref={canvasRef}
        width={canvasWidth}
        height={canvasHeight}
        role="img"
        aria-label={t(
          selectedCam ? "resultsTable.modelFocusFor" : "resultsTable.seedCrop",
          { species: selectedCam?.label ?? "" },
        )}
        data-testid="seed-crop-canvas"
        style={{
          display: "block",
          width: displayWidth,
          height: displayHeight,
        }}
      />
    </Box>
  );
};

const SpeciesPredictionList = ({
  predictions,
  cam,
  selectedRank,
  onToggleRank,
}: SpeciesListProps) => {
  const { t } = useTranslation("main");

  return (
    <Box sx={{ minWidth: 0 }}>
      <Typography variant="subtitle2" sx={{ fontSize: "0.75rem", mb: 0.5 }}>
        {t("resultsTable.speciesPredictions")}
      </Typography>
      <Box sx={{ display: "grid", gap: 0.25 }}>
        {predictions.map((prediction, rank) => {
          const camAvailable = Boolean(cam?.classes[rank]);
          const selected = selectedRank === rank;
          const label = t(
            selected
              ? "resultsTable.hideModelFocus"
              : "resultsTable.showModelFocus",
            { species: prediction.label },
          );

          return (
            <Box
              key={`${prediction.label}-${rank}`}
              sx={{
                display: "grid",
                gridTemplateColumns: camAvailable
                  ? "1rem minmax(0, 1fr) auto 1.75rem"
                  : "1rem minmax(0, 1fr) auto",
                alignItems: "center",
                gap: 0.25,
                minHeight: 27,
                px: 0.25,
                borderRadius: 0.5,
                bgcolor: selected ? "action.selected" : "transparent",
              }}
            >
              <Typography variant="caption" color="text.secondary">
                {rank + 1}.
              </Typography>
              <Typography
                variant="caption"
                sx={{ overflowWrap: "anywhere", lineHeight: 1.2 }}
              >
                {prediction.label}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {percentage(prediction.score)}
              </Typography>
              {camAvailable && (
                <Tooltip disableInteractive title={label}>
                  <IconButton
                    size="small"
                    data-testid={`focused-cam-rank-${rank}`}
                    aria-label={label}
                    aria-pressed={selected}
                    onClick={() => onToggleRank(rank)}
                    sx={{ p: 0.25 }}
                  >
                    {selected ? (
                      <VisibilityIcon
                        sx={{ fontSize: "1.15rem", color: "#1565c0" }}
                      />
                    ) : (
                      <VisibilityOffOutlinedIcon
                        sx={{ fontSize: "1.15rem", color: "#bdbdbd" }}
                      />
                    )}
                  </IconButton>
                </Tooltip>
              )}
            </Box>
          );
        })}
      </Box>
    </Box>
  );
};

const TaxonomyPair = ({ taxonomy }: { taxonomy: SpeciesTaxonomy }) => {
  const { t } = useTranslation("main");
  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
        gap: 1,
        mt: 0.25,
      }}
    >
      {(["family", "genus"] as const).map((rank) => (
        <Box key={rank} sx={{ minWidth: 0 }}>
          <Typography variant="caption" color="text.secondary">
            {t(`resultsTable.${rank}`)}
          </Typography>
          <Typography variant="caption" sx={{ display: "block" }}>
            {taxonomy[rank].label} · {percentage(taxonomy[rank].score)}
          </Typography>
        </Box>
      ))}
    </Box>
  );
};

const TaxonomyPanel = ({
  taxonomy,
  selected,
}: {
  taxonomy?: BoxTaxonomy;
  selected?: SpeciesTaxonomy;
}) => {
  const { t } = useTranslation("main");
  const [open, setOpen] = useState(false);
  const topTaxonomy = taxonomy
    ? {
        label: "",
        family: taxonomy.families[0],
        genus: taxonomy.genera[0],
      }
    : undefined;

  return (
    <Box sx={{ borderTop: "1px solid", borderColor: "divider", pt: 0.75 }}>
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: 1,
        }}
      >
        <Typography variant="subtitle2" sx={{ fontSize: "0.75rem" }}>
          {selected
            ? t("resultsTable.taxonomyFor", { species: selected.label })
            : t("resultsTable.taxonomy")}
        </Typography>
        {taxonomy && !selected && (
          <Button
            size="small"
            onClick={() => setOpen((current) => !current)}
            endIcon={
              open ? (
                <ExpandLessIcon fontSize="small" />
              ) : (
                <ExpandMoreIcon fontSize="small" />
              )
            }
            aria-expanded={open}
            sx={{
              minWidth: 0,
              px: 0.5,
              py: 0,
              fontSize: "0.65rem",
              textTransform: "none",
            }}
          >
            {t(
              open
                ? "resultsTable.hideTaxonomyDetails"
                : "resultsTable.showTaxonomyDetails",
            )}
          </Button>
        )}
      </Box>

      {selected ? (
        <TaxonomyPair taxonomy={selected} />
      ) : taxonomy && topTaxonomy?.family && topTaxonomy.genus ? (
        <>
          {!open && <TaxonomyPair taxonomy={topTaxonomy} />}
          <Collapse in={open} unmountOnExit>
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                gap: 1.25,
                mt: 0.5,
              }}
            >
              {(["families", "genera"] as const).map((rank) => (
                <Box key={rank} sx={{ minWidth: 0 }}>
                  <Typography variant="caption" color="text.secondary">
                    {t(`resultsTable.${rank}`)}
                  </Typography>
                  <RankedList predictions={taxonomy[rank]} />
                </Box>
              ))}
            </Box>
          </Collapse>
        </>
      ) : (
        <Typography variant="caption" color="text.secondary">
          {t("resultsTable.taxonomyUnavailable")}
        </Typography>
      )}
    </Box>
  );
};

const SeedInspector = ({
  imageSrc,
  imageDims,
  box,
  taxonomy,
  topResults,
  cam,
}: Props) => {
  const [selectedCamRank, setSelectedCamRank] = useState<number | null>(null);
  const selectedCam =
    selectedCamRank === null ? undefined : cam?.classes[selectedCamRank];
  const selectedTaxonomy = selectedCam
    ? taxonomy?.candidates.find(({ label }) => label === selectedCam.label)
    : undefined;

  const toggleSpeciesCam = (rank: number) => {
    if (!cam?.classes[rank]) return;
    setSelectedCamRank((current) => (current === rank ? null : rank));
  };

  return (
    <Box data-testid="seed-inspector" sx={{ display: "grid", gap: 1 }}>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "minmax(132px, 0.78fr) minmax(0, 1.22fr)",
          gap: 1.25,
          alignItems: "start",
        }}
      >
        <SeedCropCanvas
          imageSrc={imageSrc}
          imageDims={imageDims}
          box={box}
          cam={cam}
          selectedCam={selectedCam}
        />
        <SpeciesPredictionList
          predictions={topResults}
          cam={cam}
          selectedRank={selectedCamRank}
          onToggleRank={toggleSpeciesCam}
        />
      </Box>
      <TaxonomyPanel taxonomy={taxonomy} selected={selectedTaxonomy} />
    </Box>
  );
};

export default SeedInspector;
