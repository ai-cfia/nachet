import React, { useState, useMemo, useEffect } from "react";
import {
  Box,
  Dialog,
  DialogContent,
  IconButton,
  Typography,
  TextField,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { colours } from "../../../styles/colours";
import { ApiDevicesResponse } from "@common/types";
import { useImageStore } from "@stores/useImageStore";
import { useModalStore } from "@stores/useModalStore";
import {
  DeviceSelectionFields,
  SampleMetadataFields,
  PopupActionButtons,
} from "@components/common";
import { useTranslation } from "react-i18next";
import {
  imageNameSchema,
  descriptionSchema,
  deviceIdValidationSchema,
  trayCodeSchema,
  magnificationSchema,
} from "@common/validation";
import { getZodErrorKey } from "@common/zodErrorMap";
import {
  useZodFieldValidation,
  ERROR_KEY_MAPPINGS,
} from "@hooks/useZodFieldValidation";

interface ImageMetadataPopupProps {
  devicesData: ApiDevicesResponse | null;
}

const ImageMetadataPopup: React.FC<ImageMetadataPopupProps> = (props) => {
  const { t } = useTranslation("popups");
  const { images, updateImageMetadata, removeImage } = useImageStore();
  const {
    isImageMetadataOpen,
    closeImageMetadataPopup,
    imageMetadataImageIndex,
    imageMetadataMode,
  } = useModalStore();

  // Initialize image name and ID state
  const [imageName, setImageName] = useState<string>("");
  const [imageId, setImageId] = useState<string>("");

  // Initialize device selection state
  const [selectedBrandId, setSelectedBrandId] = useState<string>("");
  const [selectedModelId, setSelectedModelId] = useState<string>("");
  const [selectedLensId, setSelectedLensId] = useState<string>("");

  // Initialize sample metadata state
  const [trayCode, setTrayCode] = useState<string>("");
  const [magnification, setMagnification] = useState<number>(1);
  const [sampleDescription, setSampleDescription] = useState<string>("");

  // Load image-specific data when popup opens
  useEffect(() => {
    if (isImageMetadataOpen && imageMetadataImageIndex !== null) {
      const currentImage = images.find(
        (img) => img.index === imageMetadataImageIndex,
      );

      if (currentImage) {
        // Load image name and ID
        setImageName(() => currentImage.imageName || "");
        setImageId(() => currentImage.imageId || "");

        // Load device selection
        setSelectedBrandId(() => currentImage.deviceBrandId || "");
        setSelectedModelId(() => currentImage.deviceModelId || "");
        setSelectedLensId(() => currentImage.deviceLensId || "");

        // Load sample metadata
        setTrayCode(() => currentImage.trayCode || "");
        setMagnification(() => currentImage.magnification || 1);
        setSampleDescription(() => currentImage.imageDescription || "");
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isImageMetadataOpen, imageMetadataImageIndex]); // Only re-run when dialog opens/closes or image index changes

  // Validation error states
  const [imageNameError, setImageNameError] = useState<string>("");
  const [brandError, setBrandError] = useState<string>("");
  const [modelError, setModelError] = useState<string>("");
  const [lensError, setLensError] = useState<string>("");
  const [trayCodeError, setTrayCodeError] = useState<string>("");
  const [magnificationError, setMagnificationError] = useState<string>("");
  const [sampleDescriptionError, setSampleDescriptionError] =
    useState<string>("");

  // Zod validation hooks for auto-normalization on blur
  const imageNameValidation = useZodFieldValidation(
    imageNameSchema,
    imageName,
    setImageName,
    setImageNameError,
    ERROR_KEY_MAPPINGS.imageName,
  );

  const sampleDescriptionValidation = useZodFieldValidation(
    descriptionSchema,
    sampleDescription,
    setSampleDescription,
    setSampleDescriptionError,
    ERROR_KEY_MAPPINGS.description,
  );

  const validateAndSave = (): boolean => {
    let isValid = true;

    // Validate image name using Zod with i18n
    const imageNameResult = imageNameSchema.safeParse(imageName);
    if (!imageNameResult.success) {
      const issue = imageNameResult.error.issues[0];
      // Map Zod error codes to specific translation keys
      if (issue.code === "too_small") {
        setImageNameError(t("validation.imageName.empty"));
      } else if (issue.code === "too_big") {
        setImageNameError(t("validation.imageName.tooLong"));
      } else {
        const errorKey = getZodErrorKey(imageNameResult.error);
        setImageNameError(t(errorKey));
      }
      isValid = false;
    } else {
      setImageNameError("");
    }

    // Validate device selection using Zod with i18n
    const brandResult = deviceIdValidationSchema.safeParse(selectedBrandId);
    if (!brandResult.success) {
      setBrandError(t("deviceInfo.errors.brandRequired"));
      isValid = false;
    } else {
      setBrandError("");
    }

    const modelResult = deviceIdValidationSchema.safeParse(selectedModelId);
    if (!modelResult.success) {
      setModelError(t("deviceInfo.errors.modelRequired"));
      isValid = false;
    } else {
      setModelError("");
    }

    const lensResult = deviceIdValidationSchema.safeParse(selectedLensId);
    if (!lensResult.success) {
      setLensError(t("deviceInfo.errors.lensRequired"));
      isValid = false;
    } else {
      setLensError("");
    }

    // Validate sample metadata using Zod with i18n
    const trayCodeResult = trayCodeSchema.safeParse(trayCode);
    if (!trayCodeResult.success) {
      setTrayCodeError(t("batchUpload.metadataSection.trayCodeRequired"));
      isValid = false;
    } else {
      setTrayCodeError("");
    }

    const magnificationResult = magnificationSchema.safeParse(magnification);
    if (!magnificationResult.success) {
      const issue = magnificationResult.error.issues[0];
      // Map Zod error codes to specific translation keys
      if (issue.code === "too_small") {
        setMagnificationError(t("validation.magnification.tooSmall"));
      } else if (issue.code === "too_big") {
        setMagnificationError(t("validation.magnification.tooLarge"));
      } else {
        const errorKey = getZodErrorKey(magnificationResult.error);
        setMagnificationError(t(errorKey));
      }
      isValid = false;
    } else {
      setMagnificationError("");
    }

    // Validate sample description (now required) using Zod with i18n
    const sampleDescriptionResult =
      descriptionSchema.safeParse(sampleDescription);
    if (!sampleDescriptionResult.success) {
      const issue = sampleDescriptionResult.error.issues[0];
      // Map Zod error codes to specific translation keys
      if (issue.code === "too_small") {
        setSampleDescriptionError(t("validation.description.empty"));
      } else if (issue.code === "too_big") {
        setSampleDescriptionError(t("validation.description.tooLong"));
      } else {
        const errorKey = getZodErrorKey(sampleDescriptionResult.error);
        setSampleDescriptionError(t(errorKey));
      }
      isValid = false;
    } else {
      setSampleDescriptionError("");
    }

    return isValid;
  };

  const handleSave = (): void => {
    if (imageMetadataImageIndex !== null) {
      if (imageMetadataMode === "delete") {
        // Delete mode - remove the image
        removeImage(imageMetadataImageIndex);
        closeImageMetadataPopup();
      } else {
        // Edit mode - validate and update
        if (!validateAndSave()) {
          return;
        }

        // Update image metadata in Zustand store (frontend-only)
        updateImageMetadata(imageMetadataImageIndex, {
          imageName: imageName.trim(),
          imageDescription: sampleDescription,
          deviceBrandId: selectedBrandId,
          deviceModelId: selectedModelId,
          deviceLensId: selectedLensId,
          trayCode,
          magnification,
        });

        closeImageMetadataPopup();
      }
    }
  };

  const handleCancel = (): void => {
    // Clear validation errors
    setImageNameError("");
    setBrandError("");
    setModelError("");
    setLensError("");
    setTrayCodeError("");
    setMagnificationError("");
    setSampleDescriptionError("");

    // Close popup
    closeImageMetadataPopup();
  };

  // Get the selected brand object for display
  const selectedBrand = useMemo(() => {
    if (!props.devicesData || !selectedBrandId) return null;
    return (
      props.devicesData.devices.find((brand) => brand.id === selectedBrandId) ||
      null
    );
  }, [props.devicesData, selectedBrandId]);

  // Get available models/lenses for display
  const availableModels = useMemo(() => {
    return selectedBrand?.models || [];
  }, [selectedBrand]);

  const availableLenses = useMemo(() => {
    return selectedBrand?.lenses || [];
  }, [selectedBrand]);

  return (
    <Dialog
      open={isImageMetadataOpen}
      onClose={handleCancel}
      maxWidth="sm"
      fullWidth
      slotProps={{
        paper: {
          sx: {
            borderRadius: 1,
            padding: "1vh",
            minHeight: "50vh",
          },
        },
      }}
    >
      <DialogContent>
        <Box
          sx={{
            display: "flex",
            flexDirection: "column",
            height: "100%",
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
              {imageMetadataMode === "delete"
                ? t("imageMetadata.deleteTitle", {
                    defaultValue: "Delete Image",
                  })
                : t("imageMetadata.title")}
            </Typography>
            <IconButton onClick={handleCancel} size="small">
              <CloseIcon />
            </IconButton>
          </Box>

          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              gap: 2,
              marginTop: "2vh",
            }}
          >
            {/* Image Name Field */}
            <TextField
              label={t("imageMetadata.imageName")}
              value={imageName}
              onChange={(e) => imageNameValidation.onChange(e.target.value)}
              onBlur={imageNameValidation.onBlur}
              error={!!imageNameError}
              helperText={imageNameError}
              fullWidth
              disabled={imageMetadataMode === "delete"}
              sx={{ fontSize: "1.4vh" }}
            />

            {/* Image ID Field (Read-only) */}
            <TextField
              label={t("imageMetadata.imageId")}
              value={imageId}
              disabled
              fullWidth
              sx={{ fontSize: "1.4vh" }}
            />

            {/* Device Selection Fields */}
            <DeviceSelectionFields
              selectedBrandId={selectedBrandId}
              selectedModelId={selectedModelId}
              selectedLensId={selectedLensId}
              onBrandChange={(value) => {
                setSelectedBrandId(value);
                if (brandError) setBrandError("");
              }}
              onModelChange={(value) => {
                setSelectedModelId(value);
                if (modelError) setModelError("");
              }}
              onLensChange={(value) => {
                setSelectedLensId(value);
                if (lensError) setLensError("");
              }}
              devicesData={props.devicesData}
              brandError={brandError}
              modelError={modelError}
              lensError={lensError}
              disabled={imageMetadataMode === "delete"}
            />

            {/* Sample Metadata Fields */}
            <SampleMetadataFields
              trayCode={trayCode}
              magnification={magnification}
              sampleDescription={sampleDescription}
              onTrayCodeChange={(value) => {
                setTrayCode(value);
                if (trayCodeError) setTrayCodeError("");
              }}
              onMagnificationChange={(value) => {
                setMagnification(value);
                if (magnificationError) setMagnificationError("");
              }}
              onSampleDescriptionChange={sampleDescriptionValidation.onChange}
              onSampleDescriptionBlur={sampleDescriptionValidation.onBlur}
              trayCodeError={trayCodeError}
              magnificationError={magnificationError}
              sampleDescriptionError={sampleDescriptionError}
              disabled={imageMetadataMode === "delete"}
            />

            {/* Display selected device info */}
            {selectedBrand && (
              <Box
                sx={{
                  marginTop: "1vh",
                  padding: "1vh",
                  backgroundColor: "#f5f5f5",
                  borderRadius: "0.4vh",
                }}
              >
                <Typography
                  variant="body2"
                  sx={{ fontSize: "1.3vh", marginBottom: "0.5vh" }}
                >
                  <strong>{t("deviceInfo.brand")}:</strong> {selectedBrand.name}
                </Typography>
                {selectedBrand.description && (
                  <Typography
                    variant="body2"
                    sx={{ fontSize: "1.2vh", color: "gray" }}
                  >
                    {selectedBrand.description}
                  </Typography>
                )}
                {selectedModelId && (
                  <Typography
                    variant="body2"
                    sx={{ fontSize: "1.3vh", marginTop: "0.5vh" }}
                  >
                    <strong>{t("deviceInfo.model")}:</strong>{" "}
                    {
                      availableModels.find((m) => m.id === selectedModelId)
                        ?.name
                    }
                  </Typography>
                )}
                {selectedLensId && (
                  <Typography
                    variant="body2"
                    sx={{ fontSize: "1.3vh", marginTop: "0.5vh" }}
                  >
                    <strong>{t("deviceInfo.lens")}:</strong>{" "}
                    {availableLenses.find((l) => l.id === selectedLensId)?.name}
                  </Typography>
                )}
              </Box>
            )}
          </Box>

          <PopupActionButtons
            onSave={handleSave}
            onCancel={handleCancel}
            saveLabel={
              imageMetadataMode === "delete"
                ? t("imageMetadata.deleteButton", {
                    defaultValue: "Delete",
                  })
                : undefined
            }
            sx={{ marginTop: "3vh" }}
          />
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default ImageMetadataPopup;
