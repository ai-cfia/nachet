import React, { useRef } from "react";
import {
  Box,
  Button,
  Dialog,
  DialogContent,
  IconButton,
  Typography,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { colours } from "../../../styles/colours";
import { validateImageFile } from "@common";
import { useModalStore } from "@stores/useModalStore";
import { useTranslation } from "react-i18next";

interface params {
  pushImageToCache: (imageUrl: string) => void;
}

const UploadPopup: React.FC<params> = (props) => {
  const { t } = useTranslation("popups");
  const { pushImageToCache } = props;
  const { closeUploadPopup } = useModalStore();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const uploadImage = async (event: any): Promise<void> => {
    // loads image from local storage to cache when upload button is pressed
    event.preventDefault();
    const file = event.target.files[0];

    if (file !== undefined) {
      // Validate the file with comprehensive checks including dimensions
      const validation = await validateImageFile(file);
      if (!validation.isValid) {
        alert(validation.errors.join("\n"));
        return;
      }

      const reader = new FileReader();
      reader.onloadend = () => {
        if (typeof reader.result !== "string") {
          return;
        }
        pushImageToCache(reader.result);
      };
      reader.readAsDataURL(file);
    }
    closeUploadPopup();
  };

  const handleClose = (): void => {
    closeUploadPopup();
  };

  const handleButtonClick = (): void => {
    fileInputRef.current?.click();
  };

  return (
    <Dialog
      open={true}
      onClose={handleClose}
      maxWidth="xs"
      fullWidth
      slotProps={{
        paper: {
          sx: {
            borderRadius: 1,
            padding: "1vh",
          },
        },
      }}
    >
      <DialogContent>
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
          }}
        >
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
                color: colours.CFIA_Font_Black,
              }}
            >
              {t("uploadImage.title")}
            </Typography>
            <IconButton onClick={handleClose} size="small">
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
              marginBottom: "2vh",
            }}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="image/png"
              onChange={uploadImage}
              style={{ display: "none" }}
            />
            <Button
              variant="contained"
              onClick={handleButtonClick}
              fullWidth
              sx={{
                fontSize: "1.2vh",
                textTransform: "none",
              }}
            >
              {t("uploadImage.chooseFileButton")}
            </Button>
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default UploadPopup;
