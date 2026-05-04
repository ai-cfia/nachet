import {
  Box,
  Button,
  Dialog,
  DialogContent,
  IconButton,
  Typography,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { useTranslation } from "react-i18next";
import { versions } from "../_versions";

type VersionCheckDialogProps = {
  open: boolean;
  remoteVersion: string | null;
  onClose: () => void;
  onReload?: () => void;
};

const VersionCheckDialog = ({
  open,
  remoteVersion,
  onClose,
  onReload = () => window.location.reload(),
}: VersionCheckDialogProps) => {
  const { t } = useTranslation("main");
  const { t: tCommon } = useTranslation("common");
  const titleId = "version-check-dialog-title";
  const descriptionId = "version-check-dialog-description";

  return (
    <Dialog
      open={open}
      onClose={onClose}
      aria-labelledby={titleId}
      aria-describedby={descriptionId}
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
              id={titleId}
              variant="h6"
              sx={{
                fontWeight: 600,
                fontSize: "1.25rem",
                color: "text.primary",
              }}
            >
              {t("versionDialog.title")}
            </Typography>
            <IconButton
              onClick={onClose}
              size="small"
              aria-label={tCommon("actions.close")}
              data-testid="version-dialog-close-icon"
            >
              <CloseIcon />
            </IconButton>
          </Box>

          <Typography
            id={descriptionId}
            variant="body2"
            sx={{ color: "text.secondary", mb: 1.5 }}
          >
            {t("versionDialog.message", {
              current: versions.version,
              remote: remoteVersion ?? "",
            })}
          </Typography>

          <Typography
            variant="body2"
            sx={{
              color: "warning.dark",
              fontWeight: 600,
              mb: 2,
            }}
          >
            {t("versionDialog.warning")}
          </Typography>

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
              data-testid="version-dialog-close-button"
              sx={{ textTransform: "none" }}
            >
              {tCommon("actions.close")}
            </Button>
            <Button
              variant="contained"
              onClick={onReload}
              sx={{ textTransform: "none" }}
            >
              {t("versionDialog.reload")}
            </Button>
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default VersionCheckDialog;
