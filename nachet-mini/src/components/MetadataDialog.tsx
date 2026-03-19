import { useState, useMemo } from "react";
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Box,
} from "@mui/material";
import { useTranslation } from "react-i18next";
import { DEVICE_BRANDS } from "@common/deviceData";
import type { TrayCode, ImageMetadata } from "@common/types";
import {
  validateImageName,
  validateDescription,
  validateMagnification,
} from "@common/validation";
import { useMetadataDefaultsStore } from "@stores/useMetadataDefaultsStore";
import { useImageStore } from "@stores/useImageStore";

interface Props {
  open: boolean;
  onClose: () => void;
  mode: "defaults" | "image";
  imageIndex?: number;
}

const TRAY_CODES: TrayCode[] = ["A", "B", "C", "D", "E", "None"];

/**
 * Inner form that reads initial values once on mount.
 * The parent re-keys this component each time the dialog opens,
 * so useState initializers run fresh every time.
 */
const MetadataForm = ({ onClose, mode, imageIndex }: Omit<Props, "open">) => {
  const { t } = useTranslation("main");

  const metaDefaults = useMetadataDefaultsStore((s) => s.defaults);
  const setDefaults = useMetadataDefaultsStore((s) => s.setDefaults);
  const images = useImageStore((s) => s.images);
  const updateImageMetadata = useImageStore((s) => s.updateImageMetadata);

  const sourceImage =
    mode === "image" && imageIndex !== undefined
      ? images.find((i) => i.index === imageIndex)
      : undefined;

  const initial =
    mode === "image" && sourceImage
      ? sourceImage.metadata
      : {
          imageName: "",
          deviceBrandId: metaDefaults.deviceBrandId,
          deviceModelId: metaDefaults.deviceModelId,
          deviceLensId: metaDefaults.deviceLensId,
          trayCode: metaDefaults.trayCode,
          magnification: metaDefaults.magnification,
          description: metaDefaults.description,
        };

  const [namePrefix, setNamePrefix] = useState(metaDefaults.namePrefix);
  const [imageName, setImageName] = useState(initial.imageName);
  const [deviceBrandId, setDeviceBrandId] = useState(initial.deviceBrandId);
  const [deviceModelId, setDeviceModelId] = useState(initial.deviceModelId);
  const [deviceLensId, setDeviceLensId] = useState(initial.deviceLensId);
  const [trayCode, setTrayCode] = useState<TrayCode | "">(initial.trayCode);
  const [magnification, setMagnification] = useState(
    String(initial.magnification),
  );
  const [description, setDescription] = useState(initial.description);
  const [errors, setErrors] = useState<Record<string, string>>({});

  const selectedBrand = useMemo(
    () => DEVICE_BRANDS.find((b) => b.id === deviceBrandId) ?? null,
    [deviceBrandId],
  );

  const handleBrandChange = (brandId: string) => {
    setDeviceBrandId(brandId);
    setDeviceModelId("");
    setDeviceLensId("");
  };

  const handleSave = () => {
    const newErrors: Record<string, string> = {};
    const mag = parseFloat(magnification);

    if (mode === "defaults") {
      const prefixErr = validateImageName(namePrefix);
      if (prefixErr) newErrors.namePrefix = t(prefixErr);
    }

    if (mode === "image") {
      const nameErr = validateImageName(imageName);
      if (nameErr) newErrors.imageName = t(nameErr);
    }

    const descErr = validateDescription(description);
    if (descErr) newErrors.description = t(descErr);

    const magErr = validateMagnification(mag);
    if (magErr) newErrors.magnification = t(magErr);

    if (Object.keys(newErrors).length > 0) {
      setErrors(newErrors);
      return;
    }

    if (mode === "defaults") {
      setDefaults({
        namePrefix,
        deviceBrandId,
        deviceModelId,
        deviceLensId,
        trayCode,
        magnification: mag,
        description,
      });
    } else if (imageIndex !== undefined) {
      const metadata: ImageMetadata = {
        imageName,
        deviceBrandId,
        deviceModelId,
        deviceLensId,
        trayCode,
        magnification: mag,
        description,
      };
      updateImageMetadata(imageIndex, metadata);
    }

    onClose();
  };

  const title =
    mode === "defaults"
      ? t("metadata.defaultsTitle")
      : t("metadata.imageTitle");

  return (
    <>
      <DialogTitle>{title}</DialogTitle>
      <DialogContent>
        <Box sx={{ display: "flex", flexDirection: "column", gap: 2, pt: 1 }}>
          {mode === "defaults" && (
            <TextField
              label={t("metadata.namePrefix")}
              value={namePrefix}
              onChange={(e) => {
                setNamePrefix(e.target.value);
                setErrors((prev) => ({ ...prev, namePrefix: "" }));
              }}
              error={!!errors.namePrefix}
              helperText={errors.namePrefix || t("metadata.namePrefixHint")}
              size="small"
            />
          )}
          {mode === "image" && (
            <TextField
              label={t("metadata.imageName")}
              value={imageName}
              onChange={(e) => {
                setImageName(e.target.value);
                setErrors((prev) => ({ ...prev, imageName: "" }));
              }}
              error={!!errors.imageName}
              helperText={errors.imageName}
              size="small"
            />
          )}

          {/* Device brand */}
          <FormControl size="small" fullWidth>
            <InputLabel>{t("metadata.deviceBrand")}</InputLabel>
            <Select
              value={deviceBrandId}
              onChange={(e) => handleBrandChange(e.target.value)}
              label={t("metadata.deviceBrand")}
            >
              <MenuItem value="">
                <em>{t("metadata.selectBrand")}</em>
              </MenuItem>
              {DEVICE_BRANDS.map((brand) => (
                <MenuItem key={brand.id} value={brand.id}>
                  {brand.name}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          {/* Device model + lens side by side */}
          <Box sx={{ display: "flex", gap: 2 }}>
            <FormControl
              size="small"
              sx={{ flex: 1 }}
              disabled={!deviceBrandId}
            >
              <InputLabel>{t("metadata.deviceModel")}</InputLabel>
              <Select
                value={deviceModelId}
                onChange={(e) => setDeviceModelId(e.target.value)}
                label={t("metadata.deviceModel")}
              >
                <MenuItem value="">
                  <em>{t("metadata.selectModel")}</em>
                </MenuItem>
                {(selectedBrand?.models ?? []).map((m) => (
                  <MenuItem key={m.id} value={m.id}>
                    {m.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <FormControl
              size="small"
              sx={{ flex: 1 }}
              disabled={!deviceBrandId}
            >
              <InputLabel>{t("metadata.deviceLens")}</InputLabel>
              <Select
                value={deviceLensId}
                onChange={(e) => setDeviceLensId(e.target.value)}
                label={t("metadata.deviceLens")}
              >
                <MenuItem value="">
                  <em>{t("metadata.selectLens")}</em>
                </MenuItem>
                {(selectedBrand?.lenses ?? []).map((l) => (
                  <MenuItem key={l.id} value={l.id}>
                    {l.name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>

          {/* Tray code + magnification side by side */}
          <Box sx={{ display: "flex", gap: 2 }}>
            <FormControl size="small" sx={{ flex: 1 }}>
              <InputLabel>{t("metadata.trayCode")}</InputLabel>
              <Select
                value={trayCode}
                onChange={(e) => setTrayCode(e.target.value as TrayCode | "")}
                label={t("metadata.trayCode")}
              >
                <MenuItem value="">
                  <em>{t("metadata.selectTrayCode")}</em>
                </MenuItem>
                {TRAY_CODES.map((code) => (
                  <MenuItem key={code} value={code}>
                    {code}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <TextField
              label={t("metadata.magnification")}
              type="number"
              value={magnification}
              onChange={(e) => {
                setMagnification(e.target.value);
                setErrors((prev) => ({ ...prev, magnification: "" }));
              }}
              error={!!errors.magnification}
              helperText={errors.magnification}
              size="small"
              sx={{ flex: 1 }}
              slotProps={{ htmlInput: { min: 0.1, max: 1000, step: 0.1 } }}
            />
          </Box>

          {/* Description */}
          <TextField
            label={t("metadata.description")}
            value={description}
            onChange={(e) => {
              setDescription(e.target.value);
              setErrors((prev) => ({ ...prev, description: "" }));
            }}
            error={!!errors.description}
            helperText={errors.description}
            size="small"
            multiline
            rows={3}
          />
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{t("metadata.cancel")}</Button>
        <Button onClick={handleSave} variant="contained">
          {t("metadata.save")}
        </Button>
      </DialogActions>
    </>
  );
};

/**
 * Wrapper that controls Dialog open/close and re-keys the inner form
 * so it remounts (and reinitializes state) each time the dialog opens.
 */
const MetadataDialog = ({ open, onClose, mode, imageIndex }: Props) => {
  const [mountKey, setMountKey] = useState(0);

  const handleClose = () => {
    onClose();
    setMountKey((k) => k + 1);
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      {open && (
        <MetadataForm
          key={mountKey}
          onClose={handleClose}
          mode={mode}
          imageIndex={imageIndex}
        />
      )}
    </Dialog>
  );
};

export default MetadataDialog;
