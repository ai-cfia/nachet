import { useRef, useState } from "react";
import {
  Box,
  Button,
  Dialog,
  DialogContent,
  IconButton,
  Typography,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { validateImageFile } from "@common/imageutils";
import { useTranslation } from "react-i18next";

interface Props {
  open: boolean;
  onClose: () => void;
  /** Called with the data URL, [width, height], and original filename once a valid file is read. */
  onImageLoaded: (src: string, dims: number[], fileName: string) => void;
}

const ImageUpload = ({ open, onClose, onImageLoaded }: Props) => {
  const { t } = useTranslation("main");
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string>("");

  const handleFileChange = async (
    event: React.ChangeEvent<HTMLInputElement>,
  ): Promise<void> => {
    const files = event.target.files;
    if (!files || files.length === 0) return;

    setError("");
    const errors: string[] = [];

    for (const file of Array.from(files)) {
      const validation = await validateImageFile(file);

      if (!validation.isValid) {
        errors.push(
          `${file.name}: ${validation.errorKeys.map((key) => t(`validation.${key}`)).join(", ")}`,
        );
        continue;
      }

      await new Promise<void>((resolve) => {
        const reader = new FileReader();
        reader.onloadend = () => {
          if (typeof reader.result === "string") {
            const dims = validation.dimensions
              ? [validation.dimensions.width, validation.dimensions.height]
              : [0, 0];
            onImageLoaded(reader.result, dims, file.name);
          }
          resolve();
        };
        reader.readAsDataURL(file);
      });
    }

    if (fileInputRef.current) fileInputRef.current.value = "";

    if (errors.length > 0) {
      setError(errors.join("\n"));
    } else {
      onClose();
    }
  };

  const handleClose = (): void => {
    setError("");
    onClose();
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
              sx={{ fontWeight: 600, fontSize: "1.8vh", color: "text.primary" }}
            >
              {t("imageUpload.title")}
            </Typography>
            <IconButton onClick={handleClose} size="small" aria-label="close">
              <CloseIcon />
            </IconButton>
          </Box>

          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              paddingLeft: "1vw",
              paddingRight: "1vw",
              marginTop: "1vh",
              marginBottom: error ? "1vh" : "2vh",
            }}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="image/png,image/jpeg"
              multiple
              onChange={handleFileChange}
              style={{ display: "none" }}
            />
            <Button
              variant="contained"
              onClick={() => {
                fileInputRef.current?.click();
              }}
              fullWidth
              sx={{ fontSize: "1.2vh", textTransform: "none" }}
            >
              {t("imageUpload.chooseFile")}
            </Button>
          </Box>

          {error && (
            <Typography
              variant="body2"
              color="error"
              sx={{
                px: "1vw",
                pb: "1vh",
                fontSize: "1.1vh",
                whiteSpace: "pre-line",
              }}
            >
              {error}
            </Typography>
          )}
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default ImageUpload;
