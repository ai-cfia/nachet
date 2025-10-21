import React, { useMemo } from "react";
import { FormControl, InputLabel, MenuItem, Select } from "@mui/material";
import { ApiDevicesResponse } from "@common/types";

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
    <>
      {/* Brand Dropdown */}
      <FormControl
        fullWidth
        sx={{ marginTop: "10px" }}
        disabled={disabled}
        error={!!brandError}
      >
        <InputLabel id="device-brand-label">Device Brand</InputLabel>
        <Select
          labelId="device-brand-label"
          value={selectedBrandId}
          onChange={(e) => handleBrandChange(e.target.value)}
          label="Device Brand"
        >
          <MenuItem value="">
            <em>Select a brand</em>
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

      {/* Model Dropdown */}
      <FormControl
        fullWidth
        sx={{ marginTop: "10px" }}
        disabled={!selectedBrandId || disabled}
        error={!!modelError}
      >
        <InputLabel id="device-model-label">Device Model</InputLabel>
        <Select
          labelId="device-model-label"
          value={selectedModelId}
          onChange={(e) => onModelChange(e.target.value)}
          label="Device Model"
        >
          <MenuItem value="">
            <em>Select a model</em>
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
        fullWidth
        sx={{ marginTop: "10px" }}
        disabled={!selectedBrandId || disabled}
        error={!!lensError}
      >
        <InputLabel id="device-lens-label">Device Lens</InputLabel>
        <Select
          labelId="device-lens-label"
          value={selectedLensId}
          onChange={(e) => onLensChange(e.target.value)}
          label="Device Lens"
        >
          <MenuItem value="">
            <em>Select a lens</em>
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
    </>
  );
};
