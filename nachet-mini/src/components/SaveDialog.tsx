import { useState } from "react";
import {
  Box,
  Button,
  Dialog,
  DialogContent,
  IconButton,
  MenuItem,
  Select,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import type { SelectChangeEvent } from "@mui/material/Select";
import CloseIcon from "@mui/icons-material/Close";
import { saveAs } from "file-saver";
import JSZip from "jszip";
import { useImageStore } from "@stores/useImageStore";

interface Props {
  open: boolean;
  onClose: () => void;
}

const SaveDialog = ({ open, onClose }: Props) => {
  const images = useImageStore((s) => s.images);
  const getCurrentImage = useImageStore((s) => s.getCurrentImage);

  const [mode, setMode] = useState<"individual" | "cache">("individual");
  const [imageLabel, setImageLabel] = useState("");
  const [imageFormat, setImageFormat] = useState("image/png");
  const [labelError, setLabelError] = useState("");

  const handleClose = () => {
    setLabelError("");
    setImageLabel("");
    setMode("individual");
    setImageFormat("image/png");
    onClose();
  };

  const formatDate = (): string => {
    const d = new Date();
    return `${d.getFullYear()}-${d.getMonth() + 1}-${d.getDate()}`;
  };

  const handleSave = async () => {
    const ext = imageFormat.split("/")[1];
    const dateStr = formatDate();

    try {
      if (mode === "individual") {
        const trimmed = imageLabel.trim();
        if (!trimmed) {
          setLabelError("Label is required");
          return;
        }
        if (!/^[a-zA-Z0-9 _.-]+$/.test(trimmed)) {
          setLabelError(
            "Only letters, numbers, spaces, dashes, underscores, and periods",
          );
          return;
        }

        const currentImage = getCurrentImage();
        if (!currentImage) return;

        saveAs(currentImage.src, `${trimmed}-${dateStr}.${ext}`);
      } else {
        const zip = new JSZip();
        images.forEach((image) => {
          const base64Data = image.src.replace(/^data:image\/\w+;base64,/, "");
          zip.file(`Capture-${image.index}-${dateStr}.${ext}`, base64Data, {
            base64: true,
          });
        });
        const content = await zip.generateAsync({ type: "blob" });
        saveAs(content, `nachet-mini-${dateStr}.zip`);
      }
      handleClose();
    } catch (error) {
      console.error(
        "Save error:",
        error instanceof Error ? error.message : String(error),
      );
    }
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
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
              Save Image
            </Typography>
            <IconButton onClick={handleClose} size="small" aria-label="close">
              <CloseIcon />
            </IconButton>
          </Box>

          <ToggleButtonGroup
            fullWidth
            exclusive
            value={mode}
            onChange={(_, val) => {
              if (val) setMode(val);
            }}
            sx={{ marginBottom: "2vh", height: "3vh" }}
          >
            <ToggleButton
              value="individual"
              sx={{ textTransform: "none", fontSize: "1.1vh" }}
            >
              Current Image
            </ToggleButton>
            <ToggleButton
              value="cache"
              sx={{ textTransform: "none", fontSize: "1.1vh" }}
            >
              All Images (ZIP)
            </ToggleButton>
          </ToggleButtonGroup>

          {mode === "individual" && (
            <TextField
              label="Image name"
              variant="outlined"
              value={imageLabel}
              onChange={(e) => {
                setImageLabel(e.target.value);
                if (labelError) setLabelError("");
              }}
              size="small"
              fullWidth
              error={!!labelError}
              helperText={labelError}
              sx={{ marginBottom: "2vh", fontSize: "1.2vh" }}
            />
          )}

          <Select
            value={imageFormat}
            onChange={(e: SelectChangeEvent) => setImageFormat(e.target.value)}
            fullWidth
            sx={{ fontSize: "1.2vh", height: "3vh" }}
          >
            <MenuItem value="image/png">PNG</MenuItem>
            <MenuItem value="image/jpeg">JPEG</MenuItem>
          </Select>

          <Box
            sx={{
              display: "flex",
              justifyContent: "flex-end",
              gap: "1vh",
              marginTop: "2vh",
            }}
          >
            <Button
              variant="outlined"
              onClick={handleClose}
              sx={{ fontSize: "1.1vh", textTransform: "none" }}
            >
              Cancel
            </Button>
            <Button
              variant="contained"
              onClick={handleSave}
              disabled={images.length === 0}
              sx={{ fontSize: "1.1vh", textTransform: "none" }}
            >
              Save
            </Button>
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default SaveDialog;
