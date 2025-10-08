import React, { useState } from "react";
import {
  Box,
  Dialog,
  DialogContent,
  IconButton,
  Button,
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
import { Images } from "@common/types";
import { imageLabelSchema, imageFormatSchema } from "@common/validation";

interface params {
  imageSrc: string;
  imageCache: Images[];
  setSaveOpen?: React.Dispatch<React.SetStateAction<boolean>>;
  imageFormat?: string;
  imageLabel?: string;
  setImageFormat?: React.Dispatch<React.SetStateAction<string>>;
  setImageLabel?: React.Dispatch<React.SetStateAction<string>>;
  setSaveIndividualImage?: React.Dispatch<React.SetStateAction<string>>;
  saveIndividualImage?: string;
}

const SavePopup: React.FC<params> = (props) => {
  const [labelError, setLabelError] = useState<string>("");

  const saveImage = (): void => {
    // Validate image label if saving individual image
    if (props.saveIndividualImage === "0" && props.imageLabel) {
      const labelValidation = imageLabelSchema.safeParse(props.imageLabel);
      if (!labelValidation.success) {
        setLabelError(labelValidation.error.issues[0].message);
        return;
      }
    }

    // Clear any previous errors
    setLabelError("");

    // saves image to local storage or compresses the entire cache into a zip file which is then saved to local storage
    (async () => {
      // save individual image
      if (props.saveIndividualImage === "0" && props.imageCache.length > 0) {
        saveAs(
          props.imageSrc,
          `${props.imageLabel}-${new Date().getFullYear()}-${
            new Date().getMonth() + 1
          }-${new Date().getDate()}.${props.imageFormat?.split("/")[1]}`,
        );
        props.setSaveOpen?.(false);
      } else if (
        props.saveIndividualImage === "1" &&
        props.imageCache.length > 0
      ) {
        // compress all images from cache to zip file and download
        const zip = new JSZip();
        props.imageCache.forEach((image) => {
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
        props.setSaveOpen?.(false);
      }
    })().catch((error) => {
      console.error("Save error:", error);
      alert("Error saving image: " + error);
    });
  };

  const handleClose = (): void => {
    if (props.setSaveOpen === undefined) {
      return;
    }
    props.setSaveOpen(false);
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
      try {
        imageLabelSchema.parse(props.imageLabel);
        setLabelError("");
      } catch (error) {
        setLabelError("Capture name must be at least 3 characters long");
        isValid = false;
        console.error("Label validation error:", error);
      }
    }

    // Validate image format
    try {
      imageFormatSchema.parse(props.imageFormat);
    } catch (error) {
      isValid = false;
      console.error("Format validation error:", error);
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
              Save Capture
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
                CAPTURE
              </ToggleButton>
              <ToggleButton
                value="1"
                fullWidth
                sx={{ color: colours.CFIA_Font_Black }}
              >
                CACHE
              </ToggleButton>
            </ToggleButtonGroup>
          </div>
          {props.saveIndividualImage === "0" && (
            <>
              <>
                <TextField
                  id="outlined-basic"
                  label="Capture Name"
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
                <MenuItem value="image/png">Format: PNG</MenuItem>
                <MenuItem value="image/jpeg">Format: JPEG</MenuItem>
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
                <MenuItem value="image/png">Format: PNG</MenuItem>
                <MenuItem value="image/jpeg">Format: JPEG</MenuItem>
              </Select>
            </>
          )}
          <Box
            sx={{
              display: "flex",
              justifyContent: "center",
              marginTop: "2vh",
              marginBottom: "1vh",
            }}
          >
            <Button
              variant="outlined"
              size="medium"
              sx={{
                borderRadius: "0.4vh",
                paddingTop: "0.6vh",
                paddingBottom: "0.6vh",
                paddingLeft: "2vh",
                paddingRight: "2vh",
                fontSize: "1.17vh",
                width: "fit-content",
                border: `0.15vh solid ${colours.CFIA_Background_Blue}`,
                color: colours.CFIA_Background_Blue,
                "&:hover": {
                  backgroundColor: colours.CFIA_Background_Blue,
                  color: colours.CFIA_Background_White,
                  border: `0.15vh solid ${colours.CFIA_Background_Blue}`,
                  transition: "0.2s ease-in-out all",
                },
              }}
              onClick={() => {
                if (validateFields()) {
                  saveImage();
                }
              }}
            >
              SAVE
            </Button>
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default SavePopup;
