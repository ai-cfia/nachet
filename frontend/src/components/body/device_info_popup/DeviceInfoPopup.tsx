import React, { useState, useMemo } from "react";
import {
  Box,
  Dialog,
  DialogContent,
  IconButton,
  Button,
  Select,
  MenuItem,
  Typography,
  FormControl,
  InputLabel,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { colours } from "../../../styles/colours";
import { ApiDevicesResponse } from "@common/types";

interface DeviceInfoPopupProps {
  setDeviceInfoOpen: React.Dispatch<React.SetStateAction<boolean>>;
  deviceInfoOpen: boolean;
  devicesData: ApiDevicesResponse | null;
}

const DeviceInfoPopup: React.FC<DeviceInfoPopupProps> = (props) => {
  const [selectedBrandId, setSelectedBrandId] = useState<string>("");
  const [selectedModelId, setSelectedModelId] = useState<string>("");
  const [selectedLensId, setSelectedLensId] = useState<string>("");

  const handleClose = (): void => {
    props.setDeviceInfoOpen(false);
    // Reset selections when closing
    setSelectedBrandId("");
    setSelectedModelId("");
    setSelectedLensId("");
  };

  // Get the selected brand object
  const selectedBrand = useMemo(() => {
    if (!props.devicesData || !selectedBrandId) return null;
    return (
      props.devicesData.devices.find((brand) => brand.id === selectedBrandId) ||
      null
    );
  }, [props.devicesData, selectedBrandId]);

  // Filter models based on selected brand
  const availableModels = useMemo(() => {
    return selectedBrand?.models || [];
  }, [selectedBrand]);

  // Filter lenses based on selected brand
  const availableLenses = useMemo(() => {
    return selectedBrand?.lenses || [];
  }, [selectedBrand]);

  const handleBrandChange = (brandId: string) => {
    setSelectedBrandId(brandId);
    // Reset model and lens when brand changes
    setSelectedModelId("");
    setSelectedLensId("");
  };

  return (
    <Dialog
      open={props.deviceInfoOpen}
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
              Device Information
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
            {/* Brand Dropdown */}
            <FormControl fullWidth size="small">
              <InputLabel id="device-brand-label" sx={{ fontSize: "1.4vh" }}>
                Device Brand
              </InputLabel>
              <Select
                labelId="device-brand-label"
                value={selectedBrandId}
                onChange={(e) => handleBrandChange(e.target.value)}
                label="Device Brand"
                sx={{ fontSize: "1.4vh" }}
              >
                <MenuItem value="" sx={{ fontSize: "1.4vh" }}>
                  <em>Select a brand</em>
                </MenuItem>
                {props.devicesData?.devices.map((brand) => (
                  <MenuItem
                    key={brand.id}
                    value={brand.id}
                    sx={{ fontSize: "1.4vh" }}
                  >
                    {brand.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {/* Model Dropdown */}
            <FormControl fullWidth size="small" disabled={!selectedBrandId}>
              <InputLabel id="device-model-label" sx={{ fontSize: "1.4vh" }}>
                Device Model
              </InputLabel>
              <Select
                labelId="device-model-label"
                value={selectedModelId}
                onChange={(e) => setSelectedModelId(e.target.value)}
                label="Device Model"
                sx={{ fontSize: "1.4vh" }}
              >
                <MenuItem value="" sx={{ fontSize: "1.4vh" }}>
                  <em>Select a model</em>
                </MenuItem>
                {availableModels.map((model) => (
                  <MenuItem
                    key={model.id}
                    value={model.id}
                    sx={{ fontSize: "1.4vh" }}
                  >
                    {model.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {/* Lens Dropdown */}
            <FormControl fullWidth size="small" disabled={!selectedBrandId}>
              <InputLabel id="device-lens-label" sx={{ fontSize: "1.4vh" }}>
                Device Lens
              </InputLabel>
              <Select
                labelId="device-lens-label"
                value={selectedLensId}
                onChange={(e) => setSelectedLensId(e.target.value)}
                label="Device Lens"
                sx={{ fontSize: "1.4vh" }}
              >
                <MenuItem value="" sx={{ fontSize: "1.4vh" }}>
                  <em>Select a lens</em>
                </MenuItem>
                {availableLenses.map((lens) => (
                  <MenuItem
                    key={lens.id}
                    value={lens.id}
                    sx={{ fontSize: "1.4vh" }}
                  >
                    {lens.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

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
                  <strong>Brand:</strong> {selectedBrand.name}
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
                    <strong>Model:</strong>{" "}
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
                    <strong>Lens:</strong>{" "}
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
              Done
            </Button>
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default DeviceInfoPopup;
