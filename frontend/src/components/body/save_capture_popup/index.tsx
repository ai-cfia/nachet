import React, { useState } from "react";
import { Overlay, ButtonWrap, InfoContainer } from "./indexElements";
import {
  Box,
  CardHeader,
  IconButton,
  Button,
  TextField,
  MenuItem,
  Select,
  ToggleButton,
  ToggleButtonGroup,
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
    <Overlay>
      <Box
        sx={{
          width: "20vw",
          height: "fit-content",
          zIndex: 30,
          border: `0.01vh solid LightGrey`,
          borderRadius: 1,
          background: colours.CFIA_Background_White,
        }}
        boxShadow={1}
      >
        <CardHeader
          title="Save Capture"
          titleTypographyProps={{
            variant: "h6",
            align: "left",
            fontWeight: 600,
            fontSize: "1.3vh",
            color: colours.CFIA_Font_Black,
            zIndex: 30,
          }}
          action={
            <IconButton onClick={handleClose}>
              <CloseIcon />
            </IconButton>
          }
          sx={{ padding: "0.8vh 0.8vh 0.8vh 0.8vh" }}
        />
        <InfoContainer>
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
          <ButtonWrap>
            <Button
              variant="outlined"
              size="medium"
              sx={{
                marginRight: 0,
                marginLeft: 0,
                borderRadius: "0.4vh",
                paddingTop: "0.3vh",
                paddingBottom: "0.3vh",
                paddingLeft: "0.7vh",
                paddingRight: "0.7vh",
                fontSize: "1.17vh",
                width: "fit-content",
                border: `0.01vh solid LightGrey`,
                color: colours.CFIA_Font_Black,
                "&:hover": {
                  backgroundColor: "#F5F5F5",
                  transition: "0.1s ease-in-out all",
                  border: `0.01vh solid LightGrey`,
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
          </ButtonWrap>
        </InfoContainer>
      </Box>
    </Overlay>
  );
};

export default SavePopup;
