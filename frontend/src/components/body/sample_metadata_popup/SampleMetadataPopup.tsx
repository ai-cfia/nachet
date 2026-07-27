import React, { useState, useMemo, useEffect } from "react";
import {
  Box,
  Dialog,
  DialogContent,
  IconButton,
  Typography,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { colours } from "../../../styles/colours";
import { ApiDevicesResponse, ApiDeviceBrand } from "@common/types";
import { useDeviceStore } from "@stores/useDeviceStore";
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

const NONE_ID = "none";

interface SampleMetadataPopupProps {
  devicesData: ApiDevicesResponse | null;
}

const SampleMetadataPopup: React.FC<SampleMetadataPopupProps> = (props) => {
  const { t } = useTranslation("popups");
  const {
    deviceSelection,
    setDeviceSelection,
    sampleMetadata,
    setSampleMetadata,
  } = useDeviceStore();
  const { isSampleMetadataOpen, closeSampleMetadataPopup } = useModalStore();

  // Initialize device selection state with persisted values
  const [selectedBrandId, setSelectedBrandId] = useState<string>("");
  const [selectedModelId, setSelectedModelId] = useState<string>("");
  const [selectedLensId, setSelectedLensId] = useState<string>("");

  // Initialize sample metadata state
  const [trayCode, setTrayCode] = useState<string>("");
  const [magnification, setMagnification] = useState<number>(0.1);
  const [sampleIdPrefix, setSampleIdPrefix] = useState<string>("");
  const [sampleDescription, setSampleDescription] = useState<string>("");

  // Load persisted values when popup opens (only when transitioning to open)
  useEffect(() => {
    if (isSampleMetadataOpen) {
      console.log("DEBUG: Loading sample metadata from store:", sampleMetadata);

      // Load device selection
      setSelectedBrandId(() => deviceSelection.selectedBrandId);
      setSelectedModelId(() => deviceSelection.selectedModelId);
      setSelectedLensId(() => deviceSelection.selectedLensId);

      // Load sample metadata
      setTrayCode(() => sampleMetadata.trayCode);
      setMagnification(() => sampleMetadata.magnification);
      setSampleIdPrefix(() => sampleMetadata.sampleIdPrefix);
      setSampleDescription(() => sampleMetadata.sampleDescription);

      console.log(
        "DEBUG: After setting state - sampleIdPrefix:",
        sampleMetadata.sampleIdPrefix,
      );
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isSampleMetadataOpen]); // Only re-run when dialog opens/closes

  // Validation error states
  const [brandError, setBrandError] = useState<string>("");
  const [modelError, setModelError] = useState<string>("");
  const [lensError, setLensError] = useState<string>("");
  const [trayCodeError, setTrayCodeError] = useState<string>("");
  const [magnificationError, setMagnificationError] = useState<string>("");
  const [sampleIdPrefixError, setSampleIdPrefixError] = useState<string>("");
  const [sampleDescriptionError, setSampleDescriptionError] =
    useState<string>("");

  // Zod validation hooks for auto-normalization on blur
  const sampleIdPrefixValidation = useZodFieldValidation(
    imageNameSchema,
    sampleIdPrefix,
    setSampleIdPrefix,
    setSampleIdPrefixError,
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

    // Validate device selection using Zod with i18n.
    // "none" is an accepted answer (device unknown), so treat it as filled.
    const brandResult = deviceIdValidationSchema.safeParse(selectedBrandId);
    if (selectedBrandId !== NONE_ID && !brandResult.success) {
      setBrandError(t("deviceInfo.errors.brandRequired"));
      isValid = false;
    } else {
      setBrandError("");
    }

    const modelResult = deviceIdValidationSchema.safeParse(selectedModelId);
    if (selectedModelId !== NONE_ID && !modelResult.success) {
      setModelError(t("deviceInfo.errors.modelRequired"));
      isValid = false;
    } else {
      setModelError("");
    }

    const lensResult = deviceIdValidationSchema.safeParse(selectedLensId);
    if (selectedLensId !== NONE_ID && !lensResult.success) {
      setLensError(t("deviceInfo.errors.lensRequired"));
      isValid = false;
    } else {
      setLensError("");
    }

    // Validate sample metadata using Zod with i18n
    const trayCodeResult = trayCodeSchema.safeParse(trayCode);
    if (trayCode !== "none" && !trayCodeResult.success) {
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

    // Validate sample ID prefix using Zod with i18n (same rules as image name)
    const sampleIdPrefixResult = imageNameSchema.safeParse(sampleIdPrefix);
    if (!sampleIdPrefixResult.success) {
      const issue = sampleIdPrefixResult.error.issues[0];
      // Map Zod error codes to specific translation keys
      if (issue.code === "too_small") {
        setSampleIdPrefixError(t("deviceInfo.validation.imageName.empty"));
      } else if (issue.code === "too_big") {
        setSampleIdPrefixError(t("deviceInfo.validation.imageName.tooLong"));
      } else {
        const errorKey = getZodErrorKey(sampleIdPrefixResult.error);
        setSampleIdPrefixError(t(errorKey));
      }
      isValid = false;
    } else {
      setSampleIdPrefixError("");
    }

    // Validate sample description using Zod with i18n
    const sampleDescriptionResult =
      descriptionSchema.safeParse(sampleDescription);
    if (!sampleDescriptionResult.success) {
      const issue = sampleDescriptionResult.error.issues[0];
      // Map Zod error codes to specific translation keys
      if (issue.code === "too_small") {
        setSampleDescriptionError(t("deviceInfo.validation.description.empty"));
      } else if (issue.code === "too_big") {
        setSampleDescriptionError(
          t("deviceInfo.validation.description.tooLong"),
        );
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
    if (!validateAndSave()) {
      return;
    }

    // Save device selection to Zustand store
    setDeviceSelection({
      selectedBrandId,
      selectedModelId,
      selectedLensId,
    });

    // Save sample metadata to Zustand store
    setSampleMetadata({
      trayCode,
      magnification,
      sampleIdPrefix,
      sampleDescription,
    });

    closeSampleMetadataPopup();
  };

  const handleCancel = (): void => {
    // Don't save, just close
    closeSampleMetadataPopup();
  };

  // Synthetic "None" option used to resolve the display box when the
  // user selects None (device unknown).
  const noneOption: ApiDeviceBrand = useMemo(
    () => ({
      id: NONE_ID,
      name: t("deviceInfo.none"),
      description: "",
      models: [],
      lenses: [],
    }),
    [t],
  );

  // Get the selected brand object for display
  const selectedBrand = useMemo(() => {
    if (!selectedBrandId) return null;
    if (selectedBrandId === NONE_ID) return noneOption;
    if (!props.devicesData) return null;
    return (
      props.devicesData.devices.find((brand) => brand.id === selectedBrandId) ||
      null
    );
  }, [props.devicesData, selectedBrandId, noneOption]);

  // Get available models/lenses for display, including the None option
  const availableModels = useMemo(() => {
    return [...(selectedBrand?.models || []), noneOption];
  }, [selectedBrand, noneOption]);

  const availableLenses = useMemo(() => {
    return [...(selectedBrand?.lenses || []), noneOption];
  }, [selectedBrand, noneOption]);

  return (
    <Dialog
      open={isSampleMetadataOpen}
      onClose={handleCancel}
      maxWidth="sm"
      fullWidth
      slotProps={{
        paper: {
          sx: {
            borderRadius: 1,
            padding: "1vh",
            minHeight: "45vh",
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
              {t("deviceInfo.title")}
            </Typography>
            <IconButton onClick={handleCancel} size="small">
              <CloseIcon />
            </IconButton>
          </Box>

          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              gap: 3,
              marginTop: "2vh",
            }}
          >
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
            />

            <SampleMetadataFields
              trayCode={trayCode}
              magnification={magnification}
              sampleIdPrefix={sampleIdPrefix}
              sampleDescription={sampleDescription}
              onTrayCodeChange={(value) => {
                setTrayCode(value);
                if (trayCodeError) setTrayCodeError("");
              }}
              onMagnificationChange={(value) => {
                setMagnification(value);
                if (magnificationError) setMagnificationError("");
              }}
              onSampleIdPrefixChange={sampleIdPrefixValidation.onChange}
              onSampleIdPrefixBlur={sampleIdPrefixValidation.onBlur}
              onSampleDescriptionChange={sampleDescriptionValidation.onChange}
              onSampleDescriptionBlur={sampleDescriptionValidation.onBlur}
              trayCodeError={trayCodeError}
              magnificationError={magnificationError}
              sampleIdPrefixError={sampleIdPrefixError}
              sampleDescriptionError={sampleDescriptionError}
            />

            {/* Display selected device info */}
            {selectedBrand && (
              <Box
                sx={{
                  marginTop: "2vh",
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
            sx={{ marginTop: "3vh" }}
          />
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default SampleMetadataPopup;
