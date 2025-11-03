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
import { ApiDevicesResponse } from "@common/types";
import { useDeviceStore } from "@stores/useDeviceStore";
import { useModalStore } from "@stores/useModalStore";
import {
  DeviceSelectionFields,
  SampleMetadataFields,
  PopupActionButtons,
} from "@components/common";
import { useTranslation } from "react-i18next";

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
  const [magnification, setMagnification] = useState<number>(0);
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

  const validateAndSave = (): boolean => {
    let isValid = true;

    // Validate device selection
    if (!selectedBrandId) {
      setBrandError(t("deviceInfo.errors.brandRequired"));
      isValid = false;
    }
    if (!selectedModelId) {
      setModelError(t("deviceInfo.errors.modelRequired"));
      isValid = false;
    }
    if (!selectedLensId) {
      setLensError(t("deviceInfo.errors.lensRequired"));
      isValid = false;
    }

    // Validate sample metadata
    if (!trayCode) {
      setTrayCodeError(t("batchUpload.metadataSection.trayCodeRequired"));
      isValid = false;
    }
    if (magnification <= 0) {
      setMagnificationError(
        t("batchUpload.metadataSection.magnificationRequired"),
      );
      isValid = false;
    }
    if (!sampleIdPrefix) {
      setSampleIdPrefixError(t("batchUpload.metadataSection.sampleIdRequired"));
      isValid = false;
    }
    if (!sampleDescription) {
      setSampleDescriptionError(
        t("batchUpload.metadataSection.sampleDescriptionRequired"),
      );
      isValid = false;
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
              onSampleIdPrefixChange={(value) => {
                console.log(
                  "DEBUG: onSampleIdPrefixChange called with:",
                  value,
                );
                setSampleIdPrefix(value);
                if (sampleIdPrefixError) setSampleIdPrefixError("");
              }}
              onSampleDescriptionChange={(value) => {
                setSampleDescription(value);
                if (sampleDescriptionError) setSampleDescriptionError("");
              }}
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
