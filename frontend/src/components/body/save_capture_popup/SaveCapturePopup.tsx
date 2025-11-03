import React, { useState, useMemo } from "react";
import {
  Box,
  Dialog,
  DialogContent,
  IconButton,
  TextField,
  MenuItem,
  Select,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import type { SelectChangeEvent } from "@mui/material/Select";
import CloseIcon from "@mui/icons-material/Close";
import { colours } from "../../../styles/colours";
import { saveAs } from "file-saver";
import JSZip from "jszip";
import { imageLabelSchema, imageFormatSchema } from "@common/validation";
import { getZodErrorKey } from "@common/zodErrorMap";
import { PopupActionButtons } from "@components/common";
import { useImageStore } from "@stores/useImageStore";
import { useModalStore } from "@stores/useModalStore";
import { useNotificationStore } from "@stores/useNotificationStore";
import { useTranslation } from "react-i18next";

interface params {
  imageFormat?: string;
  imageLabel?: string;
  setImageFormat?: React.Dispatch<React.SetStateAction<string>>;
  setImageLabel?: React.Dispatch<React.SetStateAction<string>>;
  setSaveIndividualImage?: React.Dispatch<React.SetStateAction<string>>;
  saveIndividualImage?: string;
}

const SavePopup: React.FC<params> = (props) => {
  const { t } = useTranslation("popups");
  const { t: tValidation } = useTranslation("validation");
  const { t: tErrors } = useTranslation("errors");
  const { images: imageCache, getCurrentImage } = useImageStore();
  const { closeSavePopup } = useModalStore();
  const { addError } = useNotificationStore();
  const [labelError, setLabelError] = useState<string>("");

  // Get imageSrc from current image in store
  const imageSrc = useMemo(() => {
    const currentImage = getCurrentImage();
    return currentImage?.src ?? "";
  }, [getCurrentImage]);

  const saveImage = (): void => {
    // Validate image label if saving individual image
    if (props.saveIndividualImage === "0" && props.imageLabel) {
      const labelValidation = imageLabelSchema.safeParse(props.imageLabel);
      if (!labelValidation.success) {
        setLabelError(tValidation(getZodErrorKey(labelValidation.error)));
        return;
      }
    }

    // Clear any previous errors
    setLabelError("");

    // saves image to local storage or compresses the entire cache into a zip file which is then saved to local storage
    (async () => {
      // save individual image
      if (props.saveIndividualImage === "0" && imageCache.length > 0) {
        saveAs(
          imageSrc,
          `${props.imageLabel}-${new Date().getFullYear()}-${
            new Date().getMonth() + 1
          }-${new Date().getDate()}.${props.imageFormat?.split("/")[1]}`,
        );
        closeSavePopup();
      } else if (props.saveIndividualImage === "1" && imageCache.length > 0) {
        // compress all images from cache to zip file and download
        const zip = new JSZip();
        imageCache.forEach((image) => {
          const base64Data = image.src.replace(/^data:image\/\w+;base64,/, "");
          zip.file(
            `Capture-${image.index}-${new Date().getFullYear()}-${
              new Date().getMonth() + 1
            }-${new Date().getDate()}.${props.imageFormat?.split("/")[1]}`,
            base64Data,
            {
              base64: true,
            },
          );
        });
        const content = await zip.generateAsync({ type: "blob" });
        saveAs(
          content,
          `${new Date().getFullYear()}-${
            new Date().getMonth() + 1
          }-${new Date().getDate()}.${props.imageFormat?.split("/")[1]}.zip`,
        );
        closeSavePopup();
      }
    })().catch((error) => {
      console.error(
        "Save error:",
        error instanceof Error ? error.message : String(error),
      );
      addError(tErrors("save.imageFailed", { error: String(error) }), "save");
    });
  };

  const handleClose = (): void => {
    closeSavePopup();
  };

  const handleFormat = (event: SelectChangeEvent): void => {
    if (props.setImageFormat === undefined) {
      return;
    }
    props.setImageFormat(event.target.value);
  };

  const handleLabel = (event: any): void => {
    if (props.setImageLabel === undefined) {
      return;
    }
    props.setImageLabel(event.target.value);
    // Clear validation error when user types
    if (labelError) setLabelError("");
  };

  const handleToggle = (): void => {
    if (props.setSaveIndividualImage === undefined) {
      return;
    }
    if (props.saveIndividualImage === "0") {
      props.setSaveIndividualImage("1");
    } else {
      props.setSaveIndividualImage("0");
    }
  };

  const validateFields = (): boolean => {
    let isValid = true;

    // Validate image label
    if (props.saveIndividualImage === "0") {
      const labelValidation = imageLabelSchema.safeParse(props.imageLabel);
      if (!labelValidation.success) {
        setLabelError(tValidation(getZodErrorKey(labelValidation.error)));
        isValid = false;
        console.error("Label validation error:", labelValidation.error);
      } else {
        setLabelError("");
      }
    }

    // Validate image format
    const formatValidation = imageFormatSchema.safeParse(props.imageFormat);
    if (!formatValidation.success) {
      isValid = false;
      console.error("Format validation error:", formatValidation.error);
    }

    return isValid;
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
              {t("saveCapture.title")}
            </Typography>
            <IconButton onClick={handleClose} size="small">
              <CloseIcon />
            </IconButton>
          </Box>
          <div style={{ marginBottom: "2vh", marginTop: "1vh" }}>
            <ToggleButtonGroup
              sx={{
                color: colours.CFIA_Font_Black,
                fontSize: "1.0vh",
                height: "2vh",
              }}
              fullWidth
              exclusive
              onChange={handleToggle}
              value={props.saveIndividualImage}
              aria-label="Platform"
            >
              <ToggleButton
                value="0"
                fullWidth
                sx={{ color: colours.CFIA_Font_Black }}
              >
                {t("saveCapture.captureTab")}
              </ToggleButton>
              <ToggleButton
                value="1"
                fullWidth
                sx={{ color: colours.CFIA_Font_Black }}
              >
                {t("saveCapture.cacheTab")}
              </ToggleButton>
            </ToggleButtonGroup>
          </div>
          {props.saveIndividualImage === "0" && (
            <>
              <>
                <TextField
                  id="outlined-basic"
                  label={t("saveCapture.captureNameLabel")}
                  variant="outlined"
                  onChange={handleLabel}
                  value={props.imageLabel}
                  size="small"
                  fullWidth
                  InputLabelProps={{ shrink: true }}
                  error={!!labelError}
                  helperText={labelError}
                  sx={{
                    height: "2vh",
                    marginBottom: "2vh",
                    fontSize: "1.2vh",
                  }}
                />
              </>
              <Select
                value={props.imageFormat}
                onChange={handleFormat}
                fullWidth
                sx={{ fontSize: "1.2vh", height: "3vh" }}
              >
                <MenuItem value="image/png">
                  {t("saveCapture.formatPng")}
                </MenuItem>
                <MenuItem value="image/jpeg">
                  {t("saveCapture.formatJpeg")}
                </MenuItem>
              </Select>
            </>
          )}
          {props.saveIndividualImage === "1" && (
            <>
              <Select
                fullWidth
                value={props.imageFormat}
                onChange={handleFormat}
                sx={{ fontSize: "1.2vh", height: "3vh" }}
              >
                <MenuItem value="image/png">
                  {t("saveCapture.formatPng")}
                </MenuItem>
                <MenuItem value="image/jpeg">
                  {t("saveCapture.formatJpeg")}
                </MenuItem>
              </Select>
            </>
          )}
          <PopupActionButtons
            onSave={() => {
              if (validateFields()) {
                saveImage();
              }
            }}
            onCancel={handleClose}
            sx={{ marginTop: "2vh", marginBottom: "1vh" }}
          />
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default SavePopup;
