import React, { useState } from "react";
import {
  Box,
  Dialog,
  DialogContent,
  IconButton,
  Select,
  MenuItem,
  Typography,
} from "@mui/material";
import type { SelectChangeEvent } from "@mui/material/Select";
import CloseIcon from "@mui/icons-material/Close";
import { useTranslation } from "react-i18next";
import { colours } from "../../../styles/colours";
import { deviceIdSchema } from "@common/validation";
import { useModalStore } from "@stores/useModalStore";
import { useWebcamStore } from "@stores/useWebcamStore";

const SwitchDevice: React.FC = () => {
  const { t } = useTranslation("popups");
  const [deviceError, setDeviceError] = useState<string>("");
  const { closeSwitchDevicePopup } = useModalStore();
  const { devices, activeDeviceId, setActiveDeviceId } = useWebcamStore();

  const handleClose = (): void => {
    closeSwitchDevicePopup();
    setDeviceError("");
  };

  const handleSwitch = (event: SelectChangeEvent): void => {
    const selectedDeviceId = event.target.value;

    // Validate device ID
    const validation = deviceIdSchema.safeParse(selectedDeviceId);
    if (!validation.success) {
      setDeviceError(validation.error.issues[0].message);
      return;
    }

    // Clear error and proceed
    setDeviceError("");
    setActiveDeviceId(selectedDeviceId);
    closeSwitchDevicePopup();
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
              {t("switchDevice.title")}
            </Typography>
            <IconButton onClick={handleClose} size="small">
              <CloseIcon />
            </IconButton>
          </Box>
          <Box
            sx={{
              display: "flex",
              flexDirection: "column",
              paddingLeft: "1vw",
              paddingRight: "1vw",
              marginTop: "1vh",
              marginBottom: "2vh",
            }}
          >
            <Select
              value={activeDeviceId}
              onChange={handleSwitch}
              sx={{ fontSize: "1.2vh" }}
              size="small"
              fullWidth
            >
              {devices.map((device) => (
                <MenuItem
                  key={device.deviceId}
                  value={device.deviceId}
                  sx={{ fontSize: "1.2vh" }}
                >
                  {device.label.split("(")[0]}
                </MenuItem>
              ))}
            </Select>
            {deviceError && (
              <Typography
                color="error"
                variant="caption"
                sx={{ marginTop: "0.5vh" }}
              >
                {deviceError}
              </Typography>
            )}
          </Box>
        </Box>
      </DialogContent>
    </Dialog>
  );
};

export default SwitchDevice;
