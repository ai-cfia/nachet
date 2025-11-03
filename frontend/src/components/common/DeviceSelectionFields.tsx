import React, { useMemo } from "react";
import { Box, FormControl, InputLabel, MenuItem, Select } from "@mui/material";
import { ApiDevicesResponse } from "@common/types";
import { useTranslation } from "react-i18next";

interface DeviceSelectionFieldsProps {
  selectedBrandId: string;
  selectedModelId: string;
  selectedLensId: string;
  onBrandChange: (brandId: string) => void;
  onModelChange: (modelId: string) => void;
  onLensChange: (lensId: string) => void;
  devicesData: ApiDevicesResponse | null;
  disabled?: boolean;
  brandError?: string;
  modelError?: string;
  lensError?: string;
}

export const DeviceSelectionFields: React.FC<DeviceSelectionFieldsProps> = ({
  selectedBrandId,
  selectedModelId,
  selectedLensId,
  onBrandChange,
  onModelChange,
  onLensChange,
  devicesData,
  disabled = false,
  brandError,
  modelError,
  lensError,
}) => {
  const { t } = useTranslation("popups");
  // Get the selected brand object
  const selectedBrand = useMemo(() => {
    if (!devicesData || !selectedBrandId) return null;
    return (
      devicesData.devices.find((brand) => brand.id === selectedBrandId) || null
    );
  }, [devicesData, selectedBrandId]);

  // Filter models based on selected brand
  const availableModels = useMemo(() => {
    return selectedBrand?.models || [];
  }, [selectedBrand]);

  // Filter lenses based on selected brand
  const availableLenses = useMemo(() => {
    return selectedBrand?.lenses || [];
  }, [selectedBrand]);

  const handleBrandChange = (brandId: string) => {
    onBrandChange(brandId);
    // Reset model and lens when brand changes
    onModelChange("");
    onLensChange("");
  };

  return (
    <Box
      sx={{
        display: "flex",
        flexDirection: "column",
        gap: "10px",
        width: "100%",
      }}
    >
      {/* Brand Dropdown */}
      <FormControl fullWidth disabled={disabled} error={!!brandError}>
        <InputLabel id="device-brand-label">
          {t("deviceInfo.deviceBrandLabel")}
        </InputLabel>
        <Select
          labelId="device-brand-label"
          value={selectedBrandId}
          onChange={(e) => handleBrandChange(e.target.value)}
          label={t("deviceInfo.deviceBrandLabel")}
        >
          <MenuItem value="">
            <em>{t("deviceInfo.selectBrand")}</em>
          </MenuItem>
          {devicesData?.devices.map((brand) => (
            <MenuItem key={brand.id} value={brand.id}>
              {brand.name}
            </MenuItem>
          ))}
        </Select>
        {brandError && (
          <div
            style={{
              color: "#d32f2f",
              fontSize: "0.75rem",
              marginTop: "3px",
              marginLeft: "14px",
            }}
          >
            {brandError}
          </div>
        )}
      </FormControl>

      {/* Model and Lens Dropdowns - Side by Side */}
      <Box
        sx={{
          display: "flex",
          flexDirection: "row",
          gap: "10px",
          width: "100%",
        }}
      >
        {/* Model Dropdown */}
        <FormControl
          sx={{ width: "calc(50% - 5px)" }}
          disabled={!selectedBrandId || disabled}
          error={!!modelError}
        >
          <InputLabel id="device-model-label">
            {t("deviceInfo.deviceModelLabel")}
          </InputLabel>
          <Select
            labelId="device-model-label"
            value={selectedModelId}
            onChange={(e) => onModelChange(e.target.value)}
            label={t("deviceInfo.deviceModelLabel")}
          >
            <MenuItem value="">
              <em>{t("deviceInfo.selectModel")}</em>
            </MenuItem>
            {availableModels.map((model) => (
              <MenuItem key={model.id} value={model.id}>
                {model.name}
              </MenuItem>
            ))}
          </Select>
          {modelError && (
            <div
              style={{
                color: "#d32f2f",
                fontSize: "0.75rem",
                marginTop: "3px",
                marginLeft: "14px",
              }}
            >
              {modelError}
            </div>
          )}
        </FormControl>

        {/* Lens Dropdown */}
        <FormControl
          sx={{ width: "calc(50% - 5px)" }}
          disabled={!selectedBrandId || disabled}
          error={!!lensError}
        >
          <InputLabel id="device-lens-label">
            {t("deviceInfo.deviceLensLabel")}
          </InputLabel>
          <Select
            labelId="device-lens-label"
            value={selectedLensId}
            onChange={(e) => onLensChange(e.target.value)}
            label={t("deviceInfo.deviceLensLabel")}
          >
            <MenuItem value="">
              <em>{t("deviceInfo.selectLens")}</em>
            </MenuItem>
            {availableLenses.map((lens) => (
              <MenuItem key={lens.id} value={lens.id}>
                {lens.name}
              </MenuItem>
            ))}
          </Select>
          {lensError && (
            <div
              style={{
                color: "#d32f2f",
                fontSize: "0.75rem",
                marginTop: "3px",
                marginLeft: "14px",
              }}
            >
              {lensError}
            </div>
          )}
        </FormControl>
      </Box>
    </Box>
  );
};
