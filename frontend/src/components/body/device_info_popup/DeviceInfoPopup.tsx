import React, { useState, useMemo, useEffect } from "react";
import {
  Box,
  Dialog,
  DialogContent,
  IconButton,
  Button,
  Typography,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { colours } from "../../../styles/colours";
import { ApiDevicesResponse } from "@common/types";
import { useDeviceStore } from "@stores/useDeviceStore";
import { useModalStore } from "@stores/useModalStore";
import { DeviceSelectionFields } from "@components/common/DeviceSelectionFields";
import { useTranslation } from "react-i18next";

interface DeviceInfoPopupProps {
  devicesData: ApiDevicesResponse | null;
}

const DeviceInfoPopup: React.FC<DeviceInfoPopupProps> = (props) => {
  const { t } = useTranslation("popups");
  const { deviceSelection, setDeviceSelection } = useDeviceStore();
  const { isDeviceInfoOpen, closeDeviceInfoPopup } = useModalStore();

  // Initialize state with persisted values directly
  const [selectedBrandId, setSelectedBrandId] = useState<string>("");
  const [selectedModelId, setSelectedModelId] = useState<string>("");
  const [selectedLensId, setSelectedLensId] = useState<string>("");

  // Load persisted values when popup opens (only when transitioning to open)
  useEffect(() => {
    if (isDeviceInfoOpen) {
      // Use a functional update to avoid dependency on state setters
      setSelectedBrandId(() => deviceSelection.selectedBrandId);
      setSelectedModelId(() => deviceSelection.selectedModelId);
      setSelectedLensId(() => deviceSelection.selectedLensId);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [isDeviceInfoOpen]); // Only re-run when dialog opens/closes

  const handleClose = (): void => {
    // Save selections to Zustand store
    setDeviceSelection({
      selectedBrandId,
      selectedModelId,
      selectedLensId,
    });
    closeDeviceInfoPopup();
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
      open={isDeviceInfoOpen}
      onClose={handleClose}
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
            <IconButton onClick={handleClose} size="small">
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
              onBrandChange={setSelectedBrandId}
              onModelChange={setSelectedModelId}
              onLensChange={setSelectedLensId}
              devicesData={props.devicesData}
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

          <Box
            sx={{
              display: "flex",
              justifyContent: "center",
              marginTop: "3vh",
            }}
          >
            <Button
              variant="outlined"
              onClick={handleClose}
              sx={{
                borderRadius: "0.4vh",
                paddingTop: "0.6vh",
                paddingBottom: "0.6vh",
                paddingLeft: "2vh",
                paddingRight: "2vh",
                fontSize: "1.17vh",
                border: `0.15vh solid ${colours.CFIA_Background_Blue}`,
                color: colours.CFIA_Background_Blue,
                "&:hover": {
                  backgroundColor: colours.CFIA_Background_Blue,
                  color: colours.CFIA_Background_White,
                  border: `0.15vh solid ${colours.CFIA_Background_Blue}`,
                  transition: "0.2s ease-in-out all",
                },
              }}
            >
              {t("deviceInfo.doneButton")}
            </Button>
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default DeviceInfoPopup;
