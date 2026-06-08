import { useEffect, useState } from "react";
import { Chip, Stack } from "@mui/material";
import AccessTimeIcon from "@mui/icons-material/AccessTime";
import ListIcon from "@mui/icons-material/List";
import {
  useInferenceQueueStore,
  selectEtaMs,
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

  useEffect(() => {
    if (activeCount === 0) return;
    const interval = setInterval(() => forceUpdate((n) => n + 1), 1000);
    return () => clearInterval(interval);
  }, [activeCount]);

  if (activeCount === 0) return null;

  const etaMs = selectEtaMs(useInferenceQueueStore.getState());
  const etaLabel =
    etaMs === null
      ? t("inferenceQueue.etaUnknown")
      : t("inferenceQueue.eta", { time: Math.ceil(etaMs / 1000) });

  return (
    <Stack direction="row" spacing={1} sx={{ px: "0.5vh" }}>
      <Chip
        icon={<ListIcon style={{ fontSize: "1.6vh" }} />}
        label={t("inferenceQueue.itemsQueued", { count: activeCount })}
        size="small"
        sx={{
          fontSize: "1.1vh",
          height: "2.4vh",
          bgcolor: "#E3F2FD",
          color: "#1565c0",
          "& .MuiChip-label": { px: "0.6vh" },
        }}
      />
      <Chip
        icon={<AccessTimeIcon style={{ fontSize: "1.6vh" }} />}
        label={etaLabel}
        size="small"
        sx={{
          fontSize: "1.1vh",
          height: "2.4vh",
          bgcolor: "#F3E5F5",
          color: "#7b1fa2",
          "& .MuiChip-label": { px: "0.6vh" },
        }}
      />
    </Stack>
  );
};

export default QueueSummary;
