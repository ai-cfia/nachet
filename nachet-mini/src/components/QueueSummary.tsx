import { useEffect, useState } from "react";
import { Chip, Stack } from "@mui/material";
import AccessTimeIcon from "@mui/icons-material/AccessTime";
import ListIcon from "@mui/icons-material/List";
import Tooltip from "@mui/material/Tooltip";
import {
  useInferenceQueueStore,
  selectEtaMs,
  selectIsClassifying,
} from "@stores/useInferenceQueueStore";
import { useTranslation } from "react-i18next";
import { useShallow } from "zustand/react/shallow";

const QueueSummary = () => {
  const { t } = useTranslation("main");
  const [, forceUpdate] = useState(0);

  const activeCount = useInferenceQueueStore(
    useShallow(
      (s) =>
        s.queue.filter(
          (i) => i.status === "pending" || i.status === "processing",
        ).length,
    ),
  );

  const isClassifying = useInferenceQueueStore(selectIsClassifying); // ← must be before early return

  useEffect(() => {
    if (activeCount === 0) return;
    const interval = setInterval(() => forceUpdate((n) => n + 1), 1000);
    return () => clearInterval(interval);
  }, [activeCount]);

  if (activeCount === 0) return null; // ← early return after all hooks

  const etaMs = selectEtaMs(useInferenceQueueStore.getState());

  const etaLabel =
    etaMs === null
      ? t("inferenceQueue.etaUnknown")
      : isClassifying
        ? t("inferenceQueue.etaClassifying", { time: Math.ceil(etaMs / 1000) })
        : t("inferenceQueue.etaDetecting", { time: Math.ceil(etaMs / 1000) });

  return (
    <Stack direction="row" spacing={1} sx={{ px: "0.5vh" }}>
      <Chip
        icon={<ListIcon style={{ fontSize: "1.6vh" }} />}
        label={t("inferenceQueue.itemsQueued", { count: activeCount })}
        size="small"
        sx={{
          fontSize: "1.1vh",
          height: "2.4vh",
          bgcolor: isClassifying ? "#FFF3E0" : "#F3E5F5",
          color: isClassifying ? "#e65100" : "#7b1fa2",
          "& .MuiChip-label": { px: "0.6vh" },
        }}
      />
      {etaLabel && (
        <Tooltip
          title={t("inferenceQueue.etaTooltip")}
          placement="bottom"
          arrow
        >
          <Chip
            icon={<AccessTimeIcon style={{ fontSize: "1.6vh" }} />}
            label={etaLabel}
            size="small"
            sx={{
              fontSize: "1.1vh",
              height: "2.4vh",
              bgcolor: isClassifying ? "#FFF3E0" : "#F3E5F5",
              color: isClassifying ? "#e65100" : "#7b1fa2",
              "& .MuiChip-label": { px: "0.6vh" },
              cursor: "help",
            }}
          />
        </Tooltip>
      )}
    </Stack>
  );
};

export default QueueSummary;
